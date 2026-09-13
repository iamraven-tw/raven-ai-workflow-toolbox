#!/usr/bin/env python3
"""以虛構專案與假的 wrangler 程式驗證部署工具；不連 Cloudflare。"""

from __future__ import annotations

import http.server
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from functools import partial
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "skills/website-deploy/scripts/deploy_site.py"
SCAFFOLD = ROOT / "skills/website-build/scripts/scaffold_site.py"
DEFAULT = ROOT / "skills/website-setup/assets/default-config.json"

SPEC = importlib.util.spec_from_file_location("website_deploy_tested", DEPLOY)
deploy_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy_module)

FAKE_WRANGLER = '''#!/usr/bin/env python3
import os, sys
mode = os.environ.get("FAKE_WRANGLER_MODE", "logged_in")
args = sys.argv[1:]
print(" ⛅️ wrangler 4.129.0")
if args[:1] == ["whoami"]:
    if mode == "logged_out":
        print("You are not authenticated. Please run `wrangler login`."); sys.exit(1)
    print("Getting User settings...")
    print("👋 You are logged in with an OAuth Token, associated with the email fictional.owner@example.invalid.")
    print("┌──────────────────┬──────────────────────────────────┐")
    print("│ Account Name     │ Account ID                       │")
    print("├──────────────────┼──────────────────────────────────┤")
    print("│ Fictional Studio │ 0123456789abcdef0123456789abcdef │")
    print("└──────────────────┴──────────────────────────────────┘")
    print("🔓 Token Permissions:")
    print("Scope (Access)")
    print("- account (read)")
    print("- user (read)")
    print("- workers (write)")
    print("- zone (read)")
    sys.exit(0)
if args[:1] == ["deploy"]:
    if mode == "deploy_fail":
        print("✘ [ERROR] A request to the Cloudflare API failed. fictional error", file=sys.stderr); sys.exit(1)
    if mode == "deploy_no_subdomain":
        print("✘ [ERROR] You need to register a workers.dev subdomain before publishing", file=sys.stderr); sys.exit(1)
    print("Total Upload: 42.00 KiB / gzip: 12.00 KiB")
    print("Uploaded fictional-studio (1.23 sec)")
    print("Deployed fictional-studio triggers (0.45 sec)")
    print("  https://fictional-studio.fictional-owner.workers.dev")
    if mode == "deploy_with_domain":
        print("  fictional.example (custom domain)")
        print("  www.fictional.example (custom domain)")
    print("Current Version ID: 0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0")
    sys.exit(0)
print("unknown fake command", file=sys.stderr); sys.exit(2)
'''

PAGE = (
    '<!doctype html><html lang="zh-TW"><head><meta charset="utf-8"><title>{title}</title>'
    '<meta name="description" content="虛構描述"><meta name="robots" content="{robots}">'
    '<meta property="og:title" content="{title}"><meta property="og:description" content="虛構描述">'
    '<meta property="og:image" content="{og}"></head><body><h1>{title}</h1></body></html>'
)


def configured_config() -> dict:
    payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
    payload["business"].update(
        {
            "status": "configured", "site_name": "虛構工作室", "one_line_positioning": "幫虛構的小店把流程交給 AI",
            "audience_summary": "沒有技術團隊的虛構店主", "offerings": [{"name": "虛構諮詢", "summary": "一次會談"}],
            "primary_call_to_action": {"kind": "mailto", "label": "寫信給我", "target": "mailto:hello@example.invalid"},
            "contact_channels": [{"kind": "email", "label": "Email", "target": "mailto:hello@example.invalid"}],
        }
    )
    payload["hosting"]["worker_name"] = "fictional-studio"
    payload["hosting"]["custom_domain"] = {"wanted": "yes", "current_state": "existing_on_cloudflare", "acquisition_route": "existing", "domain": "fictional.example"}
    payload["verification"]["custom_domain"] = "not_started"
    return payload


