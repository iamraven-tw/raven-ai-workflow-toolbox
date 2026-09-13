#!/usr/bin/env python3
"""列出範本內建主題、產生本機風格畫廊（用真實建置的預覽頁）、寫入使用者選定的主題。只用標準函式庫。"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
SOURCE_LAYOUT = SKILL_ROOT.parent.name == "skills" and (SKILL_ROOT.parents[1] / "install.manifest.toml").is_file()
PACKAGE_ROOT = SKILL_ROOT.parents[1] if SOURCE_LAYOUT else SKILL_ROOT.parent
TEMPLATE_ROOT = PACKAGE_ROOT / "template" if SOURCE_LAYOUT else SKILL_ROOT.parent / "website-build/assets/template"
THEMES_ROOT = TEMPLATE_ROOT / "src" / "themes"
PREVIEWS_ROOT = SKILL_ROOT / "assets" / "previews"
DESIGN_RELATIVE = Path("website/design.json")
CONFIG_RELATIVE = Path("website/config.json")
GALLERY_RELATIVE = Path(".local/website/style-gallery")
TONALITIES = {
    "personal_friendly": "親切個人",
    "dark_immersive": "暗黑沉浸",
    "clean_minimal": "極簡純淨",
    "photo_showroom": "攝影展廳",
    "colorful_energetic": "鮮豔活力",
    "editorial_press": "雜誌印刷",
}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
PREVIEW_PAGES = ("home", "blog", "post")
# 匯出預覽時使用的虛構內容；render 會把它們替換成使用者的站名與文案
FICTIONAL = {
    "name": "範例工作室",
    "positioning": "幫小型團隊把重複的工作交給自動化流程",
    "audience": "沒有技術團隊、想把時間留給核心工作的一人公司與小型工作室",
    "offerings": [
        ("流程盤點諮詢", "一次會談找出最值得自動化的三個流程，並給出可執行的順序。"),
        ("自動化建置", "把盤點結果做成實際運作的流程，交付時附操作說明與維護方式。"),
        ("每月維護", "定期檢查流程是否正常，並依需求調整。"),
    ],
    "trust": ["虛構的三年顧問經驗", "虛構的二十個完成案例"],
    "cta": "寫信討論",
}


class GalleryError(RuntimeError):
    """表示必須停止且不應寫入的錯誤。"""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise GalleryError(f"{label} 必須是一般檔案：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GalleryError(f"無法讀取 {label}：{error}") from error
    if not isinstance(payload, dict):
        raise GalleryError(f"{label} 根節點必須是 JSON object")
    return payload


def load_themes(themes_root: Path = THEMES_ROOT) -> list[dict[str, Any]]:
    """讀取範本內所有主題描述檔並驗證。"""

    themes: list[dict[str, Any]] = []
    for path in sorted(themes_root.glob("*/theme.json")):
        theme = read_json(path, label=f"主題描述 {path.parent.name}")
        for key in ("id", "name", "tonality", "order", "description", "fits", "source_guide", "source_license"):
            if key not in theme:
                raise GalleryError(f"主題 {path.parent.name} 缺少 {key}")
        if theme["id"] != path.parent.name or not ID_PATTERN.fullmatch(theme["id"]):
            raise GalleryError(f"主題 id 與目錄不一致：{path}")
        if theme["tonality"] not in TONALITIES:
            raise GalleryError(f"主題 {theme['id']} 的調性不支援")
        for required in ("theme.css", "BaseLayout.astro", "Home.astro", "BlogIndex.astro", "BlogPost.astro", "Header.astro", "Footer.astro"):
            if not (path.parent / required).is_file():
                raise GalleryError(f"主題 {theme['id']} 缺少 {required}")
        themes.append(theme)
    if not themes:
        raise GalleryError("範本沒有任何主題")
    missing = [key for key in TONALITIES if not any(theme["tonality"] == key for theme in themes)]
    if missing:
        raise GalleryError("有調性沒有任何主題：" + ", ".join(missing))
    return sorted(themes, key=lambda item: (item["order"], item["id"]))


def load_preview_manifest() -> dict[str, Any]:
    """讀取匯出的預覽清單；沒有就提示先執行匯出。"""

    manifest_path = PREVIEWS_ROOT / "manifest.json"
    if not manifest_path.is_file():
        raise GalleryError("找不到預覽檔；維護者需先執行 export_previews.py（需要 Node）")
    return read_json(manifest_path, label="預覽清單")


def validate_workspace_root(raw_path: str) -> Path:
    supplied = Path(raw_path).expanduser()
    if supplied.is_symlink():
        raise GalleryError("工作區根目錄不得是 symlink")
    resolved = supplied.resolve(strict=False)
    if resolved == Path(resolved.anchor):
        raise GalleryError("工作區不得是檔案系統根目錄")
    if resolved == SKILL_ROOT or resolved.is_relative_to(SKILL_ROOT) or resolved.is_relative_to(PACKAGE_ROOT):
        raise GalleryError("工作區不得位於技能包內")
    return resolved


def validate_target_path(workspace_root: Path, relative: Path, *, label: str) -> Path:
    target = workspace_root / relative
    current = workspace_root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise GalleryError(f"{label} 的父路徑不得是 symlink：{current}")
        if current.exists() and not current.is_dir():
            raise GalleryError(f"{label} 的父路徑存在檔案類型衝突：{current}")
    if target.is_symlink():
        raise GalleryError(f"{label} 不得是 symlink：{target}")
    return target


def load_site(workspace_root: Path | None) -> dict[str, Any]:
    """從工作區設定取得站名與文案；沒有就用虛構預設。"""

    site: dict[str, Any] = {
        "name": FICTIONAL["name"], "positioning": FICTIONAL["positioning"], "audience": FICTIONAL["audience"],
        "offerings": [list(item) for item in FICTIONAL["offerings"]], "trust": list(FICTIONAL["trust"]), "cta": FICTIONAL["cta"], "from_config": False,
    }
    if workspace_root is None:
        return site
    config_path = workspace_root / CONFIG_RELATIVE
    if not config_path.is_file() or config_path.is_symlink():
        return site
    business = read_json(config_path, label="官網設定").get("business", {})
    if business.get("status") == "not_configured":
        return site
    site["from_config"] = True
    for key, field in (("name", "site_name"), ("positioning", "one_line_positioning"), ("audience", "audience_summary")):
        if business.get(field):
            site[key] = str(business[field])
    offerings = business.get("offerings") or []
    if offerings:
        site["offerings"] = [[str(item.get("name", "")), str(item.get("summary", ""))] for item in offerings[:3]]
    if business.get("trust_signals"):
        site["trust"] = [str(item) for item in business["trust_signals"][:2]]
    cta = business.get("primary_call_to_action") or {}
    if cta.get("label"):
        site["cta"] = str(cta["label"])
    return site


def substitute_content(preview_html: str, site: dict[str, Any]) -> str:
    """把匯出預覽裡的虛構文案換成使用者的內容；只做精確字串替換。"""

    if not site["from_config"]:
        return preview_html
    pairs: list[tuple[str, str]] = []
    for index, (name, summary) in enumerate(FICTIONAL["offerings"]):
        if index < len(site["offerings"]):
            pairs.append((summary, site["offerings"][index][1]))
            pairs.append((name, site["offerings"][index][0]))
    for index, signal in enumerate(FICTIONAL["trust"]):
        if index < len(site["trust"]):
            pairs.append((signal, site["trust"][index]))
    pairs.append((FICTIONAL["positioning"], site["positioning"]))
    pairs.append((FICTIONAL["audience"], site["audience"]))
    pairs.append((FICTIONAL["cta"], site["cta"]))
    pairs.append((FICTIONAL["name"], site["name"]))
    for old, new in pairs:
        preview_html = preview_html.replace(html.escape(old), html.escape(new)).replace(old, html.escape(new))
    return preview_html


GALLERY_CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f4f4f2;color:#1f1f1d;font-family:"Noto Sans TC","PingFang TC",system-ui,sans-serif;line-height:1.6}
.wrap{max-width:1280px;margin:0 auto;padding:32px 24px 64px}
h1{font-size:28px;margin:0 0 8px}
.lead{margin:0 0 28px;color:#555;max-width:760px}
.grid{display:grid;gap:28px;grid-template-columns:repeat(auto-fill,minmax(380px,1fr))}
.card{background:#fff;border:1px solid #e2e0db;border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.card.recommended{outline:3px solid #1d6f8a;outline-offset:-3px}
.frame{position:relative;width:100%;aspect-ratio:16/10;overflow:hidden;background:#eee;border-bottom:1px solid #e2e0db}
.frame iframe{position:absolute;top:0;left:0;width:1280px;height:800px;border:0;transform-origin:0 0;pointer-events:none}
.meta{padding:16px 18px 18px;display:flex;flex-direction:column;gap:6px}
.title{display:flex;align-items:center;gap:8px;font-weight:600;font-size:17px;flex-wrap:wrap}
.num{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50%;background:#1f1f1d;color:#fff;font-size:13px;font-weight:600}
.badge{font-size:12px;padding:2px 8px;border-radius:999px;background:#e8e6e1;color:#444}
.badge.rec{background:#1d6f8a;color:#fff}
.desc{margin:0;font-size:14px;color:#444}
.fits{margin:0;font-size:13px;color:#777}
.links{display:flex;gap:14px;font-size:13px;margin-top:4px}
.links a{color:#1d6f8a}
.src{font-size:12px;color:#999;margin:4px 0 0}
"""


