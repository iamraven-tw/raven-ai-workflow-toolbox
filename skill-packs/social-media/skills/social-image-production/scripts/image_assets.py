#!/usr/bin/env python3
"""以既有 Pillow 產生文字圖卡，或唯讀驗證 AI／排版圖片交付。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path


class ImageError(ValueError):
    """可回報給使用者的本機檢查錯誤。"""


def require(condition, message):
    """不使用可被最佳化移除的 assert 作輸入檢查。"""
    if not condition:
        raise ImageError(message)


def pillow():
    """延後載入既有依賴，絕不自動安裝。"""
    try:
        from PIL import Image, ImageDraw, ImageFont, __version__
    except ImportError as exc:
        raise ImageError("缺少 Pillow；未安裝任何套件，請保留簡報") from exc
    return Image, ImageDraw, ImageFont, __version__


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    """要求可解析且帶時區的時間。"""
    try:
        require(datetime.fromisoformat(value).utcoffset() is not None, "時間缺少時區")
    except (TypeError, ValueError) as exc:
        raise ImageError("時間格式無效或缺少時區") from exc


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(record):
    """綁定實際內容與檢查紀錄，不把核准自我納入雜湊。"""
    payload = {k: v for k, v in record.items() if k not in {"status", "approval"}}
    return sha(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())


def validate_brief(brief):
    """驗證單一用途與固定順序，資源上限不是平台限制。"""
    require(isinstance(brief, dict) and brief.get("schema_version") == 1, "簡報版本無效")
    require(brief.get("platform") in {"youtube", "instagram", "facebook", "threads", "substack"}, "平台無效")
    require(brief.get("kind") in {"cover", "single", "carousel"}, "圖片用途無效")
    for key in ("input_ref", "visual"):
        require(nonempty(brief.get(key)), f"缺少 {key}")
    for key in ("width", "height"):
        require(type(brief.get(key)) is int and 64 <= brief[key] <= 4096, "畫布必須介於 64–4096 pixels")
    sources = brief.get("sources")
    require(isinstance(sources, list) and sources, "缺少來源／權利紀錄")
    for source in sources:
        require(isinstance(source, dict) and all(nonempty(source.get(k)) for k in ("ref", "rights")), "來源紀錄不完整")
    pages = brief.get("pages")
    require(isinstance(pages, list) and 1 <= len(pages) <= 20, "頁數超過本機資源範圍")
    require(len(pages) >= 2 if brief["kind"] == "carousel" else len(pages) == 1, "用途與頁數不符")
    ids = set()
    for page in pages:
        require(isinstance(page, dict), "頁面格式無效")
        key = page.get("id")
        require(isinstance(key, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", key), "頁面 ID 無效")
        require(key not in ids, "頁面 ID 重複")
        ids.add(key)
        require(isinstance(page.get("exact_text"), str) and len(page["exact_text"]) <= 4000, "圖上文字無效或過長")
        require(all(c == "\n" or ord(c) >= 32 for c in page["exact_text"]), "文字含控制字元")
        require(nonempty(page.get("alt_text")), "缺少替代文字")


def no_symlink(path):
    """保留使用者選定位置，拒絕任一層符號連結。"""
    absolute = path.absolute()
    require(all(not part.is_symlink() for part in [absolute, *absolute.parents]), "路徑含 symlink")


def asset_info(data):
    """先看尺寸限制才解碼，拒絕動畫或不支援的色彩模式。"""
    Image, _, _, _ = pillow()
    require(len(data) <= 64 * 1024 * 1024, "圖片超過本機檢查容量")
    with Image.open(io.BytesIO(data)) as im:
        require(im.format in {"PNG", "JPEG"} and im.mode in {"RGB", "RGBA", "L"}, "不支援的格式／色彩模式")
        require(getattr(im, "n_frames", 1) == 1, "不接受動畫圖片")
        require(64 <= im.width <= 4096 and 64 <= im.height <= 4096, "實際圖片超過資源限制")
        im.load()
        return {"sha256": sha(data), "bytes": len(data), "width": im.width, "height": im.height, "format": im.format}


def wrap_text(draw, text, font, width):
    """依實際文字邊界換行，不刪字、不偷偷縮小字級。"""
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            bounds = draw.textbbox((0, 0), current + char, font=font)
            if bounds[2] - bounds[0] > width:
                require(bool(current), "單字元超過可用寬度")
                lines.append(current)
                current = char
                bounds = draw.textbbox((0, 0), current, font=font)
                require(bounds[2] - bounds[0] <= width, "單字元超過可用寬度")
            else:
                current += char
        lines.append(current)
    return "\n".join(lines)


def render(brief, font_path, font_rights, output):
    """新版本才可寫入；所有頁面先渲染成功，不產生半份溢位輸出。"""
    validate_brief(brief)
    no_symlink(output)
    require(output.parent.is_dir() and not output.exists(), "輸出必須是既有父目錄下的全新目錄")
    require(font_path.is_file() and nonempty(font_rights), "缺少本機字型或權利說明")
    Image, ImageDraw, ImageFont, version = pillow()
    layout = brief.get("layout")
    require(isinstance(layout, dict), "缺少排版參數")
    size, margin = layout.get("font_size"), layout.get("margin")
    require(type(size) is int and 8 <= size <= 512, "字級無效")
    require(type(margin) is int and 0 <= margin < min(brief["width"], brief["height"]) / 2, "留白無效")
    for key in ("background", "foreground"):
        require(isinstance(layout.get(key), str) and re.fullmatch(r"#[0-9a-fA-F]{6}", layout[key]), "顏色需為 #RRGGBB")
    font_data = font_path.read_bytes()
    font = ImageFont.truetype(io.BytesIO(font_data), size=size)
    buffers, assets = [], []
    for index, page in enumerate(brief["pages"], 1):
        require(nonempty(page["exact_text"]), "文字備援不製作無字圖")
        im = Image.new("RGB", (brief["width"], brief["height"]), layout["background"])
        draw = ImageDraw.Draw(im)
        text = wrap_text(draw, page["exact_text"], font, im.width - margin * 2)
        spacing = max(4, size // 4)
        bounds = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
        require(bounds[2] - bounds[0] <= im.width - margin * 2 and bounds[3] - bounds[1] <= im.height - margin * 2, "文字溢位；未截字、未寫入圖片")
        draw.multiline_text((margin - bounds[0], margin - bounds[1]), text, font=font, fill=layout["foreground"], spacing=spacing)
        buffer = io.BytesIO()
        im.save(buffer, format="PNG")
        data = buffer.getvalue()
        filename = f"{index:02d}-{page['id']}.png"
        buffers.append((filename, data))
        assets.append({"id": page["id"], "file": filename, **asset_info(data)})
    record = {
        "schema_version": 1, "brief": copy.deepcopy(brief),
        "production": {"route": "text_layout", "tool": "Pillow " + version, "model": "not_applicable",
                       "source_refs": [s["ref"] for s in brief["sources"]],
                       "font_sha256": sha(font_data), "font_rights": font_rights,
                       "created_at": datetime.now(timezone.utc).isoformat()},
        "assets": assets, "unresolved": [], "visual_review": None, "status": "draft", "approval": None,
    }
    output.mkdir()  # 原子建立全新目錄；寫入中斷時保留現場，不自動刪除。
    for filename, data in buffers:
        with (output / filename).open("xb") as handle:
            handle.write(data)
    with (output / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return record


def check(record, root, handoff=False):
    """唯讀交接檢查；雜湊不是本人簽章，也不授權發布。"""
    no_symlink(root)
    require(isinstance(record, dict) and record.get("schema_version") == 1, "成品紀錄版本無效")
    brief = record.get("brief")
    validate_brief(brief)
    production = record.get("production")
    require(isinstance(production, dict) and production.get("route") in {"ai", "text_layout", "html_css"}, "缺少製作路徑")
    for key in ("tool", "model"):
        require(nonempty(production.get(key)), "製作紀錄不完整")
    refs = production.get("source_refs")
    require(isinstance(refs, list) and refs and all(nonempty(r) for r in refs), "缺少製作來源參照")
    timestamp(production.get("created_at"))
    if production["route"] == "ai":
        require(nonempty(production.get("prompt_ref")), "AI 製作缺少提示詞紀錄參照")
    elif production["route"] == "text_layout":
        require(nonempty(production.get("font_rights")) and re.fullmatch(r"[0-9a-f]{64}", production.get("font_sha256", "")), "字型紀錄不完整")
    else:
        require(production.get("model") == "not_applicable", "HTML 排版不是 AI 模型")
    assets = record.get("assets")
    require(isinstance(assets, list) and len(assets) == len(brief["pages"]), "圖片數量不符")
    filenames = set()
    for page, asset in zip(brief["pages"], assets):
        require(isinstance(asset, dict) and asset.get("id") == page["id"], "圖片順序／ID 不符")
        filename = asset.get("file")
        require(isinstance(filename, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\.(png|jpg|jpeg)", filename), "檔案必須是版本內單層圖片名稱")
        require(filename not in filenames, "圖片檔案重複")
        filenames.add(filename)
        path = root / filename
        require(path.is_file() and not path.is_symlink(), "圖片缺少或為 symlink")
        require(path.stat().st_size <= 64 * 1024 * 1024, "圖片超過本機檢查容量")
        actual = asset_info(path.read_bytes())
        require(all(asset.get(k) == v for k, v in actual.items()), "圖片內容與紀錄不符")
        require(actual["width"] == brief["width"] and actual["height"] == brief["height"], "圖片尺寸與簡報不符")
        require((actual["format"] == "PNG") == filename.endswith(".png"), "副檔名與格式不符")
    unresolved = record.get("unresolved")
    require(isinstance(unresolved, list) and all(nonempty(v) for v in unresolved), "待解事項格式無效")
    review = record.get("visual_review")
    if review is not None:
        require(isinstance(review, dict) and review.get("checked") is True and nonempty(review.get("review_ref")), "視覺檢查紀錄無效")
        timestamp(review.get("checked_at"))
    require(record.get("status") in {"draft", "approved"}, "狀態無效")
    value = digest(record)
    if record["status"] == "approved":
        approval = record.get("approval")
        require(isinstance(approval, dict) and approval.get("scope") == "images_only" and approval.get("digest") == value, "核准缺少或已失效")
        require(all(nonempty(approval.get(k)) for k in ("user_response", "evidence_ref")), "缺少使用者確認證據")
        timestamp(approval.get("confirmed_at"))
    else:
        require(record.get("approval") is None, "草稿不應帶有核准")
    if handoff:
        require(not unresolved and review is not None and record["status"] == "approved", "交接需要解決問題、視覺檢查與使用者核准")
    return {"result": "valid", "digest": value, "count": len(assets), "publishing_authorized": False}


def main():
    """命令列不接收秘密，失敗不自動重試或安裝依賴。"""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("render")
    make.add_argument("brief", type=Path)
    make.add_argument("--font", type=Path, required=True)
    make.add_argument("--font-rights", required=True)
    make.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("check")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("--handoff", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "render":
            record = render(json.loads(args.brief.read_text(encoding="utf-8")), args.font, args.font_rights, args.output)
            result = check(record, args.output)
        else:
            no_symlink(args.manifest)
            result = check(json.loads(args.manifest.read_text(encoding="utf-8")), args.manifest.parent, args.handoff)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({"result": "blocked", "reason": str(exc), "publishing_authorized": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
