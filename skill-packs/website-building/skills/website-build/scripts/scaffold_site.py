#!/usr/bin/env python3
"""依 website/config.json 從起始範本建立 Astro 專案，並產生佔位素材。只用標準函式庫。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = SKILL_ROOT.parents[1]
DEFAULT_TEMPLATE = PACKAGE_ROOT / "template"
TEMPLATE_EXCLUDES = {"node_modules", "dist", ".astro", ".DS_Store"}
OPTIONAL_PAGE_FILES = {
    "portfolio": "portfolio.astro",
    "case_studies": "case-studies.astro",
    "pricing": "pricing.astro",
    "faq": "faq.astro",
    "newsletter": "newsletter.astro",
}
DEFAULT_SITE_URL = "https://example.invalid"
THEMES_RELATIVE = Path("src/themes")
DEFAULT_THEME = "whitebox"
THEME_ID = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
SECRET_KEY_FRAGMENTS = ("token", "secret", "password", "cookie", "credential", "apikey", "accountid", "zoneid")
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
CONTENT_WRITER_SCRIPTS = SKILL_ROOT.parent / "website-content-writing" / "scripts"


def load_copy_renderer():
    """借用相鄰的 website-content-writing 技能來驗證與渲染文案；沒安裝時回 None。"""

    module_path = CONTENT_WRITER_SCRIPTS / "content_writer.py"
    if not module_path.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("website_content_writer", module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_copy_layer(target: Path, config_path: Path) -> dict[str, Any]:
    """若工作區有 website/copy.json，就渲染成 site.copy.mjs 並複製文章；沒有就沿用範本預設。"""

    workspace_site_dir = config_path.resolve().parent
    copy_path = workspace_site_dir / "copy.json"
    if not copy_path.is_file() or copy_path.is_symlink():
        return {"applied": False, "reason": "workspace_has_no_copy_json"}
    renderer = load_copy_renderer()
    if renderer is None:
        return {"applied": False, "reason": "website-content-writing_not_installed"}
    copy = json.loads(copy_path.read_text(encoding="utf-8"))
    findings = renderer.validate_copy(copy, None)
    blocking = [f for f in findings if f["kind"] in ("unverified_number", "placeholder_source", "empty_text")]
    if blocking:
        raise ScaffoldError("website/copy.json 有阻擋項（未驗證的數字或空白來源），請先用 website-content-writing 修正")
    (target / "site.copy.mjs").write_text(renderer.render_site_copy(copy), encoding="utf-8")
    copied: list[str] = []
    posts_dir = target / "src" / "content" / "posts"
    for post in copy.get("posts", []):
        source = workspace_site_dir / "posts" / post["file"]
        if not source.is_file() or source.is_symlink():
            raise ScaffoldError(f"copy.json 指到的文章不存在：{source}")
        shutil.copy2(source, posts_dir / post["file"])
        copied.append(post["file"])
    sample = posts_dir / "hello-world.md"
    if copied and sample.is_file():
        sample.unlink()
    return {"applied": True, "status": copy.get("status"), "posts_copied": copied, "sample_post_removed": bool(copied)}


class ScaffoldError(RuntimeError):
    """表示必須停止且不應寫入目標目錄的錯誤。"""


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    """讀取一般 JSON 檔並拒絕 symlink。"""

    if path.is_symlink() or not path.is_file():
        raise ScaffoldError(f"{label} 必須是一般檔案：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScaffoldError(f"無法讀取 {label}：{error}") from error
    if not isinstance(payload, dict):
        raise ScaffoldError(f"{label} 根節點必須是 JSON object")
    return payload


def reject_secrets(value: Any, *, path: str = "$") -> None:
    """拒絕設定中出現秘密欄位。"""

    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if any(fragment in normalized for fragment in SECRET_KEY_FRAGMENTS):
                raise ScaffoldError(f"設定含秘密或私人識別欄位：{path}.{key}")
            reject_secrets(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_secrets(child, path=f"{path}[{index}]")


def load_config(config_path: Path) -> dict[str, Any]:
    """讀取並做最小檢查的官網設定；完整契約由 website-setup 的程式負責。"""

    config = read_json(config_path, label="官網設定")
    reject_secrets(config)
    if config.get("schema_version") != 1:
        raise ScaffoldError("官網設定 schema_version 必須是 1")
    business = config.get("business", {})
    if business.get("status") == "not_configured":
        raise ScaffoldError("商業資訊尚未設定；請先完成 website-setup 的一次訪談")
    for key in ("site_name", "one_line_positioning", "audience_summary"):
        if not business.get(key):
            raise ScaffoldError(f"商業資訊缺少 {key}，無法建立專案")
    if not business.get("offerings"):
        raise ScaffoldError("商業資訊至少需要一項服務或產品")
    cta = business.get("primary_call_to_action", {})
    if cta.get("kind") in (None, "not_selected") or not cta.get("label"):
        raise ScaffoldError("商業資訊必須指定主要行動呼籲")
    return config


def js_string(value: str) -> str:
    """輸出安全的單引號 JavaScript 字串。"""

    escaped = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("</", "<\\/")
    return f"'{escaped}'"


def render_site_config(config: dict[str, Any], site_url: str, theme_id: str) -> str:
    """把官網設定轉成 site.config.mjs。"""

    business = config["business"]
    cta = business["primary_call_to_action"]
    lines = [
        "// 站點設定：由 website-build 依 website/config.json 產生。",
        "// 不要把 API Token、帳號識別碼或任何秘密寫進這裡。",
        "",
        "/** @type {import('./src/site-config').SiteConfig} */",
        "export const site = {",
        f"  url: {js_string(site_url)},",
        f"  theme: {js_string(theme_id)},",
        f"  fonts: {js_string(config.get('design', {}).get('fonts', 'google'))},",
        f"  name: {js_string(business['site_name'])},",
        f"  positioning: {js_string(business['one_line_positioning'])},",
        f"  audience: {js_string(business['audience_summary'])},",
        f"  language: {js_string(business.get('language', 'zh-TW'))},",
        "  offerings: [",
    ]
    for offering in business["offerings"]:
        lines.append(f"    {{ name: {js_string(offering['name'])}, summary: {js_string(offering['summary'])} }},")
    lines.append("  ],")
    lines.append("  trustSignals: [")
    for signal in business.get("trust_signals", []):
        lines.append(f"    {js_string(signal)},")
    lines.append("  ],")
    target = "null" if cta.get("target") is None else js_string(cta["target"])
    lines.append(f"  cta: {{ kind: {js_string(cta['kind'])}, label: {js_string(cta['label'])}, target: {target} }},")
    lines.append("  contacts: [")
    for channel in business.get("contact_channels", []):
        lines.append(
            f"    {{ kind: {js_string(channel['kind'])}, label: {js_string(channel['label'])}, target: {js_string(channel['target'])} }},"
        )
    lines.append("  ],")
    optional = ", ".join(js_string(page) for page in config.get("pages", {}).get("optional", []))
    lines.append(f"  pages: {{ optional: [{optional}] }},")
    lines.append("  indexing: 'noindex',")
    lines.append("};")
    return "\n".join(lines) + "\n"


def render_wrangler(worker_name: str) -> str:
    """產生只含靜態資產的 wrangler.jsonc。"""

    return (
        "{\n"
        "  // 靜態站點部署設定：只上傳 astro build 產出的 dist/。\n"
        "  // 不使用 SSR adapter、不綁定 KV／D1／R2，維持免費方案。\n"
        "  // 自訂網域的 routes 由 website-deploy 在取得授權後加入。\n"
        f'  "name": "{worker_name}",\n'
        '  "compatibility_date": "2026-04-12",\n'
        '  "assets": {\n'
        '    "directory": "./dist"\n'
        "  }\n"
        "}\n"
    )


def derive_worker_name(config: dict[str, Any]) -> str:
    """取得 Worker 名稱；未設定時從站名推導出安全的 slug。"""

    explicit = config.get("hosting", {}).get("worker_name")
    if isinstance(explicit, str) and explicit:
        return explicit
    slug = re.sub(r"[^a-z0-9]+", "-", config["business"]["site_name"].lower()).strip("-")
    return (slug or "solo-site")[:63]


def load_themes(template: Path) -> dict[str, dict[str, Any]]:
    """讀取範本內所有主題描述檔。"""

    themes: dict[str, dict[str, Any]] = {}
    for path in sorted((template / THEMES_RELATIVE).glob("*/theme.json")):
        payload = read_json(path, label=f"主題描述 {path.parent.name}")
        if payload.get("id") != path.parent.name or not THEME_ID.fullmatch(str(payload.get("id"))):
            raise ScaffoldError(f"主題 id 與目錄不一致：{path}")
        for key in ("name", "tonality", "placeholder_colors"):
            if key not in payload:
                raise ScaffoldError(f"主題 {payload['id']} 缺少 {key}")
        themes[payload["id"]] = payload
    if not themes:
        raise ScaffoldError("範本沒有任何主題")
    return themes


def resolve_theme(config: dict[str, Any], config_path: Path, explicit: str | None, themes: dict[str, dict[str, Any]]) -> str:
    """決定要用的主題：命令列 > website/design.json > config.design.style_id > 預設。"""

    candidates: list[str | None] = [explicit]
    design_file = config_path.resolve().parent / "design.json"
    if design_file.is_file() and not design_file.is_symlink():
        candidates.append(str(read_json(design_file, label="設計選擇").get("theme") or ""))
    design = config.get("design", {})
    if design.get("style_source") in ("bundled", "bundled_theme") and design.get("style_id"):
        candidates.append(str(design["style_id"]))
    candidates.append(DEFAULT_THEME)
    for candidate in candidates:
        if candidate:
            if candidate not in themes:
                raise ScaffoldError(f"找不到主題：{candidate}；可用：{', '.join(sorted(themes))}")
            return candidate
    return DEFAULT_THEME


def theme_color(theme: dict[str, Any], key: str, default: str) -> str:
    """取得主題描述檔中可用於 SVG／PNG 的六位十六進位色碼。"""

    value = str(theme.get("placeholder_colors", {}).get(key, default))
    return value if HEX_COLOR.match(value) else default


def initials(name: str) -> str:
    """取站名前兩個字元作為佔位圖標記。"""

    cleaned = re.sub(r"\s+", "", name)
    return cleaned[:2] if cleaned else "S"


def svg_escape(text: str) -> str:
    """跳脫 SVG 文字。"""

    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svgs(name: str, theme: dict[str, Any]) -> dict[str, str]:
    """產生 favicon、Hero、頭像與三個服務圖示的 SVG，顏色依主題。"""

    bg = theme_color(theme, "surface_alt", "#f2f1ee")
    accent = theme_color(theme, "accent", "#1d6f8a")
    soft = theme_color(theme, "accent_soft", "#d9ecf2")
    on_accent = theme_color(theme, "on_accent", "#ffffff")
    mark = svg_escape(initials(name))
    favicon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<rect width="64" height="64" rx="14" fill="{accent}"/>'
        f'<text x="32" y="40" font-family="system-ui, sans-serif" font-size="26" font-weight="700" text-anchor="middle" fill="{on_accent}">{mark}</text>'
        "</svg>\n"
    )
    hero = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 720" role="img" aria-label="佔位圖">'
        f'<rect width="960" height="720" fill="{bg}"/>'
        f'<circle cx="700" cy="220" r="140" fill="{soft}"/>'
        f'<rect x="120" y="420" width="520" height="28" rx="14" fill="{soft}"/>'
        f'<rect x="120" y="480" width="380" height="28" rx="14" fill="{soft}"/>'
        f'<rect x="120" y="560" width="200" height="56" rx="16" fill="{accent}"/>'
        f'<text x="480" y="680" font-family="system-ui, sans-serif" font-size="22" text-anchor="middle" fill="{accent}">佔位圖：請替換為實際照片或插圖</text>'
        "</svg>\n"
    )
    avatar = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" role="img" aria-label="頭像佔位圖">'
        f'<rect width="400" height="400" rx="48" fill="{soft}"/>'
        f'<circle cx="200" cy="160" r="70" fill="{accent}"/>'
        f'<path d="M80 360c0-70 54-120 120-120s120 50 120 120" fill="{accent}"/>'
        "</svg>\n"
    )
    icons = {
        "offering-1.svg": f'<path d="M12 20h24v24H12z" fill="none" stroke="{accent}" stroke-width="3" stroke-linejoin="round"/><path d="M18 32l6 6 8-12" fill="none" stroke="{accent}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
        "offering-2.svg": f'<circle cx="24" cy="24" r="12" fill="none" stroke="{accent}" stroke-width="3"/><path d="M24 6v6M24 36v6M6 24h6M36 24h6" stroke="{accent}" stroke-width="3" stroke-linecap="round"/>',
        "offering-3.svg": f'<path d="M10 34l10-10 8 8 10-14" fill="none" stroke="{accent}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 40h28" stroke="{accent}" stroke-width="3" stroke-linecap="round"/>',
    }
    result = {"favicon.svg": favicon, "images/placeholders/hero.svg": hero, "images/placeholders/avatar.svg": avatar}
    for file_name, body in icons.items():
        result[f"images/placeholders/{file_name}"] = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" aria-hidden="true">{body}</svg>\n'
        )
    return result


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """六位十六進位轉 RGB。"""

    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def png_bytes(width: int, height: int, painter) -> bytes:
    """以標準函式庫寫出 RGB PNG；painter(x, y) 回傳 (r, g, b)。"""

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend(painter(x, y))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b"")


def build_pngs(theme: dict[str, Any]) -> dict[str, bytes]:
    """產生 OG 圖（1200x630）與 apple-touch-icon（180x180）的純色佔位 PNG，顏色依主題。"""

    bg = hex_to_rgb(theme_color(theme, "bg", "#fafaf9"))
    accent = hex_to_rgb(theme_color(theme, "accent", "#1d6f8a"))
    soft = hex_to_rgb(theme_color(theme, "accent_soft", "#d9ecf2"))

    def og_painter(x: int, y: int) -> tuple[int, int, int]:
        if y >= 590:
            return accent
        if 80 <= x < 560 and 260 <= y < 300:
            return soft
        if 80 <= x < 420 and 330 <= y < 370:
            return soft
        return bg

    def icon_painter(x: int, y: int) -> tuple[int, int, int]:
        return accent

    return {"og-image.png": png_bytes(1200, 630, og_painter), "apple-touch-icon.png": png_bytes(180, 180, icon_painter)}


def write_placeholders(public_root: Path, name: str, theme: dict[str, Any]) -> list[str]:
    """把佔位素材寫進 public/，回傳相對路徑清單。"""

    written: list[str] = []
    for relative, content in build_svgs(name, theme).items():
        target = public_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(relative)
    for relative, content in build_pngs(theme).items():
        (public_root / relative).write_bytes(content)
        written.append(relative)
    return sorted(written)


def validate_target(target: Path, template: Path) -> None:
    """目標目錄必須不存在或為空，且不得位於範本或技能包內。"""

    if target.is_symlink():
        raise ScaffoldError("目標目錄不得是 symlink")
    resolved = target.resolve(strict=False)
    if resolved == Path(resolved.anchor):
        raise ScaffoldError("目標不得是檔案系統根目錄")
    if resolved.is_relative_to(template.resolve()) or resolved.is_relative_to(PACKAGE_ROOT):
        raise ScaffoldError("目標目錄不得位於技能包或範本內")
    if resolved.exists():
        if not resolved.is_dir():
            raise ScaffoldError("目標路徑已存在且不是目錄")
        if any(resolved.iterdir()):
            raise ScaffoldError("目標目錄不是空的；不覆蓋既有專案")


def validate_template(template: Path) -> None:
    """確認範本結構完整。"""

    required = ("package.json", "astro.config.mjs", "site.config.mjs", "wrangler.jsonc", "src/styles/global.css", "src/pages/index.astro")
    for relative in required:
        if not (template / relative).is_file():
            raise ScaffoldError(f"範本缺少 {relative}")
    for page in OPTIONAL_PAGE_FILES.values():
        if not (template / "optional-pages" / page).is_file():
            raise ScaffoldError(f"範本缺少可選頁面 {page}")


def sha256_file(path: Path) -> str:
    """計算檔案雜湊。"""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan(config: dict[str, Any], template: Path, target: Path, site_url: str, theme_id: str, themes: dict[str, dict[str, Any]], config_path: Path) -> dict[str, Any]:
    """產生不寫檔的建立計畫。"""

    validate_template(template)
    validate_target(target, template)
    theme = themes[theme_id]
    optional = config.get("pages", {}).get("optional", [])
    return {
        "result": "plan",
        "template": str(template),
        "target": str(target),
        "site_url": site_url,
        "worker_name": derive_worker_name(config),
        "optional_pages": [OPTIONAL_PAGE_FILES[page] for page in optional if page in OPTIONAL_PAGE_FILES],
        "theme": theme_id,
        "theme_name": theme["name"],
        "available_themes": sorted(themes),
        "copy_layer": "workspace copy.json 存在，建立時會套用" if (config_path.resolve().parent / "copy.json").is_file() else "沿用範本預設文案（可先用 website-content-writing 撰寫）",
        "placeholders": sorted(build_svgs(config["business"]["site_name"], theme)) + ["og-image.png", "apple-touch-icon.png"],
        "lockfile_present": (template / "package-lock.json").is_file(),
        "next_steps": ["npm ci", "npm run build", "check_site.py --dist <target>/dist --config <workspace>/website/config.json"],
        "contains_credentials": False,
    }


def scaffold(config: dict[str, Any], template: Path, target: Path, site_url: str, theme_id: str, themes: dict[str, dict[str, Any]], config_path: Path) -> dict[str, Any]:
    """複製範本並寫入設定、可選頁面與佔位素材。"""

    validate_template(template)
    validate_target(target, template)
    theme = themes[theme_id]

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in TEMPLATE_EXCLUDES}

    target.mkdir(parents=True, exist_ok=True)
    for child in template.iterdir():
        if child.name in TEMPLATE_EXCLUDES or child.name == "optional-pages":
            continue
        destination = target / child.name
        if child.is_dir():
            shutil.copytree(child, destination, symlinks=False, ignore=ignore)
        else:
            shutil.copy2(child, destination, follow_symlinks=False)

    (target / "site.config.mjs").write_text(render_site_config(config, site_url, theme_id), encoding="utf-8")
    worker_name = derive_worker_name(config)
    (target / "wrangler.jsonc").write_text(render_wrangler(worker_name), encoding="utf-8")

    copied_pages: list[str] = []
    for page in config.get("pages", {}).get("optional", []):
        file_name = OPTIONAL_PAGE_FILES.get(page)
        if file_name is None:
            raise ScaffoldError(f"不支援的可選頁面：{page}")
        shutil.copy2(template / "optional-pages" / file_name, target / "src/pages" / file_name)
        copied_pages.append(file_name)

    copy_layer = apply_copy_layer(target, config_path)
    placeholders = write_placeholders(target / "public", config["business"]["site_name"], theme)
    manifest = {
        "site_config_sha256": sha256_file(target / "site.config.mjs"),
        "wrangler_sha256": sha256_file(target / "wrangler.jsonc"),
    }
    return {
        "result": "scaffolded",
        "target": str(target),
        "site_url": site_url,
        "worker_name": worker_name,
        "optional_pages": copied_pages,
        "theme": theme_id,
        "theme_name": theme["name"],
        "copy_layer": copy_layer,
        "placeholders": placeholders,
        "lockfile_present": (target / "package-lock.json").is_file(),
        "hashes": manifest,
        "next_steps": ["npm ci", "npm run build", "check_site.py"],
        "contains_credentials": False,
    }


def build_parser() -> argparse.ArgumentParser:
    """建立命令列介面。"""

    parser = argparse.ArgumentParser(description="從起始範本建立 Astro 專案")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "scaffold", "placeholders"):
        child = subparsers.add_parser(command)
        child.add_argument("--config", required=command != "placeholders")
        child.add_argument("--target", required=True)
        child.add_argument("--template", default=str(DEFAULT_TEMPLATE))
        child.add_argument("--site-url", default=DEFAULT_SITE_URL)
        child.add_argument("--theme", default=None, help="主題 id；未指定時讀 website/design.json 或設定檔")
        if command == "scaffold":
            child.add_argument("--confirm-write", action="store_true")
        if command == "placeholders":
            child.add_argument("--site-name", default="Solo Site")
    return parser


def main() -> int:
    """執行命令並輸出 JSON。"""

    args = build_parser().parse_args()
    try:
        template = Path(args.template).expanduser().resolve(strict=True)
        target = Path(args.target).expanduser()
        themes = load_themes(template)
        if not re.fullmatch(r"https://[a-z0-9.-]+(:\d+)?/?", args.site_url):
            raise ScaffoldError("site-url 必須是 https:// 開頭的主機名稱")
        if args.command == "placeholders":
            theme_id = args.theme or DEFAULT_THEME
            if theme_id not in themes:
                raise ScaffoldError(f"找不到主題：{theme_id}")
            written = write_placeholders(target, args.site_name, themes[theme_id])
            result: dict[str, Any] = {"result": "placeholders_written", "target": str(target), "files": written}
        else:
            config_path = Path(args.config).expanduser()
            config = load_config(config_path)
            theme_id = resolve_theme(config, config_path, args.theme, themes)
            if args.command == "plan":
                result = plan(config, template, target, args.site_url, theme_id, themes, config_path)
            else:
                if not args.confirm_write:
                    raise ScaffoldError("缺少 --confirm-write；未建立任何檔案")
                result = scaffold(config, template, target, args.site_url, theme_id, themes, config_path)
    except (ScaffoldError, OSError) as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