def render_gallery(themes: list[dict[str, Any]], site: dict[str, Any], recommended: str | None) -> str:
    """產生畫廊首頁：每個主題一格，用 iframe 縮放顯示真正建置出來的首頁。"""

    e = html.escape
    cards = []
    for index, theme in enumerate(themes, start=1):
        is_rec = theme["id"] == recommended
        cards.append(
            f'<article class="card{" recommended" if is_rec else ""}" id="{e(theme["id"])}">'
            f'<div class="frame"><iframe src="previews/{e(theme["id"])}/home.html" title="{e(theme["name"])} 首頁預覽" loading="lazy" tabindex="-1"></iframe></div>'
            '<div class="meta">'
            f'<div class="title"><span class="num">{index}</span><span>{e(theme["name"])}</span><span class="badge">{e(TONALITIES[theme["tonality"]])}</span>'
            + ('<span class="badge rec">建議</span>' if is_rec else "")
            + "</div>"
            f'<p class="desc">{e(theme["description"])}</p>'
            f'<p class="fits">適合：{e(theme["fits"])}　·　id: <code>{e(theme["id"])}</code></p>'
            f'<div class="links"><a href="previews/{e(theme["id"])}/home.html">首頁全尺寸</a><a href="previews/{e(theme["id"])}/blog.html">文章列表</a><a href="previews/{e(theme["id"])}/post.html">單篇文章</a></div>'
            f'<p class="src">{e(source_label(theme))}</p>'
            "</div></article>"
        )
    note = "" if site["from_config"] else "<p class=\"lead\" style=\"color:#a15c00\">目前顯示的是虛構範例內容；完成 website-setup 後重新產生畫廊，就會換成你的站名與文案。</p>"
    return (
        '<!doctype html><html lang="zh-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>風格畫廊 · {e(site["name"])}</title><meta name="robots" content="noindex"><style>{GALLERY_CSS}</style></head><body>'
        '<div class="wrap"><h1>選一個網站風格</h1>'
        f'<p class="lead">以下每一格都是「{e(site["name"])}」用該風格真正建置出來的首頁，不是示意圖。每套風格的版面、字型、間距、元件與動畫都各自不同，各參考一個公開示範頁的版面手法自行實作。回覆編號或名稱即可；之後想換風格只需重建，內容不會動。</p>{note}'
        f'<div class="grid">{"".join(cards)}</div></div>'
        "<script>function fit(){document.querySelectorAll('.frame').forEach(function(f){var s=f.clientWidth/1280;var i=f.querySelector('iframe');if(i){i.style.transform='scale('+s+')';}});}fit();window.addEventListener('resize',fit);</script>"
        "</body></html>"
    )


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()



