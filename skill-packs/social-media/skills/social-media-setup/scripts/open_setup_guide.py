#!/usr/bin/env python3
"""開啟隨技能安裝的唯讀教學；不連線平台、不存憑證、不更新整合狀態。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import webbrowser


ROUTES = {
    "facebook": ("page_token", "pages"),
    "instagram": ("facebook_login", "instagram_login"),
    "threads": ("threads",),
    "youtube": ("desktop",),
}


def guide_url(platform: str, route: str | None = None, step: int = 1) -> str:
    """只接受固定路線；位置由目前安裝的腳本推導，避免綁定維護者路徑。"""
    if platform not in ROUTES:
        raise ValueError("不支援的平台")
    route = route or ROUTES[platform][0]
    if route not in ROUTES[platform] or not 1 <= step <= 100:
        raise ValueError("路線或步驟不符合教學範圍")
    page = Path(__file__).resolve().parents[1] / "assets/api-setup-guide/index.html"
    if not page.is_file():
        raise FileNotFoundError("教學網頁遺失；請檢查技能安裝完整性")
    return f"{page.as_uri()}#{platform}/{route}/{step - 1}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=ROUTES)
    parser.add_argument("--route", help="Facebook：page_token 或 pages；Instagram：facebook_login 或 instagram_login")
    parser.add_argument("--step", type=int, default=1, help="從第幾步開啟，起算值為 1")
    parser.add_argument("--open", action="store_true", help="請作業系統以預設瀏覽器開啟")
    args = parser.parse_args(argv)
    try:
        url = guide_url(args.platform, args.route, args.step)
        opened = bool(webbrowser.open(url, new=2)) if args.open else False
    except (ValueError, FileNotFoundError, webbrowser.Error) as exc:
        parser.error(str(exc))
    # 開啟請求成功不保證使用者已看到，也不能表示任何平台設定已完成。
    print(json.dumps({
        "guide_url": url,
        "browser_open_requested": args.open,
        "browser_open_accepted": opened,
        "coverage": "illustrated_guide",
        "platform_verification": "not_performed",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