class DeploySiteTests(unittest.TestCase):
    def test_native_command_resolution_and_missing_npx(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            for platform, executable in (("nt", "npx.cmd"), ("posix", "npx")):
                with self.subTest(platform=platform), mock.patch.object(os, "name", platform):
                    with mock.patch.object(deploy_module.shutil, "which", return_value=executable) as which:
                        self.assertEqual(deploy_module.wrangler_command(),
                                         [executable, "--no-install", "wrangler"])
                        which.assert_called_once_with(executable)
            with mock.patch.object(deploy_module.shutil, "which", return_value=None):
                with self.assertRaisesRegex(deploy_module.DeployError, "npx"):
                    deploy_module.wrangler_command()

    def test_subprocess_preserves_windows_environment_but_not_tokens(self):
        environment = {"Path": "fictional-path", "SystemRoot": "fictional-system",
                       "USERPROFILE": "fictional-profile", "TEMP": "fictional-temp",
                       "APPDATA": "fictional-appdata", "CLOUDFLARE_API_TOKEN": "fictional-secret",
                       "UNRELATED_SECRET": "fictional-secret"}
        with mock.patch.dict(os.environ, environment, clear=True):
            with mock.patch.object(deploy_module, "wrangler_command", return_value=["fictional.exe"]):
                with mock.patch.object(deploy_module.subprocess, "run") as run:
                    deploy_module.run_wrangler(self.project, ["whoami"])
        arguments, options = run.call_args
        self.assertEqual(arguments[0], ["fictional.exe", "whoami"])
        child_env = {key.upper(): value for key, value in options["env"].items()}
        for key in ("PATH", "SYSTEMROOT", "USERPROFILE", "TEMP", "APPDATA"):
            self.assertIn(key, child_env)
        self.assertNotIn("CLOUDFLARE_API_TOKEN", child_env)
        self.assertNotIn("UNRELATED_SECRET", child_env)
        self.assertEqual(options["encoding"], "utf-8")
        self.assertFalse(options.get("shell", False))

    def test_invalid_executable_reports_startup_failure(self):
        with mock.patch.object(deploy_module, "wrangler_command", return_value=["fictional.exe"]):
            with mock.patch.object(deploy_module.subprocess, "run", side_effect=OSError(8, "fictional format")):
                with self.assertRaisesRegex(deploy_module.DeployError, "無法啟動"):
                    deploy_module.run_wrangler(self.project, ["whoami"])

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-website-deploy-")
        self.root = Path(self.temporary.name)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps(configured_config(), ensure_ascii=False), encoding="utf-8")
        self.project = self.root / "site"
        result = subprocess.run([sys.executable, str(SCAFFOLD), "scaffold", "--config", str(self.config), "--target", str(self.project), "--confirm-write"], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        self.fake = self.root / "虛構 fake-wrangler.py"
        self.fake.write_text(FAKE_WRANGLER, encoding="utf-8")
        self.fake.chmod(0o755)
        self.env = {**os.environ, "WEBSITE_WRANGLER_BIN": str(self.fake), "FAKE_WRANGLER_MODE": "logged_in"}
        self.make_dist(robots="noindex, nofollow")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_dist(self, *, robots: str, og: str = "https://example.invalid/og-image.png", include_sitemap: bool = True) -> None:
        dist = self.project / "dist"
        for relative, title in (("index.html", "首頁"), ("about/index.html", "關於"), ("services/index.html", "服務"), ("blog/index.html", "文章"), ("contact/index.html", "聯絡"), ("blog/hello-world/index.html", "文章一"), ("404.html", "找不到")):
            target = dist / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(PAGE.format(title=title, robots=robots, og=og), encoding="utf-8")
        for name in ("rss.xml", "favicon.svg", "og-image.png") + (("sitemap-index.xml",) if include_sitemap else ()):
            (dist / name).write_text("x", encoding="utf-8")
        (dist / "sitemap-0.xml").write_text('<urlset><url><loc>https://fictional.example/</loc></url><url><loc>https://fictional.example/blog/</loc></url><url><loc>https://fictional.example/blog/hello-world/</loc></url></urlset>', encoding="utf-8")
        if not include_sitemap and (dist / "sitemap-index.xml").exists():
            (dist / "sitemap-index.xml").unlink()
        future = time.time() + 5
        for path in dist.rglob("*"):
            os.utime(path, (future, future))

    def run_deploy(self, *arguments: str, mode: str | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(self.env)
        if mode:
            env["FAKE_WRANGLER_MODE"] = mode
        return subprocess.run([sys.executable, str(DEPLOY), *arguments], capture_output=True, text=True, env=env)

    def test_status_parses_login_without_recording_account_id(self) -> None:
        logged_out = self.run_deploy("status", "--project", str(self.project), mode="logged_out")
        self.assertEqual(logged_out.returncode, 1)
        payload = json.loads(logged_out.stdout)
        self.assertEqual(payload["result"], "login_required")
        self.assertIn("wrangler login", payload["human_step"])

        logged_in = self.run_deploy("status", "--project", str(self.project))
        self.assertEqual(logged_in.returncode, 0, logged_in.stderr)
        payload = json.loads(logged_in.stdout)
        self.assertEqual(payload["result"], "logged_in")
        self.assertEqual(payload["email_masked"], "f***@example.invalid")
        self.assertEqual(payload["accounts"], ["Fictional Studio"])
        self.assertNotIn("0123456789abcdef", logged_in.stdout)
        self.assertIn("zone (read)", payload["scopes"])
        self.assertFalse(payload["zone_edit"])
        self.assertEqual(payload["wrangler_version"], "4.129.0")

    def test_plan_reports_upload_and_guards_indexing(self) -> None:
        plan = self.run_deploy("plan", "--project", str(self.project), "--config", str(self.config))
        self.assertEqual(plan.returncode, 0, plan.stderr)
        payload = json.loads(plan.stdout)
        self.assertEqual(payload["worker_name"], "fictional-studio")
        self.assertEqual(payload["upload"]["files"], 12)
        self.assertEqual(payload["indexing"], "noindex")
        self.assertEqual(payload["domain_intent"]["domain"], "fictional.example")
        self.assertIn("免費", payload["cost"])
        self.assertEqual(payload["warnings"], [])

        publish_stage = self.run_deploy("plan", "--project", str(self.project), "--stage", "publish")
        self.assertEqual(publish_stage.returncode, 2)
        self.assertIn("index", publish_stage.stderr)

        later = time.time() + 60
        os.utime(self.project / "site.config.mjs", (later, later))
        stale = json.loads(self.run_deploy("plan", "--project", str(self.project)).stdout)
        self.assertTrue(any("npm run build" in warning for warning in stale["warnings"]))

    def test_deploy_requires_confirmation_and_parses_url(self) -> None:
        without = self.run_deploy("deploy", "--project", str(self.project))
        self.assertEqual(without.returncode, 2)
        mismatch = self.run_deploy("deploy", "--project", str(self.project), "--confirm-deploy", "--expect-indexing", "index")
        self.assertEqual(mismatch.returncode, 2)
        self.assertIn("noindex", mismatch.stderr)

        deployed = self.run_deploy("deploy", "--project", str(self.project), "--confirm-deploy")
        self.assertEqual(deployed.returncode, 0, deployed.stderr)
        payload = json.loads(deployed.stdout)
        self.assertEqual(payload["result"], "deployed")
        self.assertEqual(payload["workers_dev_urls"], ["https://fictional-studio.fictional-owner.workers.dev"])
        self.assertEqual(payload["version_id"], "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0")

        failed = self.run_deploy("deploy", "--project", str(self.project), "--confirm-deploy", mode="deploy_fail")
        self.assertEqual(failed.returncode, 1)
        self.assertEqual(json.loads(failed.stdout)["result"], "failed")
        subdomain = self.run_deploy("deploy", "--project", str(self.project), "--confirm-deploy", mode="deploy_no_subdomain")
        self.assertIn("workers.dev subdomain", "\n".join(json.loads(subdomain.stdout)["output_tail"]))

    def test_deploy_stops_on_forbidden_wrangler_fields(self) -> None:
        wrangler = self.project / "wrangler.jsonc"
        wrangler.write_text(wrangler.read_text(encoding="utf-8").replace('"assets": {', '"account_id": "fictional",\n  "assets": {'), encoding="utf-8")
        result = self.run_deploy("plan", "--project", str(self.project))
        self.assertEqual(result.returncode, 2)
        self.assertIn("account_id", result.stderr)

    def serve_dist(self):
        handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(self.project / "dist"))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, f"http://127.0.0.1:{server.server_address[1]}"

    def test_verify_reads_back_and_reports_findings(self) -> None:
        server, base = self.serve_dist()
        try:
            result = self.run_deploy("verify", "--url", base)
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual([f["kind"] for f in payload["findings"]], ["placeholder_site_url"])

            self.make_dist(robots="noindex, nofollow", og=base + "/og-image.png")
            result = self.run_deploy("verify", "--url", base)
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["result"], "verified")
            self.assertEqual(payload["checks"]["/missing"], 404)
            self.assertEqual(payload["checks"]["/blog/hello-world/"], 200)

            mismatch = json.loads(self.run_deploy("verify", "--url", base, "--expect-indexing", "index").stdout)
            self.assertIn("robots_mismatch", [f["kind"] for f in mismatch["findings"]])

            self.make_dist(robots="noindex, nofollow", og=base + "/og-image.png", include_sitemap=False)
            missing = json.loads(self.run_deploy("verify", "--url", base).stdout)
            self.assertIn({"kind": "unexpected_status", "detail": "/sitemap-index.xml -> 404"}, missing["findings"])
        finally:
            server.shutdown()
            server.server_close()

    def test_verify_rejects_plain_http_public_urls(self) -> None:
        result = self.run_deploy("verify", "--url", "http://fictional.example")
        self.assertEqual(result.returncode, 2)

    def test_domain_plan_apply_is_idempotent_and_writes_redirects(self) -> None:
        bad = self.run_deploy("domain", "plan", "--project", str(self.project), "--domain", "not a domain")
        self.assertEqual(bad.returncode, 2)
        plan = json.loads(self.run_deploy("domain", "plan", "--project", str(self.project), "--domain", "Fictional.Example").stdout)
        self.assertEqual([r["pattern"] for r in plan["routes_to_add"]], ["fictional.example", "www.fictional.example"])
        self.assertFalse((self.project / "public/_redirects").exists())

        without = self.run_deploy("domain", "apply", "--project", str(self.project), "--domain", "fictional.example")
        self.assertEqual(without.returncode, 2)
        applied = self.run_deploy("domain", "apply", "--project", str(self.project), "--domain", "fictional.example", "--confirm-write")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        payload = json.loads(applied.stdout)
        self.assertEqual(payload["site_url"], "https://fictional.example")
        self.assertIn("https://www.fictional.example/* https://fictional.example/:splat 301", (self.project / "public/_redirects").read_text(encoding="utf-8"))
        self.assertIn("url: 'https://fictional.example'", (self.project / "site.config.mjs").read_text(encoding="utf-8"))
        wrangler_text = (self.project / "wrangler.jsonc").read_text(encoding="utf-8")
        self.assertTrue(wrangler_text.startswith("//"))
        self.assertEqual(wrangler_text.count('"custom_domain": true'), 2)

        again = self.run_deploy("domain", "apply", "--project", str(self.project), "--domain", "fictional.example", "--confirm-write")
        self.assertEqual(again.returncode, 0)
        self.assertEqual((self.project / "wrangler.jsonc").read_text(encoding="utf-8").count('"custom_domain": true'), 2)

        plan_after = json.loads(self.run_deploy("plan", "--project", str(self.project), "--stage", "custom_domain").stdout)
        self.assertEqual(plan_after["custom_domain_routes"], ["fictional.example", "www.fictional.example"])

    def test_publish_requires_real_url_and_confirmation(self) -> None:
        blocked = self.run_deploy("publish", "--project", str(self.project), "--confirm-write")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("example.invalid", blocked.stderr)

        bad_url = self.run_deploy("set-url", "--project", str(self.project), "--url", "http://fictional-studio.fictional-owner.workers.dev", "--confirm-write")
        self.assertEqual(bad_url.returncode, 2)
        set_url = self.run_deploy("set-url", "--project", str(self.project), "--url", "https://fictional-studio.fictional-owner.workers.dev", "--confirm-write")
        self.assertEqual(set_url.returncode, 0, set_url.stderr)

        without = self.run_deploy("publish", "--project", str(self.project))
        self.assertEqual(without.returncode, 2)
        published = json.loads(self.run_deploy("publish", "--project", str(self.project), "--confirm-write").stdout)
        self.assertEqual(published["result"], "indexing_set_to_index")
        self.assertIn("indexing: 'index'", (self.project / "site.config.mjs").read_text(encoding="utf-8"))
        again = json.loads(self.run_deploy("publish", "--project", str(self.project), "--confirm-write").stdout)
        self.assertEqual(again["result"], "already_index")

        self.make_dist(robots="index, follow", og="https://fictional-studio.fictional-owner.workers.dev/og-image.png")
        plan = json.loads(self.run_deploy("plan", "--project", str(self.project), "--stage", "publish").stdout)
        self.assertEqual(plan["indexing"], "index")


if __name__ == "__main__":
    unittest.main()