def source_label(theme: dict[str, Any]) -> str:
    """卡片上的來源說明：設計指引型寫指引名稱與授權；版面參考型寫參考網址並聲明未複製程式碼。"""

    if theme.get("source_kind") == "layout_reference":
        refs = "、".join(str(url) for url in theme.get("source_references", []))
        return f"版面參考（只借鏡版面手法與動畫類型，未複製程式碼與素材）：{refs}"
    return f"設計指引來源：open-design／{theme['source_guide']}（{theme['source_license']}）"


def recommend_theme(themes: list[dict[str, Any]], tonality: str | None) -> str | None:
    if tonality is None or tonality == "not_selected":
        return None
    if tonality not in TONALITIES:
        raise GalleryError(f"調性不支援：{tonality}")
    for theme in themes:
        if theme["tonality"] == tonality:
            return theme["id"]
    return None


def command_list(themes: list[dict[str, Any]], recommend: str | None) -> dict[str, Any]:
    return {
        "result": "themes",
        "count": len(themes),
        "recommended": recommend_theme(themes, recommend),
        "themes": [
            {"index": index, "id": theme["id"], "name": theme["name"], "tonality": theme["tonality"], "description": theme["description"], "fits": theme["fits"], "source_guide": theme["source_guide"], "source_kind": theme.get("source_kind", "design_guide"), "source_references": theme.get("source_references", [])}
            for index, theme in enumerate(themes, start=1)
        ],
    }


