#!/usr/bin/env python3
"""以虛構網站驗證 website-operations。"""

from __future__ import annotations

import json
import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "skills/website-operations/scripts/manage_operations.py"
DEFAULT = ROOT / "skills/website-operations/assets/default-operations.json"
SPEC = importlib.util.spec_from_file_location("operations_under_test", MANAGER)
operations = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(operations)


def run_cli(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(MANAGER), *arguments], capture_output=True, text=True)


class FictionalSiteHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - 標準函式名稱由 http.server 定義
        bodies = {
            "/": "<html><title>虛構工作室</title></html>",
            "/robots.txt": "User-agent: *\nAllow: /\n",
            "/sitemap-index.xml": "<sitemapindex></sitemapindex>",
        }
        if self.path not in bodies:
            self.send_response(404)
            self.end_headers()
            return
        body = bodies[self.path].encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class WebsiteOperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-website-operations-")
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.project = self.root / "project"
        (self.workspace / "website/posts").mkdir(parents=True)
        (self.workspace / "website/config.json").write_text("{}\n", encoding="utf-8")
        (self.workspace / "website/posts/hello.md").write_text("# 虛構文章\n", encoding="utf-8")
        (self.project / "src/pages").mkdir(parents=True)
        (self.project / "public").mkdir()
        (self.project / "src/pages/index.astro").write_text("<h1>虛構網站</h1>\n", encoding="utf-8")
        (self.project / "public/robots.txt").write_text("User-agent: *\n", encoding="utf-8")
        (self.project / "package.json").write_text(
            json.dumps(
                {
                    "name": "fictional-site",
                    "dependencies": {"astro": "6.0.8"},
                    "devDependencies": {"wrangler": "4.129.0"},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.project / "package-lock.json").write_text("{}\n", encoding="utf-8")
        self.candidate_path = self.root / "candidate.json"
        candidate = json.loads(DEFAULT.read_text(encoding="utf-8"))
        candidate["status"] = "configured"
        self.candidate_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def roots(self) -> list[str]:
        return ["--workspace-root", str(self.workspace), "--project", str(self.project)]

    def parse_success(self, result: subprocess.CompletedProcess[str]) -> dict:
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def configure(self) -> dict:
        preview = self.parse_success(run_cli(["configure-plan", *self.roots(), "--candidate", str(self.candidate_path)]))
        applied = self.parse_success(
            run_cli(
                [
                    "configure",
                    *self.roots(),
                    "--candidate",
                    str(self.candidate_path),
                    "--expected-plan-sha256",
                    preview["plan_sha256"],
                    "--confirm-write",
                ]
            )
        )
        self.assertEqual(applied["result"], "configured")
        return preview

    def test_status_before_and_after_configure(self) -> None:
        before = self.parse_success(run_cli(["status", *self.roots()]))
        self.assertEqual(before["result"], "not_configured")
        self.assertTrue(before["dependency_pins"]["all_exact"])
        preview = self.parse_success(run_cli(["configure-plan", *self.roots(), "--candidate", str(self.candidate_path)]))
        denied = run_cli(
            [
                "configure",
                *self.roots(),
                "--candidate",
                str(self.candidate_path),
                "--expected-plan-sha256",
                preview["plan_sha256"],
            ]
        )
        self.assertEqual(denied.returncode, 2)
        self.assertFalse((self.workspace / "website/operations.json").exists())
        self.configure()
        after = self.parse_success(run_cli(["status", *self.roots()]))
        self.assertEqual(after["result"], "configured")
        self.assertTrue(after["backups"]["stale"])

    def test_configure_rejects_stale_plan_and_secret(self) -> None:
        preview = self.parse_success(run_cli(["configure-plan", *self.roots(), "--candidate", str(self.candidate_path)]))
        (self.workspace / "website/operations.json").write_text("{}\n", encoding="utf-8")
        stale = run_cli(
            [
                "configure",
                *self.roots(),
                "--candidate",
                str(self.candidate_path),
                "--expected-plan-sha256",
                preview["plan_sha256"],
                "--confirm-write",
            ]
        )
        self.assertEqual(stale.returncode, 2)
        candidate = json.loads(self.candidate_path.read_text(encoding="utf-8"))
        candidate["api_token"] = "fictional"
        secret = self.root / "secret.json"
        secret.write_text(json.dumps(candidate), encoding="utf-8")
        rejected = run_cli(["configure-plan", *self.roots(), "--candidate", str(secret)])
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("秘密", rejected.stderr)

    def test_backup_is_verified_and_excludes_secret_files(self) -> None:
        self.configure()
        (self.workspace / "website/.env").write_text("SHOULD_NOT_BE_BACKED_UP=1\n", encoding="utf-8")
        preview = self.parse_success(run_cli(["backup-plan", *self.roots()]))
        self.assertTrue(any(item["reason"] == "secret_filename" for item in preview["omitted"]))
        self.assertEqual(len(preview["files"]), preview["file_count"])
        denied = run_cli(["backup", *self.roots(), "--expected-plan-sha256", preview["plan_sha256"]])
        self.assertEqual(denied.returncode, 2)
        created = self.parse_success(
            run_cli(
                [
                    "backup",
                    *self.roots(),
                    "--expected-plan-sha256",
                    preview["plan_sha256"],
                    "--confirm-write",
                ]
            )
        )
        self.assertEqual(created["verification"], "passed")
        archive = Path(created["archive"])
        verified = self.parse_success(run_cli(["verify-backup", "--archive", str(archive)]))
        self.assertEqual(verified["archive_sha256"], created["archive_sha256"])
        with zipfile.ZipFile(archive) as backup:
            self.assertNotIn("payload/workspace/website/.env", backup.namelist())
            self.assertIn("payload/project/src/pages/index.astro", backup.namelist())

    def test_backup_plan_expires_when_source_changes(self) -> None:
        self.configure()
        preview = self.parse_success(run_cli(["backup-plan", *self.roots()]))
        (self.project / "src/pages/index.astro").write_text("<h1>已變更</h1>\n", encoding="utf-8")
        stale = run_cli(
            [
                "backup",
                *self.roots(),
                "--expected-plan-sha256",
                preview["plan_sha256"],
                "--confirm-write",
            ]
        )
        self.assertEqual(stale.returncode, 2)
        self.assertIn("已失效", stale.stderr)

    def test_restore_only_creates_new_isolated_tree(self) -> None:
        self.configure()
        preview = self.parse_success(run_cli(["backup-plan", *self.roots()]))
        created = self.parse_success(
            run_cli(["backup", *self.roots(), "--expected-plan-sha256", preview["plan_sha256"], "--confirm-write"])
        )
        recovery = self.root / "recovery"
        restore_preview = self.parse_success(
            run_cli(["restore-plan", "--archive", created["archive"], "--recovery-dir", str(recovery)])
        )
        restored = self.parse_success(
            run_cli(
                [
                    "restore",
                    "--archive",
                    created["archive"],
                    "--recovery-dir",
                    str(recovery),
                    "--expected-plan-sha256",
                    restore_preview["plan_sha256"],
                    "--confirm-write",
                ]
            )
        )
        self.assertFalse(restored["overwrote_existing"])
        self.assertTrue((recovery / "workspace/website/config.json").is_file())
        self.assertTrue((recovery / "project/src/pages/index.astro").is_file())
        rejected = run_cli(["restore-plan", "--archive", created["archive"], "--recovery-dir", str(recovery)])
        self.assertEqual(rejected.returncode, 2)

    def test_verify_rejects_zip_slip_path(self) -> None:
        archive = self.root / "unsafe.zip"
        manifest = {
            "schema_version": 1,
            "format": "website-operations-backup",
            "created_at": "2026-09-13T00:00:00+00:00",
            "files": [],
        }
        with zipfile.ZipFile(archive, "w") as target:
            target.writestr("backup-manifest.json", json.dumps(manifest))
            target.writestr("../escape.txt", "unsafe")
        rejected = run_cli(["verify-backup", "--archive", str(archive)])
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("不安全路徑", rejected.stderr)

    def test_windows_paths_rejected_before_restore(self) -> None:
        for unsafe in ("payload/project/C:/escape.txt", "payload/project/a:stream", "payload/project/CON", "payload/project/a.", "payload/project/a//b"):
            with self.subTest(path=unsafe):
                archive = self.root / "unsafe.zip"
                manifest = {"schema_version": 1, "format": operations.BACKUP_FORMAT, "files": [
                    {"archive_path": unsafe, "size": 1, "sha256": hashlib.sha256(b"x").hexdigest()}
                ]}
                with zipfile.ZipFile(archive, "w") as target:
                    target.writestr("backup-manifest.json", json.dumps(manifest))
                    target.writestr(unsafe, b"x")
                with self.assertRaises(operations.OperationsError):
                    operations.verify_archive(archive)

    def test_restore_mkdir_race_preserves_other_directory(self) -> None:
        config = json.loads(self.candidate_path.read_text(encoding="utf-8"))
        plan = operations.backup_plan(self.workspace, self.project, config)
        created = operations.command_backup(self.workspace, self.project, config, plan["plan_sha256"], True)
        archive = Path(created["archive"])
        recovery = self.root / "race-recovery"
        preview = operations.restore_plan(archive, recovery)
        original_mkdir = Path.mkdir

        def competing_mkdir(path, *args, **kwargs):
            if path == recovery:
                original_mkdir(path)
                (path / "other-user.txt").write_text("preserve", encoding="utf-8")
                raise FileExistsError("created by another process")
            return original_mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", competing_mkdir):
            with self.assertRaises(operations.OperationsError):
                operations.command_restore(archive, recovery, preview["plan_sha256"], True)
        self.assertEqual((recovery / "other-user.txt").read_text(encoding="utf-8"), "preserve")

    def test_backup_does_not_delete_existing_temporary_file(self) -> None:
        config = json.loads(self.candidate_path.read_text(encoding="utf-8"))
        plan = operations.backup_plan(self.workspace, self.project, config)
        with mock.patch.object(operations, "datetime") as time_mock:
            time_mock.now.return_value.strftime.return_value = "fictional-fixed"
            time_mock.now.return_value.replace.return_value.isoformat.return_value = "fictional-time"
            temporary = self.workspace / operations.DEFAULT_BACKUP_DIR / f"website-backup-fictional-fixed-{plan['plan_sha256'][:8]}.zip.tmp"
            temporary.parent.mkdir(parents=True)
            temporary.write_bytes(b"preserve")
            with self.assertRaises(operations.OperationsError):
                operations.command_backup(self.workspace, self.project, config, plan["plan_sha256"], True)
            self.assertEqual(temporary.read_bytes(), b"preserve")

    def test_health_check_and_bounded_history(self) -> None:
        self.configure()
        server = ThreadingHTTPServer(("127.0.0.1", 0), FictionalSiteHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            checked = self.parse_success(run_cli(["check", *self.roots(), "--url", base_url]))
            self.assertTrue(checked["passed"])
            self.assertFalse(checked["submitted_forms"])
            self.assertNotIn("recorded_to", checked)
            recorded = self.parse_success(
                run_cli(["check", *self.roots(), "--url", base_url, "--record", "--confirm-write"])
            )
            self.assertEqual(recorded["recorded_to"], ".local/website/operations/health-history.json")
            status = self.parse_success(run_cli(["status", *self.roots()]))
            self.assertTrue(status["latest_health"]["passed"])
        finally:
            server.shutdown()
            server.server_close()

    def test_health_failure_has_distinct_exit_code(self) -> None:
        self.configure()
        server = ThreadingHTTPServer(("127.0.0.1", 0), FictionalSiteHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            candidate = json.loads((self.workspace / "website/operations.json").read_text(encoding="utf-8"))
            candidate["health"]["checks"][0]["required_text"] = "不存在的字串"
            self.candidate_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            preview = self.parse_success(run_cli(["configure-plan", *self.roots(), "--candidate", str(self.candidate_path)]))
            self.parse_success(
                run_cli(
                    [
                        "configure",
                        *self.roots(),
                        "--candidate",
                        str(self.candidate_path),
                        "--expected-plan-sha256",
                        preview["plan_sha256"],
                        "--confirm-write",
                    ]
                )
            )
            failed = run_cli(["check", *self.roots(), "--url", f"http://127.0.0.1:{server.server_port}"])
            self.assertEqual(failed.returncode, 3, failed.stderr)
            self.assertFalse(json.loads(failed.stdout)["passed"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
