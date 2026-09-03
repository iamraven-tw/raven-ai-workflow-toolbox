#!/usr/bin/env python3
"""驗證 Google 工具自動化候選版的契約、技能、連結與公開邊界。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import tomllib


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TOOLBOX_ROOT = PACKAGE_ROOT.parents[1]
MANIFEST_PATH = PACKAGE_ROOT / "install.manifest.toml"
ROUTER_ROOT = PACKAGE_ROOT / "skills" / "google-workflow-router"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "routing-cases.json"
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
REAL_GOOGLE_RESOURCE = re.compile(
    r"https://(?:docs\.google\.com/(?:spreadsheets|document|forms)/d/|"
    r"script\.google\.com/(?:home/projects/|macros/s/))[A-Za-z0-9_-]{12,}"
)
PRIVATE_MARKERS = (
    "/" + "Users/",
    "@" + "gmail.com",
    "newsletter" + "-current",
    "approved" + "_locked",
    "taiwan" + "kaiyuan",
)
EXPECTED_LEARN_REF = "7d50a7bfcfbe41ea9d88c2aef8f11200871433a3"
EXPECTED_LEARN_TREE = "ef6e45626d59ae18745eb5c7245de0b3f2e48cc9"
EXPECTED_LICENSE_SHA256 = "39106e322b00c852430a6e6fca5f93b1465b24a6abd8a6d723df99ae9d2eaa15"
EXPECTED_SKILLS = {
    "google-apps-script-project-development",
    "google-apps-script-teaching",
    "google-apps-script-debugging",
    "google-docs-layout",
}
EXPECTED_ROUTES = {
    "GAS",
    "WORKSPACE_API",
    "CLOUD_RUN_SERVICE",
    "CLOUD_RUN_JOB",
    "SPECIALIST_REVIEW",
}


def fail(message: str) -> None:
    """以單一例外中止目前驗證並保留原因。"""

    raise AssertionError(message)


def sha256_file(file_path: Path) -> str:
    """計算檔案 SHA-256。"""

    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def run_git(repository: Path, *arguments: str) -> str:
    """執行唯讀 Git 驗證。"""

    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_manifest() -> dict[str, Any]:
    """確認候選版、固定依賴、用戶端與支援狀態一致。"""

    manifest = tomllib.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("status") != "ready_for_external_acceptance":
        fail("manifest 尚未達到 ready_for_external_acceptance")
    if manifest.get("installable") is not True:
        fail("Agent 端門檻完成後必須 installable = true")
    if manifest.get("support_level") != "installable_candidate_not_formally_supported":
        fail("候選安裝與正式支援沒有分開")
    if manifest.get("environment", {}).get("officially_supported") != []:
        fail("外部實機驗收前不得宣稱任何正式支援環境")

    integration = manifest["integration"]["learn_gas"]
    if integration.get("ref") != EXPECTED_LEARN_REF:
        fail("Learn-GAS commit 漂移")
    if integration.get("tree") != EXPECTED_LEARN_TREE:
        fail("Learn-GAS tree 漂移")
    if integration.get("license_sha256") != EXPECTED_LICENSE_SHA256:
        fail("Learn-GAS LICENSE SHA-256 漂移")
    if integration.get("vendor_source") is not False or integration.get("auto_update") is not False:
        fail("Learn-GAS 必須維持外部單一來源且不得自動更新")

    sources = manifest["managed_sources"]
    if set(sources.get("learn_gas_skills", [])) != EXPECTED_SKILLS:
        fail("Learn-GAS 四個技能清單不正確")
    if sources.get("learn_gas_shared_files") != ["learner-facing-terminology.md"]:
        fail("Learn-GAS 共用術語檔清單不正確")

    clients = {client["id"]: client for client in manifest["client_targets"]}
    expected_paths = {
        "codex": ("<workspace>/.agents/skills", "$HOME/.agents/skills"),
        "claude-code": ("<workspace>/.claude/skills", "$HOME/.claude/skills"),
        "google-antigravity": ("<workspace>/.agents/skills", "$HOME/.gemini/config/skills"),
    }
    for client_id, (workspace_path, user_path) in expected_paths.items():
        client = clients.get(client_id, {})
        if client.get("workspace_path") != workspace_path or client.get("user_path") != user_path:
            fail(f"{client_id} 的官方技能入口不正確")

    gates = {gate["id"]: gate["status"] for gate in manifest["readiness_gates"]}
    for gate_id in (
        "manifest_docs_privacy_license",
        "learn_gas_fixed_source_and_upstream_tests",
        "install_repeat_conflict_update_rollback_remove",
    ):
        if gates.get(gate_id) != "complete":
            fail(f"Agent 端門檻尚未完成：{gate_id}")
    if gates.get("agent_discovery") != (
        "complete_with_antigravity_authenticated_discovery_pending_external_acceptance"
    ):
        fail("三種 Agent 的本機發現與外部驗收邊界不正確")
    if gates.get("external_machine_google_acceptance") != (
        "pending_user_acceptance_on_separate_computer_or_account"
    ):
        fail("最終外部驗收狀態不正確")
    return manifest


def parse_frontmatter(skill_path: Path) -> dict[str, str]:
    """解析本候選版只使用的簡單 SKILL.md 前置資料。"""

    content = skill_path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(content)
    if not match:
        fail("google-workflow-router 缺少有效 YAML frontmatter")
    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", maxsplit=1)
        values[key.strip()] = value.strip()
    return values


def validate_skill() -> None:
    """確認路由技能有獨立缺口、必要參考與 OpenAI metadata。"""

    skill_path = ROUTER_ROOT / "SKILL.md"
    metadata = parse_frontmatter(skill_path)
    if metadata.get("name") != "google-workflow-router":
        fail("路由技能名稱不正確")
    if not metadata.get("description") or len(metadata["description"]) < 40:
        fail("路由技能 description 不足以辨識觸發情境")

    references = {
        "decision-record.md",
        "apps-script-route.md",
        "workspace-api-oauth-route.md",
        "cloud-run-route.md",
        "completion-gates.md",
    }
    actual_references = {path.name for path in (ROUTER_ROOT / "references").glob("*.md")}
    if actual_references != references:
        fail("路由技能參考檔不完整或出現未記錄檔案")

    openai_yaml = (ROUTER_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if "$google-workflow-router" not in openai_yaml:
        fail("OpenAI default_prompt 沒有明確提到技能名稱")
    if "allow_implicit_invocation: true" not in openai_yaml:
        fail("OpenAI implicit invocation 設定不正確")

    skill_text = skill_path.read_text(encoding="utf-8")
    required_terms = (
        "google-apps-script-project-development",
        "google-apps-script-teaching",
        "google-apps-script-debugging",
        "google-docs-layout",
        "Workspace API",
        "Cloud Run service",
        "Cloud Run job",
        "Cloud Scheduler",
        "需要專門設計",
    )
    for term in required_terms:
        if term not in skill_text:
            fail(f"路由技能缺少必要分流：{term}")

    for copied_skill in EXPECTED_SKILLS:
        if (PACKAGE_ROOT / "skills" / copied_skill).exists():
            fail(f"Toolbox 不得複製 Learn-GAS 技能：{copied_skill}")


def validate_fixture() -> None:
    """確認虛構路由案例涵蓋五種主要結果且不含真實資源。"""

    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or len(cases) < 8:
        fail("路由 fixture 數量不足")
    routes = {case.get("expected_route") for case in cases}
    if routes != EXPECTED_ROUTES:
        fail(f"路由 fixture 未完整涵蓋 MVP：{routes}")
    gas_skills = {
        case.get("expected_skill")
        for case in cases
        if case.get("expected_route") == "GAS"
    }
    if gas_skills != EXPECTED_SKILLS:
        fail(f"路由 fixture 未涵蓋 Learn-GAS 四個技能：{gas_skills}")
    scheduled_jobs = [
        case for case in cases if case.get("expected_route") == "CLOUD_RUN_JOB"
    ]
    if not scheduled_jobs or not all(case.get("expected_scheduler") is True for case in scheduled_jobs):
        fail("Cloud Run job fixture 沒有明確驗證 Scheduler 分流")
    specialist_cases = [
        case for case in cases if case.get("expected_route") == "SPECIALIST_REVIEW"
    ]
    if not specialist_cases or not all(case.get("reason") for case in specialist_cases):
        fail("專門審查 fixture 缺少停止原因")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)):
        fail("路由 fixture ID 重複")
    serialized = json.dumps(cases, ensure_ascii=False)
    if "虛構" not in serialized and "測試" not in serialized:
        fail("路由 fixture 沒有明確的虛構或測試資料")
    if REAL_GOOGLE_RESOURCE.search(serialized):
        fail("路由 fixture 含真實 Google 資源網址")


def validate_required_files_and_links() -> None:
    """檢查套件契約檔案與所有 Markdown 相對連結。"""

    required = (
        PACKAGE_ROOT / "README.md",
        PACKAGE_ROOT / "INSTALL.md",
        PACKAGE_ROOT / "THIRD_PARTY_NOTICES.md",
        PACKAGE_ROOT / "docs" / "architecture.md",
        PACKAGE_ROOT / "docs" / "inventory.md",
        PACKAGE_ROOT / "docs" / "mvp-boundary.md",
        PACKAGE_ROOT / "docs" / "compatibility.md",
        PACKAGE_ROOT / "scripts" / "manage_install.py",
        PACKAGE_ROOT / "tests" / "acceptance-checklist.md",
        TOOLBOX_ROOT / "docs" / "decisions" / "0002-learn-gas-integration.md",
        TOOLBOX_ROOT / "LICENSE",
    )
    for file_path in required:
        if not file_path.is_file():
            fail(f"缺少必要檔案：{file_path}")

    license_text = (TOOLBOX_ROOT / "LICENSE").read_text(encoding="utf-8")
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        fail("Toolbox 根授權不是 Apache License 2.0")

    markdown_files = list(PACKAGE_ROOT.rglob("*.md"))
    markdown_files.extend(
        [
            TOOLBOX_ROOT / "README.md",
            TOOLBOX_ROOT / "INSTALL.md",
            TOOLBOX_ROOT / "THIRD_PARTY_NOTICES.md",
            TOOLBOX_ROOT / "docs" / "decisions" / "0002-learn-gas-integration.md",
        ]
    )
    for file_path in sorted(set(markdown_files)):
        content = file_path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(content):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative_target = target.split("#", maxsplit=1)[0].strip("<>")
            if relative_target and not (file_path.parent / relative_target).resolve().exists():
                fail(f"失效的相對連結 {target!r}：{file_path.relative_to(PACKAGE_ROOT)}")


def validate_privacy() -> None:
    """掃描公開套件與整合 ADR 中不應出現的私人內容或資源網址。"""

    files = [
        path
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file() and path.suffix in {".md", ".toml", ".json", ".py", ".yaml"}
    ]
    files.extend(
        [
            TOOLBOX_ROOT / "README.md",
            TOOLBOX_ROOT / "INSTALL.md",
            TOOLBOX_ROOT / "THIRD_PARTY_NOTICES.md",
            TOOLBOX_ROOT / "docs" / "decisions" / "0002-learn-gas-integration.md",
        ]
    )
    for file_path in files:
        content = file_path.read_text(encoding="utf-8")
        for marker in PRIVATE_MARKERS:
            if marker in content:
                fail(f"發現不應公開的內容 {marker!r}：{file_path}")
        if REAL_GOOGLE_RESOURCE.search(content):
            fail(f"發現疑似真實 Google 資源網址：{file_path}")


def validate_completion_boundaries() -> None:
    """確認本機、登入、OAuth、部署與人工驗收沒有被合併。"""

    completion = (
        ROUTER_ROOT / "references" / "completion-gates.md"
    ).read_text(encoding="utf-8")
    required = ("本機程式", "Google 登入", "OAuth", "遠端同步／部署", "人工驗收")
    for label in required:
        if label not in completion:
            fail(f"完成狀態缺少：{label}")
    install_text = (PACKAGE_ROOT / "INSTALL.md").read_text(encoding="utf-8")
    if "技能出現在清單中不等於 Google 已登入" not in install_text:
        fail("INSTALL 沒有區分技能發現與 Google 登入")


def validate_learn_gas_source(source_root: Path) -> None:
    """核對使用者傳入的真實固定 Learn-GAS clone。"""

    resolved = source_root.expanduser().resolve()
    if run_git(resolved, "rev-parse", "HEAD") != EXPECTED_LEARN_REF:
        fail("實際 Learn-GAS clone 的 commit 不符")
    if run_git(resolved, "rev-parse", "HEAD^{tree}") != EXPECTED_LEARN_TREE:
        fail("實際 Learn-GAS clone 的 tree 不符")
    if run_git(resolved, "status", "--porcelain", "--untracked-files=all"):
        fail("實際 Learn-GAS clone 不是乾淨狀態")
    if sha256_file(resolved / "LICENSE") != EXPECTED_LICENSE_SHA256:
        fail("實際 Learn-GAS LICENSE SHA-256 不符")
    for skill_name in EXPECTED_SKILLS:
        if not (resolved / "skills" / skill_name / "SKILL.md").is_file():
            fail(f"實際 Learn-GAS 缺少技能：{skill_name}")
    if not (resolved / "skills" / "learner-facing-terminology.md").is_file():
        fail("實際 Learn-GAS 缺少共用術語檔")


def validate_manager_help() -> None:
    """確認五個生命週期命令可由標準 Python 啟動。"""

    result = subprocess.run(
        ["python3", str(PACKAGE_ROOT / "scripts" / "manage_install.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    for command in ("install", "update", "rollback", "remove", "status"):
        if command not in result.stdout:
            fail(f"安裝管理器缺少命令：{command}")


def parse_args() -> argparse.Namespace:
    """解析可選的固定 Learn-GAS 來源。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--learn-gas-source",
        type=Path,
        help="已驗證的固定 Learn-GAS clone；提供時會核對 commit、tree 與授權",
    )
    return parser.parse_args()


def main() -> None:
    """執行全部公開候選契約驗證。"""

    args = parse_args()
    checks = (
        validate_manifest,
        validate_skill,
        validate_fixture,
        validate_required_files_and_links,
        validate_privacy,
        validate_completion_boundaries,
        validate_manager_help,
    )
    try:
        for check in checks:
            check()
        if args.learn_gas_source:
            validate_learn_gas_source(args.learn_gas_source)
    except (
        AssertionError,
        KeyError,
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        tomllib.TOMLDecodeError,
    ) as error:
        print(f"失敗：{error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("通過：Google 工具自動化候選版契約、來源、技能、連結與公開邊界有效。")


if __name__ == "__main__":
    main()
