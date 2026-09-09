#!/usr/bin/env python3
"""驗證已實作社群媒體技能的結構、邊界與公開內容。"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTED = {"social-media-setup", "social-content-planning", "social-content-writing", "social-image-production", "social-content-publishing", "social-community-management", "social-performance-analysis"}
PLANNED = set()
PLATFORMS = {"youtube", "instagram", "facebook", "threads", "substack"}
TEXT_SUFFIXES = {".md", ".toml", ".py", ".json", ".yaml", ".yml", ".txt", ".html", ".css", ".svg"}
PRIVATE_PATTERNS = (
    "/" + "Users/",
    "/" + "Volumes/",
    "C:\\" + "Users\\",
    "kai" + "yuankang",
    "iam" + "raven",
    "ravan" + "-ai",
    "macmini/" + "newsletter",
    ".hermes" + "/",
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bya29\.[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class ValidationError(RuntimeError):
    """代表公開候選版可修正的靜態問題。"""


def read_manifest() -> dict:
    """讀取套件 manifest。"""

    with (ROOT / "install.manifest.toml").open("rb") as handle:
        return tomllib.load(handle)


def parse_skill_name(skill_file: Path) -> str:
    """從技能 frontmatter 讀取名稱。"""

    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"^---\n(?P<header>.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValidationError(f"缺少有效 frontmatter：{skill_file}")
    name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", match.group("header"), re.MULTILINE)
    if not name:
        raise ValidationError(f"frontmatter 缺少 name：{skill_file}")
    return name.group(1)


def validate_manifest(manifest: dict) -> None:
    """確認只把已實作的候選技能列入安裝。"""

    expected = {
        "schema_version": 1,
        "manifest_type": "social-media-install",
        "status": "local_candidate_full_pack",
        "installable": True,
        "requires_network": False,
        "support_level": "full_pack_installable_candidate_not_formally_supported",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValidationError(f"manifest.{key} 不符")
    manifest_date = manifest.get("checked_on")
    if not isinstance(manifest_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", manifest_date):
        raise ValidationError("manifest.checked_on 必須是 ISO 日期")
    implemented = {record.get("id") for record in manifest.get("skills", [])}
    planned = {record.get("id") for record in manifest.get("planned_skills", [])}
    if implemented != IMPLEMENTED or planned != PLANNED or implemented & planned:
        raise ValidationError("已完成與待建立技能集合不符")
    if set(manifest.get("installation", {}).get("managed_entries", [])) != IMPLEMENTED:
        raise ValidationError("安裝器只能管理目前已建立的七個技能")
    if any(record.get("status") != "local_candidate_flow_reviewed_live_pending"
           for record in manifest.get("skills", [])):
        raise ValidationError("七技能必須一致區分流程已確認、本機候選與實機待驗")
    workflow_review = manifest.get("workflow_review", {})
    expected_review = {
        "status": "all_seven_reviewed_and_allowed_to_continue",
        "meaning": "described_user_flow_only_not_agent_behavior_live_account_or_formal_support",
        "record": "docs/workflow-review-status.md",
        "reviewed_skills": [
            "social-media-setup", "social-content-planning", "social-content-writing",
            "social-image-production", "social-content-publishing",
            "social-community-management", "social-performance-analysis",
        ],
        "live_acceptance": "not_performed",
    }
    if workflow_review != expected_review:
        raise ValidationError("manifest 的七技能流程確認狀態不完整")
    review_path = ROOT / workflow_review["record"]
    if not review_path.is_file():
        raise ValidationError("缺少七技能流程確認現況文件")
    review_text = review_path.read_text(encoding="utf-8")
    for phrase in ("流程已確認", "不表示真實 Agent", "交易整合已通過本機虛構測試", "未執行"):
        if phrase not in review_text:
            raise ValidationError(f"流程確認現況文件缺少邊界：{phrase}")
    package_preflight = manifest.get("package_preflight", {})
    expected_preflight = {
        "status": "current_root_agent_fictional_forward_test_passed_independent_and_live_not_performed",
        "transcript": "tests/agent-dialogue-preflight.md",
        "validator": "tests/test_agent_dialogue_preflight.py",
        "verification": "docs/agent-dialogue-preflight-local-verification.md",
        "case_count": 10,
        "external_actions": False,
        "independent_agent_evaluation": "not_performed",
        "live_installed_agent_discovery": "not_performed",
    }
    if package_preflight != expected_preflight:
        raise ValidationError("七技能虛構對話前測狀態或限制不完整")
    for key in ("transcript", "validator", "verification"):
        if not (ROOT / package_preflight[key]).is_file():
            raise ValidationError("對話前測 manifest 指向不存在的檔案")
    transcript = (ROOT / package_preflight["transcript"]).read_text(encoding="utf-8")
    if (transcript.count("## CASE ") != package_preflight["case_count"]
            or "不是獨立模型測試" not in transcript
            or "沒有網路、登入、OAuth" not in transcript):
        raise ValidationError("對話前測必須保留真實回合數與未驗收邊界")
    package_regression = manifest.get("package_regression", {})
    expected_regression = {
        "status": "passed_local_static_install_and_fictional_suite_live_not_performed",
        "verification": "docs/package-regression-local-verification.md",
        "full_suite_total": 382,
        "full_suite_passed": 381,
        "full_suite_skipped": 1,
        "install_lifecycle_total": 13,
        "install_lifecycle_passed": 13,
        "skill_format_passed": 7,
        "broken_symlinks": 0,
        "diff_check": "passed",
    }
    if package_regression != expected_regression:
        raise ValidationError("整包回歸結果必須對應本次實際執行數字")
    if not (ROOT / package_regression["verification"]).is_file():
        raise ValidationError("缺少整包回歸驗證紀錄")
    candidate_handoff = manifest.get("candidate_handoff", {})
    expected_handoff = {
        "status": "local_candidate_closeout_complete_live_acceptance_pending",
        "record": "docs/local-candidate-handoff.md",
        "local_sections": [
            "initialization_and_document_alignment", "publishing", "community",
            "performance", "package_preflight_image_preparation_and_regression",
        ],
        "conditional_scope_policy": "active_only_when_a_real_extension_need_appears",
        "public_private_sync": "disabled_independent_snapshots",
        "live_acceptance": "deferred_requires_separate_authorization",
        "commit": "not_performed",
        "push": "not_performed",
        "release": "not_performed",
    }
    if candidate_handoff != expected_handoff:
        raise ValidationError("本機候選交付狀態或外部操作邊界不完整")
    handoff_path = ROOT / candidate_handoff["record"]
    if not handoff_path.is_file():
        raise ValidationError("缺少本機候選交付紀錄")
    handoff_text = handoff_path.read_text(encoding="utf-8")
    for phrase in (
            "381 項通過", "原生憑證探測", "本機技能發現", "API／第三方套件可安裝",
            "使用者登入與 OAuth", "平台讀取", "測試發布／外部寫入",
            "另一臺電腦驗收", "正式公開支援", "沒有建立同步", "LIVE-01"):
        if phrase not in handoff_text:
            raise ValidationError(f"本機候選交付紀錄缺少分層或邊界：{phrase}")
    live_plan = manifest.get("live_acceptance_plan", {})
    live_stages = [f"LIVE-{number:02d}" for number in range(1, 9)]
    expected_live_plan = {
        "status": "prepared_not_authorized_not_started",
        "runbook": "docs/live-acceptance-runbook.md",
        "result_template": "docs/live-acceptance-result-template.json",
        "result_schema_version": 1,
        "stages": live_stages,
        "per_stage_authorization": True,
        "external_actions_performed": False,
    }
    if live_plan != expected_live_plan:
        raise ValidationError("集中實機驗收計畫必須保持已準備、未授權且未開始")
    runbook_path = ROOT / live_plan["runbook"]
    result_template_path = ROOT / live_plan["result_template"]
    if not runbook_path.is_file() or not result_template_path.is_file():
        raise ValidationError("集中實機驗收手冊或結果範本不存在")
    runbook_text = runbook_path.read_text(encoding="utf-8")
    for stage in live_stages:
        if f"## {stage}：" not in runbook_text:
            raise ValidationError(f"集中實機驗收手冊缺少階段：{stage}")
    for phrase in (
            "未授權，未開始", "每個 `LIVE-*` 都是獨立確認關卡", "不得盲目重送",
            "對方先發起", "24 小時內", "不建 Webhook", "commit、push、版本標記及發布各自分開確認"):
        if phrase not in runbook_text:
            raise ValidationError(f"集中實機驗收手冊缺少邊界：{phrase}")
    try:
        result_template = json.loads(result_template_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValidationError("集中實機驗收結果範本不是有效 JSON") from None
    if (result_template.get("schema_version") != live_plan["result_schema_version"]
            or list(result_template.get("stages", {})) != live_stages
            or result_template.get("overall_status") != "not_run"
            or any(record.get("status") != "not_run"
                   for record in result_template.get("stages", {}).values())
            or any(result_template.get("external_actions", {}).values())
            or result_template.get("record_scope") !=
            "private_acceptance_record_do_not_commit_to_public_toolbox"):
        raise ValidationError("集中實機驗收結果範本不得預先宣稱任何實機或外部結果")
    if manifest.get("workspace", {}).get("configuration_schema_version") != 5:
        raise ValidationError("manifest 必須宣告一般設定 schema version 5")
    image_production = manifest.get("image_production", {})
    expected_image_production = {
        "preference_field": "image_production",
        "routes": ["codex", "antigravity", "web", "html_css"],
        "router": "skills/social-image-production/scripts/image_routing.py",
        "web_default": "prompt_handoff_browser_only_on_current_explicit_request",
        "html_export": "existing_authorized_local_renderer_only_live_not_verified",
        "legacy_config": "schema_3_4_read_compatible_schema_5_brand_preview_confirm_write",
        "brand_field": "brand_visual",
        "acceptance_brief": "skills/social-image-production/assets/acceptance-test-brief.json",
        "acceptance_square_brief": "skills/social-image-production/assets/acceptance-test-square-brief.json",
        "acceptance_overflow_brief": "skills/social-image-production/assets/acceptance-overflow-brief.json",
        "acceptance_web_prompts": "skills/social-image-production/assets/acceptance-web-prompts.md",
        "acceptance_html": "skills/social-image-production/assets/acceptance-information-card.html",
        "acceptance_result_template": "skills/social-image-production/assets/acceptance-result-template.json",
        "acceptance_reference": "skills/social-image-production/references/acceptance-testing.md",
        "acceptance_test": "tests/test_image_acceptance_preparation.py",
        "acceptance_status": "prepared_local_fixtures_routes_and_static_tests_live_generation_not_performed",
    }
    if image_production != expected_image_production:
        raise ValidationError("圖片四路驗收準備或實機狀態不完整")
    for key in ("router", "acceptance_brief", "acceptance_square_brief",
                "acceptance_overflow_brief", "acceptance_web_prompts",
                "acceptance_html", "acceptance_result_template",
                "acceptance_reference", "acceptance_test"):
        if not (ROOT / image_production[key]).is_file():
            raise ValidationError("圖片驗收 manifest 指向不存在的檔案")
    publishing = manifest.get("publishing", {})
    expected_publishing = {
        "helper": "skills/social-content-publishing/scripts/publish_job.py",
        "official_api_adapter": "skills/social-content-publishing/scripts/official_publish_api.py",
        "transaction_coordinator": "skills/social-content-publishing/scripts/publish_execute.py",
        "execution_sources": "skills/social-content-publishing/references/execution-sources.json",
        "official_spec_review": "docs/publishing-official-specs-local-verification.md",
        "platform_documents": ["youtube", "instagram", "facebook", "threads", "substack"],
        "official_api_platforms": ["youtube", "facebook", "instagram", "threads"],
        "substack_primary_interface": "controlled_browser_opencli",
        "execution": "agent_calls_transaction_coordinator_or_controlled_browser_after_begin",
        "local_helper": "preview_binding_lock_deduplication_stage_claim_checkpoint_readback_ledger",
        "network_access_by_helper": False,
        "network_access_by_official_api_adapter": True,
        "network_access_by_transaction_coordinator": True,
        "api_adapter_status": "implemented_local_fictional_tests_live_not_performed",
        "transaction_integration": "implemented_local_fictional_tests_live_not_performed",
        "format_routing_status": "verified_official_sources_local_contract_tests_live_not_performed",
        "live_status": "not_performed",
    }
    if publishing != expected_publishing:
        raise ValidationError("發布 manifest 必須區分低階 API 接線、交易整合與實機驗收")
    for key in ("helper", "official_api_adapter", "transaction_coordinator", "execution_sources",
                "official_spec_review"):
        if not (ROOT / publishing[key]).is_file():
            raise ValidationError("發布 manifest 指向不存在的本機資源")
    validate_publishing_sources(ROOT / publishing["execution_sources"])
    community = manifest.get("community", {})
    expected_community = {
        "helper": "skills/social-community-management/scripts/community_queue.py",
        "official_api_adapter": "skills/social-community-management/scripts/official_community_api.py",
        "transaction_coordinator": "skills/social-community-management/scripts/community_execute.py",
        "execution_sources": "skills/social-community-management/references/execution-sources.json",
        "sheets_api_adapter": "skills/social-community-management/scripts/official_sheets_api.py",
        "sheets_coordinator": "skills/social-community-management/scripts/community_sheets.py",
        "sheets_execution_source": "skills/social-community-management/references/sheets-execution-source.json",
        "manual_review_helper": "skills/social-community-management/scripts/manual_review.py",
        "review_execution_source": "skills/social-community-management/references/review-execution-source.json",
        "end_to_end_test": "tests/test_community_end_to_end.py",
        "platform_documents": ["youtube", "instagram", "facebook", "threads", "substack"],
        "scope": "owned_public_top_level_comments_and_approved_text_replies",
        "sheet_columns": ["訪客名稱", "原貼文內容", "原訪客留言", "原貼文摘要", "訪客留言網址", "AI 回覆草稿"],
        "sheet_input_option": "RAW",
        "sheets_interface": "official_rest_with_injected_existing_google_auth",
        "sheets_transport_status": "implemented_local_fictional_tests_live_not_performed",
        "sheets_oauth": "external_existing_google_workflow_not_implemented_here",
        "official_api_platforms": ["youtube", "facebook", "instagram", "threads"],
        "hybrid_permalink_platforms": ["youtube", "instagram"],
        "substack_primary_interface": "controlled_browser_opencli",
        "local_helper": "quarantine_review_mapping_confirmation_lock_dedup_sheet_claim_stage_claim_checkpoint_readback",
        "network_access_by_helper": False,
        "network_access_by_official_api_adapter": True,
        "network_access_by_transaction_coordinator": True,
        "network_access_by_sheets_api_adapter": True,
        "network_access_by_sheets_coordinator": True,
        "execution": "agent_calls_sheets_coordinator_then_community_coordinator_after_separate_approvals",
        "api_adapter_status": "implemented_local_fictional_tests_live_not_performed",
        "transaction_integration": "implemented_local_fictional_tests_live_not_performed",
        "review_mode": "human_review_only_local_loopback",
        "manual_review_status": "implemented_local_fictional_tests_live_not_performed",
        "classifier": "isolated_ai_disabled_not_bundled_or_selectable",
        "network_access_by_manual_review_helper": False,
        "end_to_end_status": "implemented_local_fictional_tests_live_not_performed",
        "unknown_result_resolution": "independent_observation_binds_original_claim_without_resend",
        "direct_message_research": "docs/community-direct-messaging-mvp-research.md",
        "direct_message_contract": "skills/social-community-management/references/direct-messaging-contract.md",
        "direct_message_execution_source": "skills/social-community-management/references/direct-message-execution-source.json",
        "direct_message_queue": "skills/social-community-management/scripts/direct_message_queue.py",
        "direct_message_api_adapter": "skills/social-community-management/scripts/official_direct_message_api.py",
        "direct_message_coordinator": "skills/social-community-management/scripts/direct_message_execute.py",
        "direct_message_end_to_end_test": "tests/test_direct_message_end_to_end.py",
        "direct_message_mode": "explicit_on_demand_facebook_instagram_inbound_24h_text_no_webhook",
        "direct_message_review_surface": "private_local_manual_review_no_google_sheets",
        "network_access_by_direct_message_queue": False,
        "network_access_by_direct_message_api_adapter": True,
        "network_access_by_direct_message_coordinator": True,
        "direct_messages": "implemented_local_fictional_tests_live_not_performed",
        "live_status": "not_performed",
    }
    if community != expected_community:
        raise ValidationError("互動 manifest 必須區分 API 接線、瀏覽器補證、六欄 RAW 與實機驗收")
    for key in ("helper", "official_api_adapter", "transaction_coordinator", "execution_sources",
                "sheets_api_adapter", "sheets_coordinator", "sheets_execution_source",
                "manual_review_helper", "review_execution_source", "end_to_end_test",
                "direct_message_research", "direct_message_contract",
                "direct_message_execution_source", "direct_message_queue",
                "direct_message_api_adapter", "direct_message_coordinator",
                "direct_message_end_to_end_test"):
        if not (ROOT / community[key]).is_file():
            raise ValidationError("互動 manifest 指向不存在的本機資源")
    direct_message_research = (ROOT / community["direct_message_research"]).read_text(encoding="utf-8")
    for phrase in (
        "官方能力查證與 MVP 架構確認完成",
        "Facebook 粉絲專頁 Messenger",
        "Instagram 專業帳號私訊",
        "使用者叫 Agent 時才同步",
        "第一版不建 Webhook",
        "本機收發程式與虛構資料測試 | 已建立並通過針對性虛構測試",
    ):
        if phrase not in direct_message_research:
            raise ValidationError(f"私訊 MVP 研究文件缺少：{phrase}")
    direct_source = json.loads(
        (ROOT / community["direct_message_execution_source"]).read_text(encoding="utf-8"))
    if (direct_source.get("schema_version") != 1
            or direct_source.get("mode") != community["direct_message_mode"]
            or direct_source.get("implementation_status") != community["direct_messages"]
            or direct_source.get("limits", {}).get("reply_window_hours") != 24
            or direct_source.get("limits", {}).get("content") != "plain_text_only"
            or direct_source.get("limits", {}).get("webhook") is not False
            or direct_source.get("limits", {}).get("google_sheets") is not False
            or set(direct_source.get("platforms", {})) != {
                "facebook", "instagram_login", "instagram_facebook_login"}):
        raise ValidationError("私訊執行來源必須固定按需、24 小時、純文字、不建 Webhook 的 MVP")
    validate_community_sources(ROOT / community["execution_sources"])
    validate_sheets_source(ROOT / community["sheets_execution_source"])
    validate_review_source(ROOT / community["review_execution_source"])
    performance = manifest.get("performance", {})
    expected_performance = {
        "helper": "skills/social-performance-analysis/scripts/performance_review.py",
        "collector": "skills/social-performance-analysis/scripts/performance_collect.py",
        "official_api_adapter": "skills/social-performance-analysis/scripts/official_performance_api.py",
        "metric_catalog": "skills/social-performance-analysis/references/metric-catalog.json",
        "metric_catalog_validator": "skills/social-performance-analysis/scripts/metric_catalog.py",
        "source_contract": "skills/social-performance-analysis/references/performance-source-contract.md",
        "execution_sources": "skills/social-performance-analysis/references/execution-sources.json",
        "end_to_end_test": "tests/test_performance_end_to_end.py",
        "platform_documents": ["youtube", "instagram", "facebook", "threads", "substack"],
        "modes": ["weekly", "monthly", "quarterly", "yearly"],
        "network_access_by_helper": False,
        "network_access_by_collector": False,
        "network_access_by_official_api_adapter": True,
        "official_api_platforms": ["youtube", "facebook", "instagram", "threads"],
        "substack_execution": "official_read_only_mcp_then_official_export_then_controlled_browser_imported_evidence",
        "execution": "official_api_or_hash_bound_imported_evidence_then_existing_analysis_contract",
        "data_sources": "implemented_metric_catalog_local_fictional_tests_live_not_performed",
        "end_to_end_status": "implemented_four_modes_local_fictional_tests_live_not_performed",
        "strategy_write": "human_judgment_then_preview_then_separate_confirmation_hash_bound_append",
        "raw_data_target": "<workspace>/social-media/performance/",
        "live_status": "not_performed",
    }
    if performance != expected_performance:
        raise ValidationError("成效分析必須區分四週期、資料來源接線與實機狀態")
    for key in ("helper", "collector", "official_api_adapter", "metric_catalog",
                "metric_catalog_validator", "source_contract", "execution_sources",
                "end_to_end_test"):
        if not (ROOT / performance[key]).is_file():
            raise ValidationError("成效 manifest 指向不存在的本機資源")
    performance_sources = json.loads(
        (ROOT / performance["execution_sources"]).read_text(encoding="utf-8"))
    if (performance_sources.get("schema_version") != 1
            or performance_sources.get("implementation_status") != performance["data_sources"]
            or performance_sources.get("live_status") != "not_performed"
            or set(performance_sources.get("platforms", {})) != PLATFORMS
            or performance_sources.get("platforms", {}).get("substack", {}).get(
                "preferred_source") != "official_substack_mcp"
            or performance_sources.get("platforms", {}).get("threads", {}).get(
                "coverage") != "unknown_no_invented_since_until_query"
            or performance_sources.get("metric_catalog") !=
                "references/metric-catalog.json"
            or performance_sources.get("metric_catalog_validator") !=
                "scripts/metric_catalog.py"):
        raise ValidationError("成效執行來源必須固定四平台 API 與 Substack 證據匯入邊界")
    metric_catalog = json.loads(
        (ROOT / performance["metric_catalog"]).read_text(encoding="utf-8"))
    if (metric_catalog.get("schema_version") != 1
            or set(metric_catalog.get("platforms", {})) != PLATFORMS
            or set(metric_catalog["platforms"]["youtube"].get("metrics", {})) != {
                "views", "engagedViews", "estimatedMinutesWatched",
                "averageViewDuration", "averageViewPercentage", "comments",
                "likes", "shares", "subscribersGained", "subscribersLost"}
            or metric_catalog["platforms"]["facebook"].get(
                "required_query", {}).get("show_description_from_api_doc") is not True
            or "followers_count" not in metric_catalog["platforms"]["threads"].get(
                "descriptive_only", {})
            or metric_catalog["platforms"]["substack"].get("mcp_eligibility") !=
                "publication_admin_and_bestseller_and_connected_mcp_client"):
        raise ValidationError("成效指標目錄未固定白名單、runtime 證據與來源資格")
    credential_storage = manifest.get("credential_storage", {})
    expected_credential_storage = {
        "helper": "skills/social-media-setup/scripts/credential_store.py",
        "registry_schema": "skills/social-media-setup/references/credential-references.schema.json",
        "registry_schema_version": 2,
        "terminal_helper": "skills/social-media-setup/scripts/credential_terminal.py",
        "registry_target": "<workspace>/.local/social-media/credential-references.json",
        "default_macos_backend": "macos-keychain",
        "default_windows_backend": "windows-credential-manager",
        "unsupported_os_policy": "stop_without_plaintext_fallback",
        "interactive_input": "visible_terminal_hidden_prompt",
        "secret_cli_output": False,
    }
    if credential_storage != expected_credential_storage:
        raise ValidationError("manifest 的原生憑證庫契約不完整")
    if manifest.get("acceptance_policy", {}).get("default_tests") != "fictional_local_only":
        raise ValidationError("目前一般測試必須維持虛構本機資料，不自動開始實機驗收")
    oauth = manifest.get("oauth_runtime", {})
    if oauth.get("routes") != ["facebook", "youtube", "instagram", "threads"] or oauth.get("status") != "implemented_fictional_tests_live_deferred":
        raise ValidationError("OAuth 執行器必須明列四條路徑，不能代表所有登入路線或實機通過")
    for key in ("entrypoint", "engine", "transport", "state_schema", "meta_user_adapter", "instagram_facebook_adapter"):
        if not (ROOT / oauth.get(key, "missing")).is_file():
            raise ValidationError("OAuth 執行器缺少 manifest 對應檔案")
    if oauth.get("instagram_facebook_flow") != "facebook_login_https_code_selected_linked_page_token_instagram_identity":
        raise ValidationError("manifest 缺少 Instagram via Facebook Login 的 Page／IG 身分契約")
    if oauth.get("instagram_permission_evidence") != "initial_exchange_exact_scopes_current_basic_identity_function_endpoint_required":
        raise ValidationError("manifest 必須區分 Instagram Login 初次 scope 與逐功能證據")
    if "instagram_via_facebook_login_oauth" in manifest.get("implementation_gaps", {}):
        raise ValidationError("已實作的 Instagram via Facebook Login 不得繼續列為程式缺口")
    if "instagram_current_full_scope_readback" in manifest.get("implementation_gaps", {}):
        raise ValidationError("已查證的平台證據限制不得繼續冒充待實作端點")
    if manifest.get("capability_limits", {}) != {
        "instagram_login_current_full_scope_list": "not_documented_in_official_sources_checked_2026_09_06",
        "instagram_login_function_scope_status": "verify_at_selected_official_endpoint_each_use",
    }:
        raise ValidationError("manifest 缺少 Instagram Login 當前權限證據限制")
    if manifest.get("license_spdx") != "Apache-2.0":
        raise ValidationError("缺少 Apache-2.0 授權聲明")
    if not (ROOT / "LICENSE").is_file():
        raise ValidationError("可獨立散布的技能包缺少 LICENSE")
    validate_opencli_dependency(manifest)
    runtime = manifest.get("runtime", {})
    if runtime.get("local_strategy_requires_network") is not False:
        raise ValidationError("純策略設定不得要求網路")
    if runtime.get("platform_capability_refresh_requires_network") is not True:
        raise ValidationError("平台能力刷新必須揭露網路需求")
    if runtime.get("external_account_actions_require_explicit_authorization") is not True:
        raise ValidationError("外部帳號操作必須保留明確授權關卡")
    gates = {item.get("id"): item.get("status") for item in manifest.get("readiness_gates", [])}
    if gates.get("local_credential_storage") != (
        "implementation_and_fictional_backend_tests_complete_macos_windows_live_not_performed"
    ):
        raise ValidationError("原生憑證庫不得在實機驗收前標示完成")
    if gates.get("formal_public_support") != "not_supported":
        raise ValidationError("候選版不得宣稱正式公開支援")
    for reference in manifest.get("official_references", []):
        if not str(reference.get("url", "")).startswith("https://"):
            raise ValidationError("官方來源必須使用 HTTPS")
        reference_date = reference.get("checked_on")
        if not isinstance(reference_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reference_date):
            raise ValidationError("官方來源缺少有效查證日期")
        if reference_date > manifest_date:
            raise ValidationError("官方來源查證日期不得晚於 manifest.checked_on")


def validate_opencli_dependency(manifest: dict) -> None:
    """驗證離線技能安裝與明示核准的固定 OpenCLI 來源分離。"""
    dependencies = manifest.get("dependencies", [])
    if len(dependencies) != 2 or {d.get("id") for d in dependencies} != {"opencli", "pillow"}:
        raise ValidationError("僅允許已定義的 OpenCLI 與既有 Pillow 執行期依賴")
    dependency = next(d for d in dependencies if d["id"] == "opencli")
    image_runtime = next(d for d in dependencies if d["id"] == "pillow")
    if any(image_runtime.get(k) != v for k, v in {
        "required": False, "installable": False, "bundled": False,
        "managed_by_skill_installer": False, "version": "12.3.0",
        "license_spdx": "MIT-CMU", "installation_stage": "none_existing_environment_only",
        "upstream_url": "https://github.com/python-pillow/Pillow",
        "source_url": "https://github.com/python-pillow/Pillow/tree/12.3.0",
        "tested_existing_versions": ["12.1.1", "12.3.0"],
    }.items()):
        raise ValidationError("Pillow 只可使用既有環境，不能混入自動安裝")
    expected = {
        "required": False, "default_for": "project_initialization",
        "installation_stage": "agent_runtime_after_notice_and_approval",
        "bundled": False, "managed_by_skill_installer": False,
        "installable": True,
        "status": "pinned_source_candidate_live_installation_not_performed",
        "source_contract": "skills/social-media-setup/references/opencli-source.json",
        "procedure": "skills/social-media-setup/references/opencli-initialization.md",
    }
    if any(dependency.get(key) != value for key, value in expected.items()):
        raise ValidationError("OpenCLI 必須在預先告知與核准後才由 Agent 安裝")
    if manifest.get("runtime", {}).get("opencli_download_requires_notice_and_approval") is not True:
        raise ValidationError("OpenCLI 不得省略下載前告知與核准")
    if not (ROOT / dependency["procedure"]).is_file():
        raise ValidationError("缺少 OpenCLI 操作流程")
    source = json.loads((ROOT / dependency["source_contract"]).read_text(encoding="utf-8"))
    validate_opencli_source(source)


def validate_publishing_sources(path: Path) -> None:
    """驗證五平台已選定真實介面，但不得提升為實機成功。"""

    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValidationError("發布執行來源表不是有效 JSON") from None
    if source.get("schema_version") != 2 or source.get("checked_on") != "2026-09-06":
        raise ValidationError("發布執行來源表缺少版本或查證日期")
    if source.get("caller") != "social-content-publishing Agent invokes publish_execute.py after publish_job begin":
        raise ValidationError("發布執行來源表必須指定 Agent 於 begin 後呼叫")
    if source.get("transaction_coordinator") != "scripts/publish_execute.py":
        raise ValidationError("發布執行來源表缺少交易協調器")
    if source.get("live_status") != "not_performed":
        raise ValidationError("本機接線不得冒充實機發布")
    if ("before_preview_and_begin" not in source.get("routing_policy", "")
            or "rechecked_against_current_official_docs" not in source.get("version_policy", "")
            or "do_not_treat_document_examples_as_permanent_limits" not in source.get("limit_policy", "")):
        raise ValidationError("發布執行來源表缺少格式路由、版本或動態上限規則")
    platforms = source.get("platforms", {})
    if set(platforms) != PLATFORMS:
        raise ValidationError("發布執行來源表必須恰有五平台")
    for platform in {"youtube", "facebook", "instagram", "threads"}:
        record = platforms[platform]
        if (record.get("primary_interface") != "official_api"
                or record.get("primary_source") != "scripts/official_publish_api.py"
                or record.get("implementation_status") != "transaction_integrated_local_fictional_tests_live_pending"
                or not str(record.get("official_reference", "")).startswith("https://")
                or not record.get("implemented_actions")
                or not record.get("format_routes")):
            raise ValidationError(f"{platform} 缺少可辨識的正式 API 執行來源")
    youtube_video = platforms["youtube"]["format_routes"].get("video", {})
    if (youtube_video.get("route") != "official_api"
            or youtube_video.get("maximum_file_size") != "256_GB"
            or youtube_video.get("maximum_duration") != "12_hours_platform_limit"
            or "subject_to_change" not in youtube_video.get("quota", "")):
        raise ValidationError("YouTube 影片格式、限制或動態配額契約不完整")
    facebook_video = platforms["facebook"]["format_routes"].get("video", {})
    if (facebook_video.get("route") != "controlled_browser"
            or facebook_video.get("official_capability") != "reels_upload_api_documented"
            or facebook_video.get("local_adapter") != "not_implemented"
            or "not_enforced" not in " ".join(facebook_video)):
        raise ValidationError("Facebook Reels 必須區分官方能力、舊限制與未實作 adapter")
    instagram_carousel = platforms["instagram"]["format_routes"].get("carousel", {})
    if (instagram_carousel.get("maximum_items") != 10
            or instagram_carousel.get("image_only_route") != "official_api"
            or instagram_carousel.get("mixed_image_video_route") != "controlled_browser"
            or "do_not_hardcode" not in platforms["instagram"].get("fixed_daily_limit_status", "")):
        raise ValidationError("Instagram 輪播變體或動態發布額度契約不完整")
    threads_carousel = platforms["threads"]["format_routes"].get("carousel", {})
    if (threads_carousel.get("route") != "controlled_browser"
            or threads_carousel.get("local_adapter") != "not_implemented"
            or threads_carousel.get("minimum_items") != 2
            or threads_carousel.get("maximum_items") != 20
            or "threads_publishing_limit" not in platforms["threads"].get("publishing_limit_endpoint", "")):
        raise ValidationError("Threads 輪播或動態發布額度契約不完整")
    substack = platforms["substack"]
    if (substack.get("primary_interface") != "controlled_browser"
            or substack.get("implementation_status") != "browser_handoff_claim_and_observation_integrated_live_pending"
            or "OpenCLI" not in substack.get("primary_source", "")
            or "official_api" in substack.get("primary_source", "").lower()
            or not substack.get("documented_actions")
            or "read_only" not in substack.get("known_gap", "")):
        raise ValidationError("Substack 必須維持受控瀏覽器且不得假造官方寫入 API")


def validate_community_sources(path: Path) -> None:
    """驗證留言執行來源、URL 證據與不重送契約。"""

    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValidationError("互動執行來源表不是有效 JSON") from None
    if source.get("schema_version") != 1 or source.get("checked_on") != "2026-09-06":
        raise ValidationError("互動執行來源表缺少版本或查證日期")
    if source.get("caller") != (
            "social-community-management Agent invokes community_execute.py after each required approval gate"):
        raise ValidationError("互動執行來源表必須指定 Agent 在確認關卡後呼叫")
    if source.get("transaction_coordinator") != "scripts/community_execute.py":
        raise ValidationError("互動執行來源表缺少交易協調器")
    if (source.get("live_status") != "not_performed"
            or "must not be resent" not in source.get("write_policy", "")
            or "real reply URL" not in source.get("readback_policy", "")):
        raise ValidationError("互動執行來源表不得省略不重送、完整讀回或實機邊界")
    limits = source.get("batch_limits", {})
    if limits != {"maximum_comments": 100, "maximum_pages_per_list": 5,
                   "incomplete_pagination_result": "partial_requires_attention"}:
        raise ValidationError("互動執行來源表缺少固定分頁護欄")
    platforms = source.get("platforms", {})
    if set(platforms) != PLATFORMS:
        raise ValidationError("互動執行來源表必須恰有五平台")
    for platform in {"youtube", "facebook", "instagram", "threads"}:
        record = platforms[platform]
        if (record.get("api_source") != "scripts/official_community_api.py"
                or record.get("implementation_status") !=
                "transaction_integrated_local_fictional_tests_live_pending"
                or not record.get("implemented_actions")
                or not str(record.get("official_reference", "")).startswith("https://")):
            raise ValidationError(f"{platform} 缺少可辨識的留言 API 執行來源")
    for platform in {"youtube", "instagram"}:
        record = platforms[platform]
        if (record.get("primary_interface") != "official_api_plus_controlled_browser_permalink"
                or "permalink" not in record.get("url_evidence", "")
                or "OpenCLI" not in record.get("browser_source", "")):
            raise ValidationError(f"{platform} 必須保留 API 加受控瀏覽器網址證據")
    if (platforms["facebook"].get("primary_interface") != "official_api"
            or "permalink_url" not in platforms["facebook"].get("url_evidence", "")):
        raise ValidationError("Facebook 必須由官方 Comment permalink_url 完成讀回")
    threads = platforms["threads"]
    if (threads.get("primary_interface") != "official_api"
            or "/{thread-id}/replies" not in threads.get("official_read_edges", [])
            or "/{thread-id}/conversation" not in threads.get("official_read_edges", [])
            or "replied_to" not in threads.get("url_evidence", "")
            or "publish_reply" not in threads.get("implemented_actions", [])):
        raise ValidationError("Threads 必須包含完整回覆讀取、父關係與兩階段發布")
    substack = platforms["substack"]
    if (substack.get("primary_interface") != "controlled_browser"
            or substack.get("implementation_status") !=
            "browser_handoff_claim_and_observation_integrated_live_pending"
            or "OpenCLI" not in substack.get("primary_source", "")
            or "no official public" not in substack.get("known_gap", "")):
        raise ValidationError("Substack 必須維持受控瀏覽器且不得假造官方留言 API")


def validate_sheets_source(path: Path) -> None:
    """驗證 Sheets 正式介面、授權分離、RAW 與不重送契約。"""

    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValidationError("Sheets 執行來源表不是有效 JSON") from None
    if (source.get("schema_version") != 1
            or source.get("checked_on") != "2026-09-06"
            or source.get("primary_interface") != "google_sheets_v4_official_rest"
            or source.get("api_adapter") != "scripts/official_sheets_api.py"
            or source.get("transaction_coordinator") != "scripts/community_sheets.py"):
        raise ValidationError("Sheets 執行來源與本機程式不一致")
    if (source.get("write_operation") != "spreadsheets.values.update"
            or source.get("write_method") != "PUT"
            or source.get("value_input_option") != "RAW"
            or source.get("read_operation") != "spreadsheets.get"
            or source.get("read_value_field") != "CellData.userEnteredValue"):
        raise ValidationError("Sheets 必須採 RAW 寫入與 userEnteredValue 型別讀回")
    if ("single claim" not in source.get("transaction_policy", "")
            or "do not resend" not in source.get("unknown_result_policy", "")
            or "before every" not in source.get("reply_policy", "")):
        raise ValidationError("Sheets 來源表缺少 claim、不重送或逐則重讀")
    authorization = source.get("authorization", {})
    if (authorization.get("scope") != "https://www.googleapis.com/auth/spreadsheets"
            or authorization.get("social_oauth_is_not_google_sheets_oauth") is not True
            or "outside this skill" not in authorization.get("oauth_setup", "")):
        raise ValidationError("Sheets OAuth 必須與社群 OAuth 及此技能實作分開")
    cli = source.get("observed_local_cli", {})
    if (cli.get("command") != "gws" or cli.get("used_as_default") is not False
            or cli.get("official_upstream") != "https://github.com/googleworkspace/cli"):
        raise ValidationError("已觀測 gws 必須標示為非預設來源")
    references = source.get("official_references", [])
    if len(references) < 4 or any(not item.startswith(
            "https://developers.google.com/workspace/sheets/") for item in references):
        raise ValidationError("Sheets 來源表缺少官方 REST 與 CellData 依據")
    if (source.get("implementation_status") !=
            "official_rest_adapter_and_transaction_coordinator_local_fictional_tests_live_pending"
            or source.get("live_status") != "not_performed"):
        raise ValidationError("Sheets 本機實作不得冒充真實帳號驗收")


def validate_review_source(path: Path) -> None:
    """驗證人工 MVP、回環介面與未啟用 AI 的真實邊界。"""

    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValidationError("互動審查來源表不是有效 JSON") from None
    if (source.get("schema_version") != 1
            or source.get("checked_on") != "2026-09-06"
            or source.get("mvp_mode") != "human_review_only"
            or source.get("manual_review_helper") != "scripts/manual_review.py"):
        raise ValidationError("互動審查必須明列本機人工 MVP")
    if ("127.0.0.1" not in source.get("network_policy", "")
            or "no external requests" not in source.get("network_policy", "")
            or "no source or draft text" not in source.get("output_policy", "")
            or "0600" not in source.get("session_policy", "")
            or source.get("dependencies") != "python_standard_library_only"):
        raise ValidationError("人工審查介面缺少回環、無外連或私人輸出邊界")
    if source.get("decision_values") != ["allow", "uncertain", "quarantine"]:
        raise ValidationError("人工審查決策集合不固定")
    isolated = source.get("isolated_ai", {})
    if (isolated.get("status") != "disabled_not_bundled_or_selectable"
            or len(isolated.get("enable_only_after", [])) < 6
            or "cannot prove" not in isolated.get("reason", "")):
        raise ValidationError("沒有實際隔離證據時不得啟用 AI reviewer")
    if ("not permission to reply" not in source.get("allow_meaning", "")
            or source.get("live_status") != "local_fictional_loopback_tests_only"):
        raise ValidationError("人工 allow 不得冒充回覆授權或實機驗收")


def validate_opencli_source(source: dict) -> None:
    """固定作者來源、版本與完整性格式；不連線或宣稱資產已下載。"""
    if source.get("upstream_url") != "https://github.com/jackwener/opencli" or source.get("download_url") != "https://github.com/jackwener/opencli.git":
        raise ValidationError("OpenCLI 必須取自作者 GitHub")
    if not re.fullmatch(r"\d+\.\d+\.\d+", source.get("version", "")) or source.get("tag") != "v" + source["version"]:
        raise ValidationError("OpenCLI 不得採浮動版本")
    for name in ("commit", "tree"):
        if not re.fullmatch(r"[0-9a-f]{40}", source.get(name, "")):
            raise ValidationError("OpenCLI 缺少完整 Git 來源識別")
    for name in ("license_sha256", "lockfile_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", source.get(name, "")):
            raise ValidationError("OpenCLI 缺少來源完整性資料")
    extension = source.get("extension", {})
    expected_url = f'https://github.com/jackwener/OpenCLI/releases/download/{source["tag"]}/opencli-extension-v{extension.get("version")}.zip'
    if extension.get("url") != expected_url or not re.fullmatch(r"[0-9a-f]{64}", extension.get("sha256", "")):
        raise ValidationError("擴充功能必須是同一固定 Release 的可驗證資產")
    if type(extension.get("size_bytes")) is not int or extension["size_bytes"] <= 0:
        raise ValidationError("擴充功能缺少容量資訊")
    if not {"cookies", "debugger", "tabs"}.issubset(extension.get("permissions", [])) or extension.get("host_permissions") != ["<all_urls>"]:
        raise ValidationError("來源契約不得隱藏目前已查證的廣泛擴充權限")
    if source.get("license_spdx") != "Apache-2.0" or source.get("live_installation") != "not_performed":
        raise ValidationError("授權或實機驗收狀態不符")


def validate_skill_structure(manifest: dict) -> None:
    """確認技能可獨立安裝且平台文件完整。"""

    skill_root = ROOT / "skills"
    actual = {path.name for path in skill_root.iterdir() if path.is_dir()}
    if actual != IMPLEMENTED:
        raise ValidationError(f"技能目錄不應出現空殼：{sorted(actual)}")
    skill = skill_root / "social-media-setup"
    planning = skill_root / "social-content-planning"
    writing = skill_root / "social-content-writing"
    image_skill = skill_root / "social-image-production"
    publishing = skill_root / "social-content-publishing"
    performance = skill_root / "social-performance-analysis"
    if parse_skill_name(performance / "SKILL.md") != "social-performance-analysis":
        raise ValidationError("成效技能名稱不符")
    for name in ("agents/openai.yaml", "scripts/performance_review.py",
                 "scripts/performance_collect.py", "scripts/official_performance_api.py",
                 "scripts/metric_catalog.py",
                 "references/metrics-contract.md", "references/strategy-feedback.md",
                 "references/performance-source-contract.md",
                 "references/execution-sources.json", "references/metric-catalog.json"):
        if not (performance / name).is_file():
            raise ValidationError("成效技能缺少必要資源")
    if {p.stem for p in (performance / "references/platforms").glob("*.md")} != PLATFORMS:
        raise ValidationError("成效技能必須包含五份平台指標文件")
    community = skill_root / "social-community-management"
    if parse_skill_name(community / "SKILL.md") != "social-community-management":
        raise ValidationError("互動技能名稱不符")
    for name in ("agents/openai.yaml", "scripts/community_queue.py",
                 "scripts/official_community_api.py", "scripts/community_execute.py",
                 "scripts/official_sheets_api.py", "scripts/community_sheets.py",
                 "scripts/manual_review.py",
                 "references/community-contract.md", "references/execution-sources.json",
                 "references/sheets-execution-source.json", "references/sheets-review.md",
                 "references/classifier-contract.md", "references/review-execution-source.json"):
        if not (community / name).is_file():
            raise ValidationError("互動技能缺少必要資源")
    if {p.stem for p in (community / "references/platforms").glob("*.md")} != PLATFORMS:
        raise ValidationError("互動技能必須包含五份平台文件")
    community_cases = (ROOT / "tests/community-management-cases.md").read_text(
        encoding="utf-8")
    for phrase in ("完整虛構串接", "只交換單一欄位", "原本唯一的 API claim",
                   "完整 observation"):
        if phrase not in community_cases:
            raise ValidationError(f"互動完整串接案例缺少：{phrase}")
    if parse_skill_name(publishing / "SKILL.md") != "social-content-publishing":
        raise ValidationError("發布技能名稱不符")
    for name in ("agents/openai.yaml", "scripts/publish_job.py", "scripts/official_publish_api.py",
                 "scripts/publish_execute.py",
                 "references/publishing-contract.md", "references/execution-sources.json"):
        if not (publishing / name).is_file():
            raise ValidationError("發布技能缺少必要資源")
    if {p.stem for p in (publishing / "references/platforms").glob("*.md")} != PLATFORMS:
        raise ValidationError("發布技能必須包含五份平台執行文件")
    downstream_handoffs = {
        publishing / "SKILL.md": ("social-media-setup", "Runtime.access()", "不可直接讀取原生秘密庫分段"),
        publishing / "references/publishing-contract.md": ("OfficialAPIAdapter", "publish_execute.py", "不能拿來發布"),
        publishing / "references/platforms/instagram.md": ("instagram_login", "instagram_facebook_login", "graph.instagram.com", "graph.facebook.com", "Runtime.access", "只有實際 container／publish 端點"),
        publishing / "references/platforms/threads.md": ("Runtime.access", "官方 debugger", "不是發布 driver"),
        community / "SKILL.md": ("social-media-setup", "Runtime.access()", "讀取授權與稍後的回覆確認仍是不同關卡",
                                      "official_community_api.py", "community_execute.py", "record-observation",
                                      "official_sheets_api.py", "community_sheets.py", "refresh_sheet",
                                      "manual_review.py", "human", "isolated_ai_not_enabled"),
        community / "references/platforms/instagram.md": ("Runtime.access", "當次 `/{ig-media-id}/comments` 成功", "初次交換"),
        community / "references/platforms/threads.md": ("Runtime.access", "官方 debugger", "完整回覆列表與父關係"),
        performance / "SKILL.md": ("social-media-setup", "Runtime.access()", "runtime 成功、SDK 欄位存在或 OAuth scope 已取得", "metric_catalog.py", "Substack eligibility"),
        performance / "references/platforms/instagram.md": ("Runtime.access", "當次 insights GET", "空資料、權限拒絕、失效與讀取錯誤分開"),
        performance / "references/platforms/threads.md": ("Runtime.access", "官方 debugger", "實際 insights 仍由下列端點判定"),
    }
    for path, phrases in downstream_handoffs.items():
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                raise ValidationError(f"下游 OAuth 交接契約缺少：{path}: {phrase}")
    handoff_cases = {
        ROOT / "tests/content-publishing-cases.md": ("IG 或 Threads 已完成 setup OAuth", "不取代發布確認"),
        ROOT / "tests/community-management-cases.md": ("IG／Threads 已完成 setup OAuth", "不等於留言權限"),
        ROOT / "tests/performance-analysis-cases.md": (
            "IG／Threads 已有 setup OAuth", "空集合不要求重新 OAuth",
            "四週期完整虛構串接", "再次確認寫回", "原始資料與逐期報告"),
    }
    for path, phrases in handoff_cases.items():
        text = path.read_text(encoding="utf-8")
        if any(phrase not in text for phrase in phrases):
            raise ValidationError(f"下游 OAuth 虛構行為案例不完整：{path}")
    if parse_skill_name(image_skill / "SKILL.md") != "social-image-production":
        raise ValidationError("圖片技能名稱不符")
    for name in ("agents/openai.yaml", "references/production-and-review.md",
                 "references/local-fallback-and-records.md", "assets/image-brief.json",
                 "scripts/image_assets.py", "scripts/image_routing.py",
                 "references/generation-methods.md", "references/html-css.md",
                 "assets/information-card.html", "references/acceptance-testing.md",
                 "assets/acceptance-test-brief.json",
                 "assets/acceptance-test-square-brief.json",
                 "assets/acceptance-overflow-brief.json",
                 "assets/acceptance-web-prompts.md",
                 "assets/acceptance-information-card.html",
                 "assets/acceptance-result-template.json"):
        if not (image_skill / name).is_file():
            raise ValidationError("圖片技能缺少必要製作與檢查資源")
    if parse_skill_name(writing / "SKILL.md") != "social-content-writing":
        raise ValidationError("文案技能名稱不符")
    for name in ("agents/openai.yaml", "references/deliverables-and-media.md",
                 "assets/draft-template.md", "scripts/check_drafts.py"):
        if not (writing / name).is_file():
            raise ValidationError("文案技能缺少必要交付與檢查資源")
    if {p.stem for p in (writing / "references/platforms").glob("*.md")} != PLATFORMS:
        raise ValidationError("文案技能必須包含五份平台規格")
    if parse_skill_name(planning / "SKILL.md") != "social-content-planning":
        raise ValidationError("內容規劃技能名稱不符")
    for name in ("agents/openai.yaml", "references/social-research.md", "references/deliverables.md",
                 "assets/planning-template.md", "scripts/check_planning.py"):
        if not (planning / name).is_file():
            raise ValidationError("內容規劃技能缺少交付、研究或檢查資源")
    if parse_skill_name(skill / "SKILL.md") != "social-media-setup":
        raise ValidationError("技能名稱與 manifest 不符")
    required = {
        "agents/openai.yaml",
        "assets/default-config.json",
        "scripts/credential_store.py",
        "scripts/credential_terminal.py",
        "scripts/oauth_callback.py",
        "scripts/oauth_runtime.py",
        "scripts/oauth_http.py",
        "references/oauth-runtime.md",
        "references/oauth-state.schema.json",
        "scripts/manage_workspace.py",
        "references/credential-references.schema.json",
        "references/local-credential-storage.md",
        "references/strategy-mode.md",
        "references/integration-mode.md",
        "references/opencli-initialization.md",
        "references/opencli-source.json",
        "references/meta-api-setup.md",
        "references/youtube-api-setup.md",
        "references/permission-selection.md",
        "references/configuration-contract.md",
        "references/image-production-preferences.md",
        "references/verification-levels.md",
        "references/social-media-config.schema.json",
        "references/setup-state.schema.json",
    }
    missing = [name for name in sorted(required) if not (skill / name).is_file()]
    if missing:
        raise ValidationError("技能缺少必要檔案：" + ", ".join(missing))
    platform_root = skill / "references/platforms"
    platforms = {path.stem for path in platform_root.glob("*.md")}
    if platforms != PLATFORMS:
        raise ValidationError(f"平台初始化文件不完整：{sorted(platforms)}")

    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
    required_phrases = (
        "策略初始化",
        "平台整合初始化",
        "一次只問一個最重要的問題",
        "預設採完整管理模式",
        "如果有任何權限不想開放，請現在告訴我",
        "同一次 Meta 初始化",
        "取得明確確認後才寫入",
        "不得把瀏覽器內部請求或第三方套件冒充官方 API",
        "實際整合執行",
        "最小化人類操作",
        "API → MCP → OpenCLI",
        "只有使用者特別要求 Computer Use",
        "速度較慢",
        "Computer Use 最後手段",
        "不要貼進聊天",
        "macOS Keychain 或 Windows Credential Manager",
        "credential_store.py put",
        "使用者只貼上一次",
        "不代表已授權發布",
        "執行錯誤最小回填",
        "一次小修正、一次針對性重測",
        "不得修改已安裝快取、內建技能、外掛或第三方來源",
        "不發布",
        "停止條件",
        "虛構工作區驗證",
    )
    for phrase in required_phrases:
        if phrase not in skill_text:
            raise ValidationError(f"技能契約缺少：{phrase}")

    # 防止回復成先問模式、預設代操作或全面禁止優先工具。
    for setup_doc in [skill / "SKILL.md", *(skill / "references").rglob("*.md")]:
        setup_text = setup_doc.read_text(encoding="utf-8")
        for obsolete in (
            "這次要由「AI 操作」還是「人類自行操作」",
            "社群媒體設定一律由人類操作",
            "不提供 AI 代操作選項",
            "不要求使用者手動選 use case",
            "python scripts/credential_browser.py",
        ):
            if obsolete in setup_text:
                raise ValidationError(f"初始化仍含後台代操作指示：{setup_doc.name}")

    meta_text = (skill / "references/meta-api-setup.md").read_text(encoding="utf-8")
    facebook_text = (skill / "references/platforms/facebook.md").read_text(encoding="utf-8")
    instagram_text = (skill / "references/platforms/instagram.md").read_text(encoding="utf-8")
    threads_text = (skill / "references/platforms/threads.md").read_text(encoding="utf-8")
    behavior_text = (ROOT / "tests/behavior-cases.md").read_text(encoding="utf-8")
    meta_requirements = (
        "Meta 三平台合併初始化",
        "同一次設定對話中詢問是否一併設定另外兩個",
        "不可預設一定共用",
        "人工關卡一：身分、安全與法律同意",
        "人工關卡二：OAuth 同意",
        "不得要求使用者把值貼進對話",
        "credential_store.py put --platform facebook --name app-secret",
        "store_secret()",
        "state",
        "platform_read",
        "remote_write",
    )
    for phrase in meta_requirements:
        if phrase not in meta_text:
            raise ValidationError(f"Meta 實際初始化契約缺少：{phrase}")
    facebook_requirements = (
        "預設正式整合路徑：完整社群管理授權",
        "明確縮限路徑：粉絲專頁唯讀驗證",
        "pages_show_list",
        "GET /me/accounts?fields=id,name,access_token,tasks",
        "pages_manage_posts",
        "pages_manage_metadata",
        "pages_messaging",
        "read_insights",
        "可選延伸權限",
        "Page 唯讀查詢",
    )
    for phrase in facebook_requirements:
        if phrase not in facebook_text:
            raise ValidationError(f"Facebook 完整管理契約缺少：{phrase}")
    instagram_requirements = (
        "預設完整核心權限",
        "instagram_business_basic",
        "instagram_business_content_publish",
        "instagram_business_manage_comments",
        "instagram_business_manage_insights",
        "instagram_business_manage_messages",
        "instagram_manage_messages",
        "同一次 Meta 初始化",
    )
    for phrase in instagram_requirements:
        if phrase not in instagram_text:
            raise ValidationError(f"Instagram 完整管理契約缺少：{phrase}")
    threads_requirements = (
        "threads_basic",
        "threads_content_publish",
        "threads_read_replies",
        "threads_manage_replies",
        "threads_manage_insights",
        "沒有一般私訊管理 API",
        "同一次 Meta 初始化",
    )
    for phrase in threads_requirements:
        if phrase not in threads_text:
            raise ValidationError(f"Threads 完整管理契約缺少：{phrase}")
    for case_number in range(11, 43):
        if f"## {case_number}." not in behavior_text:
            raise ValidationError(f"缺少進階虛構行為案例 {case_number}")

    default = json.loads((skill / "assets/default-config.json").read_text(encoding="utf-8"))
    if default["strategy"]["status"] != "not_configured":
        raise ValidationError("公開範本必須維持 not_configured")
    if default["schema_version"] != 5:
        raise ValidationError("一般設定 schema_version 必須是 5")
    if default["brand_visual"]["status"] != "not_configured" or any(v is not None for k, v in default["brand_visual"].items() if k != "status"):
        raise ValidationError("公開範本不得預設使用者品牌")
    if set(default["integrations"]) != PLATFORMS:
        raise ValidationError("公開範本必須明列五個平台")
    for record in default["integrations"].values():
        if record["selected"] or record["requested_capabilities"]:
            raise ValidationError("公開範本不得預選平台或功能")
        if record.get("authorization_profile") != "not_selected":
            raise ValidationError("未選平台的授權模式必須是 not_selected")
        if record.get("requested_permissions") or record.get("declined_permissions"):
            raise ValidationError("公開範本不得預先要求或拒絕 permission")
        if record.get("verification") != {
            "api_app": "not_started",
            "user_auth": "not_started",
            "platform_read": "not_started",
            "remote_write": "not_requested",
        }:
            raise ValidationError("公開範本必須分開初始化四個整合驗證層級")
    json.loads((skill / "references/social-media-config.schema.json").read_text(encoding="utf-8"))
    json.loads((skill / "references/setup-state.schema.json").read_text(encoding="utf-8"))
    credential_schema = json.loads(
        (skill / "references/credential-references.schema.json").read_text(
            encoding="utf-8"
        )
    )
    oauth_schema = json.loads((skill / "references/oauth-state.schema.json").read_text(encoding="utf-8"))
    if oauth_schema.get("additionalProperties") is not False or oauth_schema["properties"]["contains_credentials"] != {"const": False}:
        raise ValidationError("OAuth 狀態不得放入額外欄位或秘密")
    if credential_schema.get("properties", {}).get("contains_credentials") != {
        "const": False
    }:
        raise ValidationError("憑證參照 schema 必須禁止秘密值")
    credential_text = (skill / "references/local-credential-storage.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "預設使用目前登入作業系統帳號的原生憑證庫",
        "不得改存 `.env`",
        "不得接受 `--value`",
        "不代表已授權發布",
        "不得新增會把秘密印到 stdout 的 `get` 命令",
        "另一臺電腦必須重新 OAuth",
    ):
        if phrase not in credential_text:
            raise ValidationError(f"本機憑證儲存契約缺少：{phrase}")
    credential_script = (skill / "scripts/credential_store.py").read_text(
        encoding="utf-8"
    )
    for phrase in ("SecItemAdd", "CredWriteW", "getpass.getpass"):
        if phrase not in credential_script:
            raise ValidationError(f"原生憑證 helper 缺少：{phrase}")
    if 'add_argument("--value"' in credential_script:
        raise ValidationError("憑證 helper 不得接受命令列秘密值")


def validate_public_boundary() -> None:
    """掃描公開文字中的私人路徑、來源名稱與常見秘密。"""

    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"[\ue000-\uf8ff\ufffd]", text):
            raise ValidationError(f"公開文字含非預期私用字元或解碼替代字元：{path}")
        for pattern in PRIVATE_PATTERNS:
            if pattern.lower() in text.lower():
                raise ValidationError(f"公開檔案含私人來源或路徑：{path}: {pattern}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ValidationError(f"公開檔案疑似含秘密：{path}")


def validate_python_sources() -> None:
    """以記憶體編譯 Python，避免在來源目錄產生快取。"""

    for path in ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def validate_markdown() -> None:
    """確認公開 Markdown fence 成對，且套件內相對連結存在。"""

    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        fence_count = sum(1 for line in text.splitlines()
                          if line.lstrip().startswith("```"))
        if fence_count % 2:
            raise ValidationError(f"Markdown fence 未成對：{path}")
        for target in link_pattern.findall(text):
            clean = target.strip().strip("<>").split("#", 1)[0]
            if (not clean or re.match(r"^[a-z]+://", clean)
                    or clean.startswith("mailto:")):
                continue
            resolved = (path.parent / clean).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                raise ValidationError(f"相對連結離開套件：{path} -> {target}") from None
            if not resolved.exists():
                raise ValidationError(f"失效相對連結：{path} -> {target}")


def main() -> int:
    """執行全部靜態檢查。"""

    try:
        manifest = read_manifest()
        validate_manifest(manifest)
        validate_skill_structure(manifest)
        validate_public_boundary()
        validate_python_sources()
        validate_markdown()
    except (ValidationError, OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"驗證失敗：{error}", file=sys.stderr)
        return 1
    print("靜態結構、技能契約、公開邊界、Markdown 與 Python 語法驗證通過。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
