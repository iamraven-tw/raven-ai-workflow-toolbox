#!/usr/bin/env python3
"""驗證 AI 剪片公開候選版的契約、連結、fixture 與隱私邊界。"""

from __future__ import annotations

import json
import hashlib
import re
import sys
import tomllib
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PACKAGE_ROOT / "install.manifest.toml"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "synthetic-project"
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PRIVATE_MARKERS = (
    "/" + "Users/",
    "@" + "gmail.com",
    "newsletter" + "-current",
    "approved" + "_locked",
)


def fail(message: str) -> None:
    """累積前不需要繼續的契約錯誤。"""
    raise AssertionError(message)


def validate_manifest() -> None:
    """確認可安裝候選狀態與固定依賴沒有漂移。"""
    manifest = tomllib.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("status") != "ready_for_external_acceptance":
        fail("manifest 狀態不是 ready_for_external_acceptance")
    if manifest.get("installable") is not True:
        fail("外部驗收候選版必須 installable = true")
    if manifest.get("support_level") != "installable_candidate_not_formally_supported":
        fail("候選安裝與正式支援的狀態沒有分開")
    if manifest["environment"].get("officially_supported") != []:
        fail("外部驗收前不得宣稱任何正式支援環境")

    overlay = manifest["compatibility_overlay"]
    overlay_path = PACKAGE_ROOT / overlay["path"]
    if hashlib.sha256(overlay_path.read_bytes()).hexdigest() != overlay["sha256"]:
        fail("跨平台補丁 SHA-256 不符")
    patch = json.loads(overlay_path.read_text(encoding="utf-8"))
    license_text = (overlay_path.parent / "LICENSE-Video-Use.txt").read_text(encoding="utf-8")
    if "Copyright (c) 2026 Browser Use" not in license_text or "Permission is hereby granted" not in license_text:
        fail("散布 Video-Use 補丁時缺少上游 MIT 授權")
    if patch["base_commit"] != "da344098518230f69ff70f78a4860d4904e9e6cb":
        fail("補丁沒有對應固定上游 commit")
    paths = {entry["path"] for entry in patch["files"]}
    if not {"requirements/asr-runtime-windows.lock", "requirements/ckip-runtime-windows.lock", "requirements/opencc-windows.lock", "helpers/platform_support.py", "WINDOWS.md"} <= paths:
        fail("跨平台補丁缺少必要依賴或執行契約")
    for asset in manifest["windows"]["assets"].values():
        if not asset["url"].startswith("https://github.com/") or not re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]) or not asset["license"]:
            fail("Windows 工具缺少固定來源、完整雜湊或授權")

    dependencies = {item["id"]: item for item in manifest["dependencies"]}
    expected_refs = {
        "uv": "0.12.7",
        "cpython-runtime": "3.12.14+20260825",
        "video-use": "da344098518230f69ff70f78a4860d4904e9e6cb",
        "qwen-asr-runtime": "0.0.6",
        "opencc": "1.4.2",
        "ffmpeg-full-libass": "9.0.1_1",
        "ckip-transformers": "0.3.4",
    }
    for dependency_id, expected in expected_refs.items():
        dependency = dependencies.get(dependency_id)
        if dependency is None:
            fail(f"manifest 缺少依賴：{dependency_id}")
        actual = dependency.get("ref")
        if actual != expected:
            fail(f"{dependency_id} ref 漂移：{actual!r} != {expected!r}")

    clients = {item["id"]: item for item in manifest["client_targets"]}
    expected_paths = {
        "codex": "<target-workspace>/.agents/skills/video-use",
        "claude-code": "<target-workspace>/.claude/skills/video-use",
        "google-antigravity": "<target-workspace>/.agents/skills/video-use",
    }
    for client_id, expected in expected_paths.items():
        if clients.get(client_id, {}).get("path") != expected:
            fail(f"{client_id} 的技能入口不正確")

    gates = {item["id"]: item["status"] for item in manifest["readiness_gates"]}
    if gates.get("automated_verification") != "complete":
        fail("Agent 端自動驗證門檻尚未完成")
    if gates.get("external_machine_human_acceptance") != "pending_user_acceptance_on_separate_computer":
        fail("外部電腦驗收狀態不正確")


def validate_fixture() -> None:
    """確認公開 fixture 是中性、有效且詞級時間軸單調。"""
    required = (
        FIXTURE_ROOT / "README.md",
        FIXTURE_ROOT / "edl.json",
        FIXTURE_ROOT / "subtitle-protected-phrases.json",
        FIXTURE_ROOT / "subtitle-ckip-words.json",
        FIXTURE_ROOT / "transcripts" / "take.json",
    )
    for file_path in required:
        if not file_path.is_file():
            fail(f"缺少公開 fixture：{file_path.relative_to(PACKAGE_ROOT)}")
    transcript = json.loads(required[-1].read_text(encoding="utf-8"))
    if transcript.get("language") != "zh-Hant-TW":
        fail("fixture 不是臺灣繁體中文")
    previous_end = 0.0
    for word in transcript.get("words", []):
        start = float(word["start"])
        end = float(word["end"])
        if start < previous_end or end <= start:
            fail("fixture 詞級時間軸重疊或倒退")
        previous_end = end
    if "公開測試流程" not in transcript.get("text", ""):
        fail("fixture 缺少預期的中性測試片語")


def validate_markdown_and_privacy() -> None:
    """檢查相對連結與不應公開的維護者內容。"""
    for file_path in sorted(PACKAGE_ROOT.rglob("*")):
        if not file_path.is_file() or file_path.suffix not in {".md", ".toml", ".json", ".py"}:
            continue
        content = file_path.read_text(encoding="utf-8")
        for marker in PRIVATE_MARKERS:
            if marker in content:
                fail(f"發現不應公開的內容 {marker!r}：{file_path.relative_to(PACKAGE_ROOT)}")
        if file_path.suffix != ".md":
            continue
        for target in MARKDOWN_LINK.findall(content):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative_target = target.split("#", maxsplit=1)[0].strip("<>")
            if relative_target and not (file_path.parent / relative_target).resolve().exists():
                fail(
                    f"失效的相對連結 {target!r}：{file_path.relative_to(PACKAGE_ROOT)}"
                )


def main() -> None:
    checks = (validate_manifest, validate_fixture, validate_markdown_and_privacy)
    try:
        for check in checks:
            check()
    except (AssertionError, KeyError, OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"失敗：{error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("通過：AI 剪片候選版契約、公開 fixture、連結與隱私邊界有效。")


if __name__ == "__main__":
    main()
