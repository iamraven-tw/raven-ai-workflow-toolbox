#!/usr/bin/env python3
"""唯讀判斷製圖路徑；不呼叫模型、不操作瀏覽器、不寫入設定。"""

import argparse
import json
from pathlib import Path

METHODS = ("codex", "antigravity", "web", "html_css")


def select_visual(config, override=None):
    """四路共用視覺來源；本次覆寫不修改保存設定。"""
    fields = {"primary_color", "secondary_color", "background_color", "text_color",
              "font_family", "style_notes", "logo_ref", "main_visual_ref"}
    saved = config.get("brand_visual")
    if config.get("schema_version") == 5:
        if not isinstance(saved, dict) or set(saved) != fields | {"status"} or saved["status"] not in ("not_configured", "confirmed"):
            raise ValueError("品牌視覺格式不完整")
    elif saved is not None:
        raise ValueError("舊版不得夾帶品牌欄位")
    visual = {key: saved[key] for key in fields if saved[key] is not None} if saved and saved["status"] == "confirmed" else {}
    sources = {key: "saved_brand" for key in visual}
    if override is not None:
        if not isinstance(override, dict) or not set(override) <= fields:
            raise ValueError("本次視覺覆寫欄位不支援")
        visual.update(override)
        sources.update({key: "current_request" for key in override})
    return {"values": visual, "sources": sources, "missing": sorted(fields - visual.keys()), "writes_config": False}


def select_route(config, *, method=None, information_dense=False, browser_requested=False, visual_override=None):
    """本次明確方式優先；設定只是偏好，不是瀏覽器或新增費用授權。"""
    if not isinstance(config, dict):
        raise ValueError("設定必須為 object")
    version = config.get("schema_version")
    if type(version) is not int or version not in (3, 4, 5):
        raise ValueError("不支援的設定版本")
    if version == 3:
        if "image_production" in config:
            raise ValueError("舊版設定不得夾帶新版圖片欄位")
        preferences = None
    else:
        preferences = config.get("image_production")
        fields = {"default_method", "information_dense_method", "web_provider", "icon_source"}
        if not isinstance(preferences, dict) or set(preferences) != fields:
            raise ValueError("圖片偏好格式不完整")
        if preferences["default_method"] not in ("not_configured", *METHODS):
            raise ValueError("製圖方式不支援")
        if preferences["information_dense_method"] not in ("inherit", "html_css") or preferences["icon_source"] not in ("heroicons", "none"):
            raise ValueError("資訊圖卡或圖示偏好不支援")
        provider = preferences["web_provider"]
        if provider is not None and (not isinstance(provider, str) or not provider.strip() or len(provider) > 100):
            raise ValueError("網頁模型名稱無效")
    if method is not None and method not in METHODS:
        raise ValueError("本次製圖方式不支援")
    visual = select_visual(config, visual_override)
    selected = method or (preferences or {}).get("default_method", "not_configured")
    basis = "current_request" if method else "saved_preference"
    if selected == "not_configured":
        return {"result": "needs_preference", "question_count": 1, "writes_config": False, "publishing_authorized": False}
    if method is None and information_dense and preferences["information_dense_method"] == "html_css":
        selected, basis = "html_css", "saved_information_dense_preference"
    action = {"codex": "direct_generate", "antigravity": "direct_generate", "web": "deliver_prompt", "html_css": "render_html"}[selected]
    if selected == "web" and browser_requested:
        action = "operate_browser_with_current_request"
    return {"result": "route_selected", "method": selected, "action": action, "basis": basis,
            "browser_requested": selected == "web" and browser_requested,
            "visual": visual, "writes_config": False, "publishing_authorized": False}


def main():
    """旗標只是記錄當次請求，不能代替人類授權證據。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--information-dense", action="store_true")
    parser.add_argument("--browser-requested", action="store_true")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {"schema_version": 3}
        result = select_route(config, method=args.method, information_dense=args.information_dense, browser_requested=args.browser_requested)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["result"] == "route_selected" else 2
    except (ValueError, OSError, TypeError) as exc:
        # 不回顯一般設定內容或解析器的可能私人路徑。
        print(json.dumps({"result": "blocked", "reason": type(exc).__name__, "writes_config": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
