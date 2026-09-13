#!/usr/bin/env python3
"""官網文案工具：從設定產生文案草稿骨架、列出欄位指南、驗證文案與使用者自己寫的文章、預覽並寫入工作區、同步到已建好的專案。只用標準函式庫。

Agent 負責寫出實際的句子；本工具負責結構、來源標記、事實邊界（不得出現使用者沒提供的數字）、佔位句偵測與原子寫入。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIELD_GUIDE = SKILL_ROOT / "assets" / "field-guide.json"
COPY_RELATIVE = Path("website/copy.json")
POSTS_RELATIVE = Path("website/posts")
SOURCES = ("user_fact", "ai_suggestion", "placeholder")
HOME_FIELDS = ("eyebrow", "title", "lead", "primary_cta", "secondary_cta", "offerings_eyebrow", "offerings_heading", "offerings_intro", "trust_eyebrow", "trust_heading", "closing_eyebrow", "closing_heading", "closing_lead")
SIMPLE_PAGES = {
    "services": ("title", "intro", "closing_note"),
    "contact": ("title", "intro", "form_note"),
    "blog": ("title", "intro", "empty_note"),
    "not_found": ("title", "lead"),
}
MAX_LENGTH = {"title": 60, "eyebrow": 40, "primary_cta": 20, "secondary_cta": 20, "heading": 60, "default": 400}
PLACEHOLDER_MARKERS = ("佔位", "請依實際情況改寫", "請替換", "lorem", "TODO", "待補")
SECRET_KEY_FRAGMENTS = ("token", "secret", "password", "cookie", "credential", "apikey", "accountid")
DIGIT_PATTERN = re.compile(r"\d[\d,.]*")
# 中文數詞只在「二到九、十、百、千、萬」接成就類名詞時視為數量宣稱；「一個」「一次」「三十分鐘」是自然用語不算。
# 阿拉伯數字另由 DIGIT_PATTERN 全部比對。
FABRICATION_HINTS = re.compile(r"([二三四五六七八九十百千萬億]+)\s*(位|家|年|倍|人|客戶|學員|訂閱|成員|案例|國|萬|千|百)")
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


class ContentError(RuntimeError):
    """表示必須停止且不應寫入的錯誤。"""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ContentError(f"{label} 必須是一般檔案：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContentError(f"無法讀取 {label}：{error}") from error
    if not isinstance(payload, dict):
        raise ContentError(f"{label} 根節點必須是 JSON object")
    return payload


def validate_workspace_root(raw: str) -> Path:
    supplied = Path(raw).expanduser()
    if supplied.is_symlink():
        raise ContentError("工作區根目錄不得是 symlink")
    resolved = supplied.resolve(strict=False)
    if resolved == Path(resolved.anchor) or resolved.is_relative_to(SKILL_ROOT.parents[1]):
        raise ContentError("工作區不得是根目錄或位於技能包內")
    return resolved


def validate_target_path(root: Path, relative: Path, *, label: str) -> Path:
    target = root / relative
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ContentError(f"{label} 的父路徑不得是 symlink：{current}")
        if current.exists() and not current.is_dir():
            raise ContentError(f"{label} 的父路徑存在檔案類型衝突：{current}")
    if target.is_symlink():
        raise ContentError(f"{label} 不得是 symlink：{target}")
    return target


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def entry(text: str | None, source: str) -> dict[str, Any]:
    return {"text": text, "source": source}


def facts_from_config(config: dict[str, Any]) -> list[str]:
    """使用者提供的事實：商業資訊裡所有文字，供數字邊界比對。"""

    business = config.get("business", {})
    facts: list[str] = []
    for key in ("site_name", "one_line_positioning", "audience_summary"):
        if business.get(key):
            facts.append(str(business[key]))
    for offering in business.get("offerings", []):
        facts.extend([str(offering.get("name", "")), str(offering.get("summary", ""))])
    facts.extend(str(item) for item in business.get("trust_signals", []))
    cta = business.get("primary_call_to_action", {})
    if cta.get("label"):
        facts.append(str(cta["label"]))
    return facts


def load_field_guide() -> list[dict[str, Any]]:
    """讀取欄位指南（必填、用途、範例、長度、提示）。"""

    payload = json.loads(FIELD_GUIDE.read_text(encoding="utf-8"))
    return payload["fields"]


def get_entry(copy: dict[str, Any], path: str) -> dict[str, Any] | None:
    """依路徑取出欄位；about.sections 回傳第一個有文字的段落 body。"""

    page, _, field = path.partition(".")
    if path == "about.sections":
        bodies = [section["body"] for section in copy["about"]["sections"] if isinstance(section, dict)]
        filled = [body for body in bodies if body.get("text")]
        return filled[0] if filled else (bodies[0] if bodies else None)
    return copy.get(page, {}).get(field)


def command_guide(copy: dict[str, Any] | None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """列出每個欄位的用途、範例與目前狀態，供 Agent 引導使用者填寫。"""

    rows = []
    for field in load_field_guide():
        selected = config["pages"]["required"] if config else (copy or {}).get("selected_pages")
        if selected is not None and field["path"].split(".")[0] not in selected:
            continue
        entry_value = get_entry(copy, field["path"]) if copy else None
        status = "empty"
        if entry_value and entry_value.get("text"):
            status = {"user_fact": "written_by_user", "ai_suggestion": "ai_example_needs_review", "placeholder": "placeholder"}[entry_value["source"]]
        rows.append({**field, "status": status, "current_text": (entry_value or {}).get("text")})
    required_missing = [row["path"] for row in rows if row["required"] and row["status"] in ("empty", "placeholder")]
    ai_pending = [row["path"] for row in rows if row["status"] == "ai_example_needs_review"]
    return {
        "result": "guide",
        "required_missing": required_missing,
        "ai_examples_needing_review": ai_pending,
        "fields": rows,
        "advice": "Agent 先完成已選頁面的摘要與文案，標明事實來源；人類批次核對商業事實與方向，不必親自代寫。",
        "contains_credentials": False,
    }


def command_draft(config: dict[str, Any]) -> dict[str, Any]:
    """從設定產生文案草稿骨架：事實欄位標 user_fact，其餘留 null 等 Agent 填寫。"""

    business = config.get("business", {})
    if business.get("status") == "not_configured":
        raise ContentError("商業資訊尚未設定；請先完成 website-setup 的一次訪談")
    cta = business.get("primary_call_to_action", {})
    draft = {
        "schema_version": 1,
        "status": "draft",
        "language": business.get("language", "zh-TW"),
        "facts_snapshot": facts_from_config(config),
        "selected_pages": config["pages"]["required"],
        "home": {field: entry(None, "placeholder") for field in HOME_FIELDS},
        "about": {"title": entry(None, "placeholder"), "intro": entry(None, "placeholder"), "sections": [], "cta_heading": entry(None, "placeholder")},
        "services": {field: entry(None, "placeholder") for field in SIMPLE_PAGES["services"]},
        "contact": {field: entry(None, "placeholder") for field in SIMPLE_PAGES["contact"]},
        "blog": {field: entry(None, "placeholder") for field in SIMPLE_PAGES["blog"]},
        "not_found": {field: entry(None, "placeholder") for field in SIMPLE_PAGES["not_found"]},
        "posts": [],
        "contains_credentials": False,
    }
    draft["home"]["title"] = entry(business.get("one_line_positioning"), "user_fact")
    draft["home"]["lead"] = entry(business.get("audience_summary"), "user_fact")
    draft["home"]["primary_cta"] = entry(cta.get("label"), "user_fact")
    draft["about"]["sections"] = [
        {"heading": entry("我服務的對象", "ai_suggestion"), "body": entry(business.get("audience_summary"), "user_fact")},
        {"heading": entry("我怎麼工作", "ai_suggestion"), "body": entry(None, "placeholder")},
    ]
    return draft


def number_findings(text: str, facts_text: str) -> list[str]:
    """AI 建議裡的數字與數量宣稱必須出現在使用者事實中；回傳未驗證項的說明。日期格式的數字（YYYY-MM-DD）略過。"""

    details: list[str] = []
    for match in FABRICATION_HINTS.finditer(text):
        fragment = match.group(0)
        if fragment not in facts_text and match.group(1) not in facts_text:
            details.append(f"AI 建議含使用者未提供的數量描述：{fragment}")
    for match in DIGIT_PATTERN.finditer(text):
        token = match.group(0).rstrip(".,")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[match.start():match.start() + 10]):
            continue
        if token not in facts_text:
            details.append(f"AI 建議含使用者未提供的數字：{token}")
    return details


def check_entry(item: Any, *, path: str, facts_text: str, final: bool, findings: list[dict[str, str]], key: str) -> None:
    if not isinstance(item, dict) or set(item) != {"text", "source"}:
        raise ContentError(f"{path} 必須是 {{text, source}}")
    text, source = item["text"], item["source"]
    if source not in SOURCES:
        raise ContentError(f"{path}.source 不支援：{source}")
    if text is None:
        if final and source != "placeholder":
            findings.append({"path": path, "kind": "empty_text", "detail": "標記了來源卻沒有文字"})
        if final and source == "placeholder":
            findings.append({"path": path, "kind": "placeholder_source", "detail": "定稿不得保留 placeholder 來源"})
        return
    if not isinstance(text, str) or not text.strip():
        raise ContentError(f"{path}.text 必須是非空文字或 null")
    limit = MAX_LENGTH.get(key, MAX_LENGTH["heading"] if key.endswith("heading") else MAX_LENGTH["default"])
    if len(text) > limit:
        findings.append({"path": path, "kind": "too_long", "detail": f"{len(text)} 字，上限 {limit}"})
    if any(marker.lower() in text.lower() for marker in PLACEHOLDER_MARKERS):
        findings.append({"path": path, "kind": "placeholder_text", "detail": "含佔位字樣" if final else "仍是佔位，定稿前要改"})
    if source == "placeholder" and final:
        findings.append({"path": path, "kind": "placeholder_source", "detail": "定稿不得保留 placeholder 來源"})
    if source == "ai_suggestion":
        for detail in number_findings(text, facts_text):
            findings.append({"path": path, "kind": "unverified_number", "detail": detail})


def reject_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "contains_credentials":
                continue  # 這是「不含憑證」的宣告欄位，不是秘密
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if any(fragment in normalized for fragment in SECRET_KEY_FRAGMENTS):
                raise ContentError(f"文案不得包含秘密或私人識別欄位：{path}.{key}")
            reject_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_secrets(child, f"{path}[{index}]")


def validate_copy(copy: dict[str, Any], config: dict[str, Any] | None) -> list[dict[str, str]]:
    """驗證文案結構與事實邊界；回傳 findings（空代表通過）。結構錯誤直接丟例外。"""

    reject_secrets(copy)
    expected = {"schema_version", "status", "language", "facts_snapshot", "home", "about", "services", "contact", "blog", "not_found", "posts", "contains_credentials"}
    if set(copy) - {"selected_pages"} != expected:
        raise ContentError(f"copy.json 欄位不符；缺少={sorted(expected - set(copy))}，多出={sorted(set(copy) - expected)}")
    if copy["schema_version"] != 1 or copy["status"] not in ("draft", "final") or copy["contains_credentials"] is not False:
        raise ContentError("copy.json 的版本、狀態或憑證聲明不符")
    selected = config["pages"]["required"] if config else copy.get("selected_pages", ["home", "about", "services", "contact", "blog", "not_found"])
    if not isinstance(selected, list) or not {"home", "not_found"}.issubset(selected) or any(p not in {"home", "about", "services", "contact", "blog", "not_found"} for p in selected):
        raise ContentError("selected_pages 不合法")
    if config and copy.get("selected_pages", selected) != selected:
        raise ContentError("文案頁面清單已過期，請依設定重新產生預覽")
    final = copy["status"] == "final"
    facts = list(copy.get("facts_snapshot", [])) + (facts_from_config(config) if config else [])
    facts_text = "\n".join(str(item) for item in facts)
    findings: list[dict[str, str]] = []
    home = copy["home"]
    if set(home) != set(HOME_FIELDS):
        raise ContentError("copy.home 欄位不符")
    for field in HOME_FIELDS:
        check_entry(home[field], path=f"home.{field}", facts_text=facts_text, final=final, findings=findings, key=field)
    about = copy["about"]
    if set(about) != {"title", "intro", "sections", "cta_heading"}:
        raise ContentError("copy.about 欄位不符")
    for field in ("title", "intro", "cta_heading"):
        check_entry(about[field], path=f"about.{field}", facts_text=facts_text, final=final, findings=findings, key=field)
    if not isinstance(about["sections"], list) or len(about["sections"]) > 6:
        raise ContentError("about.sections 必須是最多 6 段的清單")
    for index, section in enumerate(about["sections"]):
        if not isinstance(section, dict) or set(section) != {"heading", "body"}:
            raise ContentError(f"about.sections[{index}] 必須是 {{heading, body}}")
        check_entry(section["heading"], path=f"about.sections[{index}].heading", facts_text=facts_text, final=final, findings=findings, key="heading")
        check_entry(section["body"], path=f"about.sections[{index}].body", facts_text=facts_text, final=final, findings=findings, key="body")
    for page, fields in SIMPLE_PAGES.items():
        block = copy[page]
        if set(block) != set(fields):
            raise ContentError(f"copy.{page} 欄位不符")
        for field in fields:
            check_entry(block[field], path=f"{page}.{field}", facts_text=facts_text, final=final, findings=findings, key=field)
    if final:
        for field in load_field_guide():
            if field["required"] and field["path"].split(".")[0] in selected:
                current = get_entry(copy, field["path"])
                if not current or not current.get("text"):
                    findings.append({"path": field["path"], "kind": "required_missing", "detail": f"必填欄位「{field['label']}」定稿時必須有文字"})
    if not isinstance(copy["posts"], list) or len(copy["posts"]) > 10:
        raise ContentError("posts 必須是最多 10 篇的清單")
    for index, post in enumerate(copy["posts"]):
        if not isinstance(post, dict) or set(post) != {"slug", "file", "source"}:
            raise ContentError(f"posts[{index}] 必須是 {{slug, file, source}}")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", str(post["slug"])) or post["file"] != f"{post['slug']}.md" or post["source"] not in SOURCES:
            raise ContentError(f"posts[{index}] 的 slug、file 或 source 不合法")
    # 未選頁面的空欄位不阻擋定稿；有內容的事實與秘密檢查仍保留。
    return [f for f in findings if not (
        f["path"].split(".")[0] not in selected and f["kind"] in {"placeholder_source", "empty_text"}
    )]


def parse_post(path: Path) -> dict[str, Any]:
    """讀取 Markdown 文章的 frontmatter（title、date、description、tags、coverImage）。"""

    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        raise ContentError(f"文章缺少 frontmatter：{path.name}")
    meta: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [item.strip().strip('"').strip("'") for item in value[1:-1].split(",") if item.strip()]
        else:
            meta[key] = value.strip('"').strip("'")
    for key in ("title", "date", "description"):
        if not meta.get(key):
            raise ContentError(f"文章 {path.name} 缺少 frontmatter 欄位 {key}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(meta["date"])):
        raise ContentError(f"文章 {path.name} 的 date 必須是 YYYY-MM-DD")
    body = match.group(2)
    if len(body.strip()) < 100:
        raise ContentError(f"文章 {path.name} 內文少於 100 字")
    return {"meta": meta, "body": body, "chars": len(body)}


def validate_posts(workspace: Path, copy: dict[str, Any], config: dict[str, Any] | None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    facts_text = "\n".join(list(copy.get("facts_snapshot", [])) + (facts_from_config(config) if config else []))
    final = copy["status"] == "final"
    for post in copy["posts"]:
        path = workspace / POSTS_RELATIVE / post["file"]
        if path.is_symlink() or not path.is_file():
            raise ContentError(f"找不到文章檔：{path}")
        parsed = parse_post(path)
        if any(marker in parsed["body"] for marker in PLACEHOLDER_MARKERS):
            findings.append({"path": f"posts/{post['file']}", "kind": "placeholder_text", "detail": "內文含佔位字樣" if final else "仍是佔位"})
        if post["source"] == "ai_suggestion":
            for detail in number_findings(parsed["body"], facts_text)[:3]:
                findings.append({"path": f"posts/{post['file']}", "kind": "unverified_number", "detail": detail})
    return findings


def flatten_copy(copy: dict[str, Any]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    def add(path: str, item: dict[str, Any]) -> None:
        rows.append({"path": path, "source": item["source"], "text": item["text"]})
    for field in HOME_FIELDS:
        add(f"home.{field}", copy["home"][field])
    for field in ("title", "intro", "cta_heading"):
        add(f"about.{field}", copy["about"][field])
    for index, section in enumerate(copy["about"]["sections"]):
        add(f"about.sections[{index}].heading", section["heading"]); add(f"about.sections[{index}].body", section["body"])
    for page, fields in SIMPLE_PAGES.items():
        for field in fields:
            add(f"{page}.{field}", copy[page][field])
    return rows


def command_preview(workspace: Path, candidate_path: Path, config: dict[str, Any] | None) -> dict[str, Any]:
    candidate = read_json(candidate_path, label="候選文案")
    findings = validate_copy(candidate, config) + validate_posts(workspace, candidate, config)
    target = validate_target_path(workspace, COPY_RELATIVE, label="文案目標")
    current_digest = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    content = json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    binding = json.dumps({"candidate": hashlib.sha256(content.encode()).hexdigest(), "current": current_digest, "workspace": str(workspace)}, sort_keys=True)
    rows = flatten_copy(candidate)
    counts = {source: sum(1 for row in rows if row["source"] == source) for source in SOURCES}
    return {
        "result": "preview",
        "status": candidate["status"],
        "preview_sha256": hashlib.sha256(binding.encode()).hexdigest(),
        "current_copy_sha256": current_digest,
        "source_counts": counts,
        "rows": rows,
        "posts": [post["file"] for post in candidate["posts"]],
        "findings": findings,
        "blocking": [f for f in findings if f["kind"] in ("unverified_number", "placeholder_source", "empty_text", "required_missing") or (candidate["status"] == "final" and f["kind"] == "placeholder_text")],
        "confirm_hint": "user_fact 是使用者自己寫的或訪談說過的；ai_suggestion 是 AI 範例，請使用者逐條決定採用、改寫或刪除，並建議定稿前親自改過一遍。",
        "required_missing": [f["path"] for f in findings if f["kind"] == "required_missing"],
        "contains_credentials": False,
    }


def command_apply(workspace: Path, candidate_path: Path, config: dict[str, Any] | None, expected: str, *, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise ContentError("缺少 --confirm-write；未寫入任何檔案")
    preview = command_preview(workspace, candidate_path, config)
    if not re.fullmatch(r"[0-9a-f]{64}", expected or "") or preview["preview_sha256"] != expected:
        raise ContentError("預覽已失效：候選、既有文案或工作區已變動")
    if preview["blocking"]:
        raise ContentError("文案有未解決的阻擋項（未驗證的數字、空白來源或定稿仍含佔位），未寫入")
    candidate = read_json(candidate_path, label="候選文案")
    target = validate_target_path(workspace, COPY_RELATIVE, label="文案目標")
    write_text_atomic(target, json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {"result": "applied", "copy_target": str(target), "copy_sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "status": candidate["status"], "posts": [post["file"] for post in candidate["posts"]], "contains_credentials": False}


def js_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("</", "<\\/") + "'"


def js_value(item: dict[str, Any]) -> str:
    return "null" if item["text"] is None else js_string(item["text"])


def render_site_copy(copy: dict[str, Any]) -> str:
    lines = ["// 文案層：由 website-content-writing 產生。null 代表沿用主題預設。不要寫入任何秘密。", "", "/** @type {import('./src/site-copy').SiteCopy} */", "export const copy = {"]
    lines.append("  home: {")
    for field in HOME_FIELDS:
        lines.append(f"    {field}: {js_value(copy['home'][field])},")
    lines.append("  },")
    lines.append("  about: {")
    lines.append(f"    title: {js_value(copy['about']['title'])},")
    lines.append(f"    intro: {js_value(copy['about']['intro'])},")
    lines.append("    sections: [")
    for section in copy["about"]["sections"]:
        heading = section["heading"]["text"] or ""
        lines.append(f"      {{ heading: {js_string(heading)}, body: {js_value(section['body'])} }},")
    lines.append("    ],")
    lines.append(f"    cta_heading: {js_value(copy['about']['cta_heading'])},")
    lines.append("  },")
    for page, fields in SIMPLE_PAGES.items():
        lines.append(f"  {page}: {{")
        for field in fields:
            lines.append(f"    {field}: {js_value(copy[page][field])},")
        lines.append("  },")
    lines.append("};")
    return "\n".join(lines) + "\n"


def command_sync(workspace: Path, project: Path, *, confirmed: bool, remove_sample: bool) -> dict[str, Any]:
    """把工作區的 copy.json 與文章同步進已建好的專案。"""

    if not confirmed:
        raise ContentError("缺少 --confirm-write；未修改任何檔案")
    copy_path = workspace / COPY_RELATIVE
    copy = read_json(copy_path, label="文案")
    config_path = workspace / "website/config.json"
    config = read_json(config_path, label="官網設定") if config_path.exists() else None
    findings = validate_copy(copy, config) + validate_posts(workspace, copy, config)
    blocking = [f for f in findings if f["kind"] in ("unverified_number", "placeholder_source", "empty_text", "required_missing")]
    if blocking:
        raise ContentError("文案有阻擋項，未同步")
    project = project.resolve(strict=True)
    for name in ("site.config.mjs", "src/content/posts"):
        if not (project / name).exists():
            raise ContentError(f"專案缺少 {name}；請先用 website-build 建立")
    (project / "site.copy.mjs").write_text(render_site_copy(copy), encoding="utf-8")
    copied: list[str] = []
    posts_dir = project / "src/content/posts"
    for post in copy["posts"]:
        source = workspace / POSTS_RELATIVE / post["file"]
        shutil.copy2(source, posts_dir / post["file"])
        copied.append(post["file"])
    removed = None
    sample = posts_dir / "hello-world.md"
    if remove_sample and copied and sample.is_file():
        sample.unlink(); removed = "hello-world.md"
    return {"result": "synced", "site_copy": str(project / "site.copy.mjs"), "posts_copied": copied, "sample_removed": removed, "next": ["npm run build", "check_site.py --dist <project>/dist"], "contains_credentials": False}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="官網文案工具")
    sub = parser.add_subparsers(dest="command", required=True)
    draft = sub.add_parser("draft"); draft.add_argument("--config", required=True); draft.add_argument("--out", required=True)
    guide = sub.add_parser("guide"); guide.add_argument("--candidate", default=None)
    validate = sub.add_parser("validate"); validate.add_argument("--workspace-root", required=True); validate.add_argument("--candidate", required=True); validate.add_argument("--config", default=None)
    preview = sub.add_parser("preview"); preview.add_argument("--workspace-root", required=True); preview.add_argument("--candidate", required=True); preview.add_argument("--config", default=None)
    apply = sub.add_parser("apply"); apply.add_argument("--workspace-root", required=True); apply.add_argument("--candidate", required=True); apply.add_argument("--config", default=None); apply.add_argument("--expected-preview-sha256", required=True); apply.add_argument("--confirm-write", action="store_true")
    sync = sub.add_parser("sync"); sync.add_argument("--workspace-root", required=True); sync.add_argument("--project", required=True); sync.add_argument("--confirm-write", action="store_true"); sync.add_argument("--keep-sample-post", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "guide":
            candidate = read_json(Path(args.candidate).expanduser(), label="候選文案") if args.candidate else None
            result = command_guide(candidate)
        elif args.command == "draft":
            config = read_json(Path(args.config).expanduser(), label="官網設定")
            out = Path(args.out).expanduser()
            if out.exists():
                raise ContentError(f"輸出檔已存在，不覆蓋：{out}")
            draft = command_draft(config)
            write_text_atomic(out, json.dumps(draft, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            guide = command_guide(draft)
            result: dict[str, Any] = {"result": "drafted", "out": str(out), "required_missing": guide["required_missing"], "fields_to_write": [row["path"] for row in flatten_copy(draft) if row["text"] is None], "next": "用 guide --candidate 列出每欄的用途與範例，由 Agent 完成已選頁面文案，再與設計一起批次確認", "contains_credentials": False}
        else:
            workspace = validate_workspace_root(args.workspace_root)
            config = read_json(Path(args.config).expanduser(), label="官網設定") if getattr(args, "config", None) else None
            if args.command == "validate":
                candidate = read_json(Path(args.candidate).expanduser(), label="候選文案")
                findings = validate_copy(candidate, config) + validate_posts(workspace, candidate, config)
                result = {"result": "valid" if not findings else "findings", "findings": findings, "contains_credentials": False}
            elif args.command == "preview":
                result = command_preview(workspace, Path(args.candidate).expanduser(), config)
            elif args.command == "apply":
                result = command_apply(workspace, Path(args.candidate).expanduser(), config, args.expected_preview_sha256, confirmed=args.confirm_write)
            elif args.command == "sync":
                result = command_sync(workspace, Path(args.project).expanduser(), confirmed=args.confirm_write, remove_sample=not args.keep_sample_post)
            else:
                raise ContentError("未知命令")
    except (ContentError, OSError) as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
