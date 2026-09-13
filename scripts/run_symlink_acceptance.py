#!/usr/bin/env python3
"""維護者的嚴格 symlink 補驗：只跑隔離案例，任何 skip 都不是成功。"""

import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "ai-knowledge-base": [
        "test_install_lifecycle.InstallLifecycleTest.test_unknown_symlink_stops",
    ],
    "social-media": [
        "test_community_queue.CommunityTests.test_symlinks_are_rejected",
        "test_content_publishing.PublishingTests.test_symlink_is_not_followed",
        "test_credential_store.CredentialStoreTests.test_broken_symlink_stops",
        "test_credential_store.CredentialStoreTests.test_symlink_registry_path_is_rejected",
        "test_image_production.ImageProductionTests.test_symlink_is_rejected",
        "test_image_production.ImageProductionTests.test_symlink_output_parent_is_rejected",
        "test_performance_review.PerformanceTests.test_symlinks_are_rejected",
        "test_workspace_config.WorkspaceConfigurationTests.test_intermediate_symlink_cannot_redirect_configuration",
    ],
    "website-building": [
        "test_workspace_config.WorkspaceConfigurationTests.test_intermediate_symlink_cannot_redirect_configuration",
        "test_scaffold_site.ScaffoldTests.test_rejects_symlink_target",
        "test_style_gallery.StyleGalleryTests.test_symlink_targets_stop",
    ],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = args.report.resolve()
    if not report.is_relative_to(ROOT / ".local") or report.exists():
        parser.error("報告必須是 repository .local 內的新檔案")
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    result = {"timestamp": datetime.now(timezone.utc).isoformat(), "platform": sys.platform,
              "python": sys.version.split()[0], "result": "blocked", "packs": []}
    try:
        # 真實建立連結，不能以 API 存在、mock、junction 或 skip 取代。
        with tempfile.TemporaryDirectory(prefix="fictional-symlink-preflight-") as temporary:
            root = Path(temporary)
            (root / "target").mkdir()
            (root / "link").symlink_to(root / "target", target_is_directory=True)
            if not (root / "link").is_symlink():
                raise OSError("symlink preflight did not create a symbolic link")
        for pack, cases in CASES.items():
            names = [f"skill-packs.{pack}.tests.{case}" for case in cases]
            suite = unittest.defaultTestLoader.loadTestsFromNames(names)
            outcome = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
            result["packs"].append({
                "pack": pack, "tests": outcome.testsRun,
                "failures": len(outcome.failures), "errors": len(outcome.errors),
                "skipped": len(outcome.skipped),
                "problems": [str(test) for test, _ in outcome.failures + outcome.errors + outcome.skipped],
            })
        passed = all(p["tests"] == len(CASES[p["pack"]]) and not
                     (p["failures"] or p["errors"] or p["skipped"]) for p in result["packs"])
        result["result"] = "passed" if passed else "failed"
    except OSError as error:
        result["reason"] = "symlink_preflight_failed"
        result["winerror"] = getattr(error, "winerror", None)
    report.parent.mkdir(parents=True, exist_ok=True)
    # 排他建立，不覆蓋先前驗收；只輸出案例名稱及結果，不寫 traceback／私人資料。
    with report.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["result"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
