#!/usr/bin/env python3
"""測試第 8 課 Agent 端安全 Webhook 測試工具。"""

from __future__ import annotations

import json
import unittest

from run_lesson08_webhook_tests import build_payloads, run_tests, validate_inputs


VALID_URL = "https://script.google.com/macros/s/TEST_DEPLOYMENT_ID/exec"
VALID_TOKEN = "a" * 64


class Lesson08WebhookToolTests(unittest.TestCase):
    """確認固定四請求、去重與敏感值處理規則。"""

    def test_build_payloads_uses_fixed_safe_sequence(self) -> None:
        payloads = build_payloads(VALID_TOKEN)

        self.assertEqual(len(payloads), 4)
        self.assertEqual(payloads[0], "{")
        wrong = json.loads(payloads[1])
        valid = json.loads(payloads[2])
        duplicate = json.loads(payloads[3])
        self.assertEqual(wrong["token"], f"{VALID_TOKEN}-wrong")
        self.assertEqual(valid, duplicate)
        self.assertEqual(valid["requestId"], "LESSON08-DEMO-REQUEST-001")
        self.assertEqual(valid["email"], "lesson08@example.com")

    def test_run_tests_accepts_expected_codes(self) -> None:
        expected = [
            {"ok": False, "code": "INVALID_JSON", "message": "格式錯誤"},
            {"ok": False, "code": "INVALID_TOKEN", "message": "驗證失敗"},
            {"ok": True, "code": "OK", "message": "新增成功"},
            {"ok": True, "code": "DUPLICATE", "message": "已處理"},
        ]
        calls: list[str] = []

        def fake_sender(url: str, payload: str) -> dict[str, object]:
            self.assertEqual(url, VALID_URL)
            calls.append(payload)
            return expected[len(calls) - 1]

        self.assertEqual(run_tests(VALID_URL, VALID_TOKEN, fake_sender), expected)
        self.assertEqual(len(calls), 4)

    def test_validate_inputs_rejects_unsafe_values(self) -> None:
        with self.assertRaises(ValueError):
            validate_inputs("https://example.com/exec", VALID_TOKEN)
        with self.assertRaises(ValueError):
            validate_inputs(VALID_URL, "too-short")


if __name__ == "__main__":
    unittest.main()
