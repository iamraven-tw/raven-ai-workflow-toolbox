#!/usr/bin/env python3
"""由 Agent 安全執行第 8 課四個真實 Webhook 測試。"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from getpass import getpass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


WEB_APP_URL_PATTERN = re.compile(
    r"^https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec$"
)
REQUEST_ID = "LESSON08-DEMO-REQUEST-001"
EXPECTED_CODES = ("INVALID_JSON", "INVALID_TOKEN", "OK_OR_DUPLICATE", "DUPLICATE")


def validate_inputs(url: str, token: str) -> None:
    """先驗證輸入格式，避免把請求送到錯誤位置。"""
    if not WEB_APP_URL_PATTERN.fullmatch(url):
        raise ValueError("網頁應用程式網址格式不正確，必須是版本化 /exec 網址")
    if not 24 <= len(token) <= 200 or "\n" in token or "\r" in token:
        raise ValueError("臨時教學密語長度或格式不正確")


def send_request(url: str, payload: str) -> dict[str, Any]:
    """送出單一 JSON 請求，只回傳安全的應用層結果。"""
    request = Request(
        url,
        data=payload.encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Learn-GAS-Lesson08-Agent-Test",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw_response = response.read().decode("utf-8")
    except HTTPError as error:
        raise RuntimeError(f"網路請求失敗｜HTTP 狀態={error.code}") from error
    except URLError as error:
        raise RuntimeError("無法連線到第 8 課公開測試入口") from error

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as error:
        raise RuntimeError("公開測試入口沒有回傳有效 JSON") from error
    if not isinstance(result, dict):
        raise RuntimeError("公開測試入口回傳格式不正確")

    # 只保留不含網址、密語或原始本文的安全摘要。
    return {
        "ok": bool(result.get("ok")),
        "code": str(result.get("code", "")),
        "message": str(result.get("message", "")),
    }


def build_payloads(token: str) -> list[str]:
    """建立無效格式、錯誤密語、正常與重送四個請求。"""
    valid_payload = {
        "token": token,
        "requestId": REQUEST_ID,
        "name": "第8課 Webhook 範例",
        "email": "lesson08@example.com",
        "session": "上午場",
        "source": "learn-gas-lesson-08",
    }
    return [
        "{",
        json.dumps(
            {**valid_payload, "token": f"{token}-wrong"},
            ensure_ascii=False,
        ),
        json.dumps(valid_payload, ensure_ascii=False),
        json.dumps(valid_payload, ensure_ascii=False),
    ]


def run_tests(
    url: str,
    token: str,
    sender: Callable[[str, str], dict[str, Any]] = send_request,
) -> list[dict[str, Any]]:
    """依固定順序送出四個請求並驗證回應碼。"""
    validate_inputs(url, token)
    results = [sender(url, payload) for payload in build_payloads(token)]

    if results[0].get("code") != EXPECTED_CODES[0]:
        raise RuntimeError("第 1 個請求未回傳 INVALID_JSON")
    if results[1].get("code") != EXPECTED_CODES[1]:
        raise RuntimeError("第 2 個請求未回傳 INVALID_TOKEN")
    if results[2].get("code") not in {"OK", "DUPLICATE"}:
        raise RuntimeError("第 3 個請求未回傳 OK 或 DUPLICATE")
    if results[3].get("code") != EXPECTED_CODES[3]:
        raise RuntimeError("第 4 個請求未回傳 DUPLICATE")
    return results


def main() -> int:
    """從隱藏輸入取得網址與密語，避免出現在命令或終端輸出。"""
    url = getpass("請貼上 WEB_APP_URL（輸入不顯示）：").strip()
    token = getpass("請貼上 WEBHOOK_TOKEN（輸入不顯示）：").strip()
    try:
        results = run_tests(url, token)
    except (ValueError, RuntimeError) as error:
        print(f"[失敗] {error}", file=sys.stderr)
        return 1

    for index, result in enumerate(results, start=1):
        print(
            f"[結果] 請求={index}｜code={result['code']}｜message={result['message']}"
        )
    print("[成功] 第 8 課真實 Webhook 測試完成｜請求數=4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