def command_render(themes: list[dict[str, Any]], workspace_root: Path, recommend: str | None) -> dict[str, Any]:
    """把畫廊與六個主題的預覽頁寫進工作區的本機目錄，並替換成使用者內容。"""

    manifest = load_preview_manifest()
    exported = {record["id"]: record for record in manifest.get("themes", [])}
    site = load_site(workspace_root)
    recommended = recommend_theme(themes, recommend)
    gallery_root = validate_target_path(workspace_root, GALLERY_RELATIVE / "index.html", label="畫廊").parent
    if gallery_root.exists() and not gallery_root.is_dir():
        raise GalleryError("畫廊目錄存在檔案類型衝突")
    written: list[str] = []
    for theme in themes:
        record = exported.get(theme["id"])
        if record is None:
            raise GalleryError(f"主題 {theme['id']} 沒有匯出的預覽；請維護者重新執行 export_previews.py")
        for page in PREVIEW_PAGES:
            source = PREVIEWS_ROOT / record["pages"][page]["file"]
            if not source.is_file():
                raise GalleryError(f"預覽檔不存在：{source}")
            target = gallery_root / "previews" / theme["id"] / f"{page}.html"
            write_text_atomic(target, substitute_content(source.read_text(encoding="utf-8"), site))
            written.append(str(target))
    samples_src = PREVIEWS_ROOT / "images" / "samples"
    if samples_src.is_dir():
        samples_dst = gallery_root / "previews" / "images" / "samples"
        samples_dst.mkdir(parents=True, exist_ok=True)
        for photo in samples_src.glob("*"):
            if photo.is_file() and not photo.is_symlink():
                (samples_dst / photo.name).write_bytes(photo.read_bytes())
                written.append(str(samples_dst / photo.name))
    write_text_atomic(gallery_root / "index.html", render_gallery(themes, site, recommended))
    return {
        "result": "rendered",
        "gallery": str(gallery_root / "index.html"),
        "previews": written,
        "site_name": site["name"],
        "content_source": "website/config.json" if site["from_config"] else "fictional_defaults",
        "recommended": recommended,
        "count": len(themes),
        "open_hint": "用瀏覽器工具開啟 gallery 路徑並截圖；畫廊用 iframe 載入預覽，需以 http 伺服器或瀏覽器直接開啟檔案。字型來自 Google Fonts，需要網路才會顯示各主題的中文字型。",
        "contains_credentials": False,
    }


def command_select(themes: list[dict[str, Any]], workspace_root: Path, theme_id: str, *, confirmed: bool, replace: bool) -> dict[str, Any]:
    """把選定主題寫入 website/design.json。"""

    if not confirmed:
        raise GalleryError("缺少 --confirm-write；未寫入任何檔案")
    matches = [theme for theme in themes if theme["id"] == theme_id]
    if not matches:
        raise GalleryError(f"找不到主題：{theme_id}")
    theme = matches[0]
    target = validate_target_path(workspace_root, DESIGN_RELATIVE, label="設計選擇")
    if target.exists():
        existing = read_json(target, label="既有設計選擇")
        if existing.get("theme") != theme["id"] and not replace:
            raise GalleryError(f"既有設計選擇是 {existing.get('theme')}；要換主題請加 --replace")
    payload = {
        "schema_version": 1,
        "theme": theme["id"],
        "name": theme["name"],
        "tonality": theme["tonality"],
        "source_guide": theme["source_guide"],
        "selected_at": utc_now(),
        "contains_credentials": False,
    }
    write_text_atomic(target, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {
        "result": "selected",
        "theme": theme["id"],
        "name": theme["name"],
        "tonality": theme["tonality"],
        "design_target": str(target),
        "design_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "config_patch": {"design": {"status": "confirmed", "tonality": theme["tonality"], "style_source": "bundled", "style_id": theme["id"]}},
        "next_step": "以 website-setup 的 manage_workspace.py 預覽並確認 config_patch；建站時 scaffold_site.py 會自動讀取 website/design.json。",
        "contains_credentials": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="內建主題風格畫廊")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--recommend", default=None, help="調性 id，回傳建議主題")
    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--workspace-root", required=True)
    render_parser.add_argument("--recommend", default=None)
    select_parser = subparsers.add_parser("select")
    select_parser.add_argument("--workspace-root", required=True)
    select_parser.add_argument("--theme", required=True)
    select_parser.add_argument("--confirm-write", action="store_true")
    select_parser.add_argument("--replace", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        themes = load_themes()
        if args.command == "list":
            result = command_list(themes, args.recommend)
        elif args.command == "render":
            result = command_render(themes, validate_workspace_root(args.workspace_root), args.recommend)
        elif args.command == "select":
            result = command_select(themes, validate_workspace_root(args.workspace_root), args.theme, confirmed=args.confirm_write, replace=args.replace)
        else:
            raise GalleryError("未知命令")
    except (GalleryError, OSError) as error:
        print(json.dumps({"result": "stopped", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
