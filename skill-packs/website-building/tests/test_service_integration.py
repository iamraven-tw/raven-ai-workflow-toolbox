#!/usr/bin/env python3
"""以隔離的虛構網站驗證 website-service-integration。"""

from __future__ import annotations

import json
import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/website-service-integration/scripts/manage_integrations.py"
DEFAULT = ROOT / "skills/website-service-integration/assets/default-integrations.json"


CONTACT = """---
// 聯絡：聯絡管道與主要行動呼籲。表單類整合屬第二版，這裡只放連結。
import BaseLayout from '@theme/BaseLayout.astro';
import { site } from '../../site.config.mjs';
import { copy } from '../../site.copy.mjs';
---
<BaseLayout title="聯絡">
  <p>聯絡</p>
  {site.cta.kind === 'form_later' && <p class="t-note mt-10">{copy.contact.form_note ?? '聯絡表單會在第二版加入；目前請直接使用上方的聯絡方式。'}</p>}
</BaseLayout>
"""


class ServiceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-service-integration-")
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.project = self.workspace / "site"
        (self.workspace / "website").mkdir(parents=True)
        (self.workspace / "website/config.json").write_text("{}\n", encoding="utf-8")
        (self.project / "src/pages").mkdir(parents=True)
        (self.project / "src/pages/contact.astro").write_text(CONTACT, encoding="utf-8")
        (self.project / "package.json").write_text('{"private":true}\n', encoding="utf-8")
        self.candidate = self.root / "candidate.json"
        self.payload = json.loads(DEFAULT.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, command: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                command,
                "--workspace-root",
                str(self.workspace),
                "--project",
                str(self.project),
                *extra,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def configured(self) -> dict:
        payload = json.loads(json.dumps(self.payload))
        payload["status"] = "configured"
        payload["services"]["contact_form"].update({
            "enabled": True,
            "provider": "虛構表單服務",
            "endpoint": "https://forms.example.test/f/contact",
            "privacy_url": "https://forms.example.test/privacy",
        })
        payload["services"]["newsletter"].update({
            "enabled": True,
            "provider": "虛構電子報服務",
            "url": "https://news.example.test/subscribe",
            "privacy_url": "https://news.example.test/privacy",
        })
        payload["services"]["booking"].update({
            "enabled": True,
            "provider": "虛構預約服務",
            "url": "https://book.example.test/consultation",
            "privacy_url": "https://book.example.test/privacy",
        })
        payload["services"]["payment"].update({
            "enabled": True,
            "provider": "虛構付款服務",
            "url": "https://pay.example.test/item/demo",
            "privacy_url": "https://pay.example.test/privacy",
        })
        return payload

    def save_candidate(self, payload: dict | None = None) -> None:
        self.candidate.write_text(json.dumps(payload or self.configured(), ensure_ascii=False), encoding="utf-8")

    def plan(self) -> dict:
        result = self.run_cli("plan", "--candidate", str(self.candidate))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def apply(self) -> dict:
        plan = self.plan()
        result = self.run_cli(
            "apply",
            "--candidate",
            str(self.candidate),
            "--expected-plan-sha256",
            plan["plan_sha256"],
            "--confirm-write",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def write_valid_dist(self, payload: dict) -> None:
        dist = self.project / "dist/contact"
        dist.mkdir(parents=True, exist_ok=True)
        values = [payload["disclosure"]["heading"], payload["disclosure"]["intro"]]
        for service in payload["services"].values():
            if service["enabled"]:
                values.extend([service["provider"], service["privacy_url"], service.get("endpoint") or service.get("url")])
        document = '<form method="post">' + "".join(f"<span>{value}</span>" for value in values)
        document += ''.join(f'<input name="{field}">' for field in ("name", "email", "message", "privacy_consent")) + "</form>"
        (dist / "index.html").write_text(document, encoding="utf-8")

    def test_default_is_not_configured(self) -> None:
        status = self.run_cli("status")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["result"], "not_configured")
        self.candidate.write_bytes(DEFAULT.read_bytes())
        plan = self.plan()
        self.assertEqual(plan["enabled_services"], [])

    def test_plan_apply_status_and_idempotence(self) -> None:
        self.save_candidate()
        plan = self.plan()
        blocked = self.run_cli(
            "apply", "--candidate", str(self.candidate),
            "--expected-plan-sha256", plan["plan_sha256"],
        )
        self.assertEqual(blocked.returncode, 2)
        self.assertFalse((self.workspace / "website/integrations.json").exists())
        applied = self.apply()
        self.assertEqual(applied["result"], "applied")
        contact = (self.project / "src/pages/contact.astro").read_text(encoding="utf-8")
        self.assertEqual(contact.count("website-service-integration:start"), 1)
        self.assertEqual(contact.count("ServiceIntegrations from"), 1)
        self.assertNotIn("第二版加入", contact)
        self.assertTrue((self.project / "src/components/ServiceIntegrations.astro").is_file())
        self.assertEqual(self.run_cli("status").returncode, 0)
        self.apply()
        contact_again = (self.project / "src/pages/contact.astro").read_text(encoding="utf-8")
        self.assertEqual(contact_again, contact)

    def test_stale_plan_and_secret_url_stop_without_write(self) -> None:
        self.save_candidate()
        plan = self.plan()
        contact = self.project / "src/pages/contact.astro"
        contact.write_text(contact.read_text(encoding="utf-8") + "\n<!-- user edit -->\n", encoding="utf-8")
        stale = self.run_cli(
            "apply", "--candidate", str(self.candidate),
            "--expected-plan-sha256", plan["plan_sha256"], "--confirm-write",
        )
        self.assertEqual(stale.returncode, 2)
        self.assertFalse((self.workspace / "website/integrations.json").exists())

        payload = self.configured()
        payload["services"]["contact_form"]["endpoint"] = "https://forms.example.test/f/contact?api_key=not-public"
        self.save_candidate(payload)
        rejected = self.run_cli("plan", "--candidate", str(self.candidate))
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("query", rejected.stderr)

    def test_enabled_service_requires_privacy_url(self) -> None:
        payload = self.configured()
        payload["services"]["newsletter"]["privacy_url"] = None
        self.save_candidate(payload)
        result = self.run_cli("plan", "--candidate", str(self.candidate))
        self.assertEqual(result.returncode, 2)
        self.assertIn("privacy_url", result.stderr)

    def test_local_verify_reads_built_html_and_reports_missing_values(self) -> None:
        payload = self.configured()
        self.save_candidate(payload)
        self.apply()
        self.write_valid_dist(payload)
        verified = self.run_cli("verify")
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["result"], "verified")
        (self.project / "dist/contact/index.html").write_text("<p>broken</p>", encoding="utf-8")
        failed = self.run_cli("verify")
        self.assertEqual(failed.returncode, 1)
        self.assertEqual(json.loads(failed.stdout)["result"], "failed")

    def test_public_readback_uses_contact_page_without_submitting(self) -> None:
        payload = self.configured()
        self.save_candidate(payload)
        self.apply()
        self.write_valid_dist(payload)

        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                pass

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(self.project / "dist"), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            result = self.run_cli("verify", "--url", url)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload_out = json.loads(result.stdout)
            self.assertTrue(payload_out["public_readback"]["verified"])
            self.assertIn("form_delivery", payload_out["not_covered"])
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    @unittest.skipUnless(os.environ.get("WEBSITE_NODE_ACCEPTANCE") == "1", "需要 WEBSITE_NODE_ACCEPTANCE=1 與 Node.js")
    def test_real_astro_build_with_enabled_integrations(self) -> None:
        shutil.rmtree(self.project)
        shutil.copytree(ROOT / "template", self.project)
        self.save_candidate()
        self.apply()
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        self.assertIsNotNone(npm, "找不到 npm")
        installed = subprocess.run([npm, "ci"], cwd=self.project, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(installed.returncode, 0, installed.stderr)
        built = subprocess.run([npm, "run", "build"], cwd=self.project, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(built.returncode, 0, built.stderr)
        verified = self.run_cli("verify")
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["result"], "verified")


if __name__ == "__main__":
    unittest.main()
