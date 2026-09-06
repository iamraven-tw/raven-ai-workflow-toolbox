#!/usr/bin/env python3
"""Google Sheets v4 adapter 的虛構傳輸測試；不使用帳號、Token 或網路。"""

import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/social-community-management/scripts/official_sheets_api.py"
SPEC = importlib.util.spec_from_file_location("official_sheets_api", SCRIPT)
sheets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sheets)


class FakeToken:
    """提供不具任何權限的虛構字串，並記錄取得次數。"""

    def __init__(self):
        self.calls = 0

    def access(self):
        self.calls += 1
        return "fictional-token"


class FakeHTTP:
    """在記憶體回傳官方形狀資料，不建立連線。"""

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def request_json(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return sheets.HTTPResult(200, self.payloads.pop(0))


class FakeConnection:
    """讓標準函式庫 transport 在記憶體完成一次請求。"""

    def __init__(self, response):
        self.response = response
        self.calls = []
        self.closed = False

    def request(self, method, path, body=None, headers=None):
        self.calls.append((method, path, body, headers))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class FakeResponse:
    """提供固定 HTTP status 與 JSON bytes。"""

    def __init__(self, status, payload):
        self.status = status
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self, _limit):
        return self.payload


class OfficialSheetsAdapterTests(unittest.TestCase):
    def setUp(self):
        self.binding = {"spreadsheet_id": "sheet_123", "sheet_id": 7,
                        "title": "留言審核's"}

    def payload(self, data=None):
        return {"spreadsheetId": "sheet_123", "sheets": [{
            "properties": {"sheetId": 7, "title": "留言審核's"},
            "data": [] if data is None else data,
        }]}

    def adapter(self, *payloads):
        token = FakeToken()
        http = FakeHTTP(payloads)
        return sheets.OfficialSheetsAdapter(token_provider=token,
                                            http_transport=http), token, http

    def test_get_is_bound_to_one_spreadsheet_sheet_range_and_fields(self):
        adapter, token, http = self.adapter(self.payload())
        result = adapter.require_empty(self.binding)
        self.assertEqual(result["result"], "empty")
        self.assertEqual(token.calls, 1)
        method, path, kwargs = http.calls[0]
        self.assertEqual((method, path), ("GET", "/v4/spreadsheets/sheet_123"))
        self.assertEqual(kwargs["query"], {
            "ranges": "'留言審核''s'", "includeGridData": "true",
            "fields": sheets.FIELDS,
        })
        self.assertEqual(kwargs["bearer"], "fictional-token")

    def test_whole_sheet_nonempty_stops_even_outside_review_range(self):
        distant = [{"startRow": 500, "startColumn": 12, "rowData": [
            {"values": [{"userEnteredValue": {"stringValue": "occupied"}}]}
        ]}]
        adapter, _, _ = self.adapter(self.payload(distant))
        with self.assertRaisesRegex(sheets.SheetsAPIError, "sheet_not_empty"):
            adapter.require_empty(self.binding)

    def test_malformed_whole_sheet_grid_stops_with_fixed_read_error(self):
        for data in ([None], [{"rowData": "not-a-list"}],
                     [{"rowData": [None]}],
                     [{"rowData": [{"values": [None]}]}]):
            adapter, _, _ = self.adapter(self.payload(data))
            with self.subTest(data=data), self.assertRaisesRegex(
                    sheets.SheetsAPIError, "read_failed"):
                adapter.require_empty(self.binding)

    def test_sparse_grid_restores_exact_extended_value_types(self):
        data = [{"startRow": 0, "startColumn": 0, "rowData": [
            {"values": [
                {"userEnteredValue": {"stringValue": "訪客名稱"}}, {},
                {"userEnteredValue": {"formulaValue": "=1+2"}},
            ]},
            {"values": [
                {"userEnteredValue": {"stringValue": "甲"}},
                {"userEnteredValue": {"numberValue": 3}},
            ]},
        ]}]
        adapter, _, _ = self.adapter(self.payload(data))
        snapshot = adapter.read_snapshot(self.binding, 2)
        self.assertEqual(snapshot["rows"][0][0], {"stringValue": "訪客名稱"})
        self.assertEqual(snapshot["rows"][0][1], {})
        self.assertEqual(snapshot["rows"][0][2], {"formulaValue": "=1+2"})
        self.assertEqual(snapshot["rows"][1][1], {"numberValue": 3})
        self.assertEqual(len(snapshot["rows"][1]), 6)

    def test_raw_write_uses_exact_range_body_and_count_receipt(self):
        accepted = {"spreadsheetId": "sheet_123", "updatedRows": 2,
                    "updatedColumns": 6, "updatedCells": 12}
        adapter, token, http = self.adapter(accepted)
        values = [["h1", "h2", "h3", "h4", "h5", "h6"],
                  ["=1+2", "b", "c", "d", "e", "f"]]
        grant = {"binding": self.binding, "valueInputOption": "RAW",
                 "range": "'留言審核''s'!A1:F2", "majorDimension": "ROWS",
                 "values": values, "transaction_status": "claimed",
                 "approval_ref": "fictional-approval"}
        result = adapter.write_values(grant)
        self.assertEqual(result["result"], "request_accepted")
        self.assertEqual(token.calls, 1)
        method, path, kwargs = http.calls[0]
        self.assertEqual(method, "PUT")
        self.assertNotIn("留言審核", path)
        self.assertEqual(kwargs["query"], {"valueInputOption": "RAW"})
        self.assertTrue(kwargs["mutation"])
        self.assertEqual(kwargs["body"], {
            "range": "'留言審核''s'!A1:F2", "majorDimension": "ROWS",
            "values": values,
        })

    def test_write_rejects_unclaimed_user_entered_or_wrong_dimensions(self):
        base = {"binding": self.binding, "valueInputOption": "RAW",
                "range": "'留言審核''s'!A1:F2", "majorDimension": "ROWS",
                "values": [["1", "2", "3", "4", "5", "6"],
                           ["a", "b", "c", "d", "e", "f"]],
                "transaction_status": "claimed", "approval_ref": "ok"}
        adapter, token, http = self.adapter()
        for change in ({"transaction_status": "ready"},
                       {"valueInputOption": "USER_ENTERED"},
                       {"values": [["too", "short"]]},
                       {"range": "'other'!A1:F2"}):
            with self.subTest(change=change), self.assertRaises(sheets.SheetsAPIError):
                adapter.write_values(base | change)
        self.assertEqual(token.calls, 0)
        self.assertFalse(http.calls)

    def test_target_identity_mismatch_stops(self):
        for payload in (
                self.payload() | {"spreadsheetId": "other"},
                {"spreadsheetId": "sheet_123", "sheets": []},
                {"spreadsheetId": "sheet_123", "sheets": [{
                    "properties": {"sheetId": 8, "title": "留言審核's"}, "data": []}]},
        ):
            adapter, _, _ = self.adapter(payload)
            with self.subTest(payload=payload), self.assertRaisesRegex(
                    sheets.SheetsAPIError, "target_mismatch"):
                adapter.require_empty(self.binding)

    def test_error_classification_never_treats_ambiguous_write_as_retryable(self):
        cases = ((401, "reauth_required"), (403, "permission_mismatch"),
                 (429, "rate_limited"), (500, "remote_result_unknown"),
                 (302, "remote_result_unknown"))
        for status, expected in cases:
            with self.subTest(status=status), self.assertRaisesRegex(
                    sheets.SheetsAPIError, expected):
                sheets._classify(status, {"error": {"code": status}}, mutation=True)

    def test_http_transport_rejects_unapproved_paths_and_token_queries(self):
        transport = sheets.OfficialSheetsHTTP()
        for method, path, query in (
                ("POST", "/v4/spreadsheets/sheet_123", {}),
                ("GET", "/v4/spreadsheets/../secret", {}),
                ("GET", "/v4/spreadsheets/sheet_123", {"access_token": "x"})):
            with self.subTest(method=method, path=path), self.assertRaises(
                    sheets.SheetsAPIError):
                transport.request_json(method, path, query=query,
                                       bearer="fictional-token")

    def test_http_transport_accepts_encoded_a1_put_once_without_redirect_or_retry(self):
        response = FakeResponse(200, {"spreadsheetId": "sheet_123",
                                      "updatedRows": 2, "updatedColumns": 6,
                                      "updatedCells": 12})
        connection = FakeConnection(response)
        transport = sheets.OfficialSheetsHTTP()
        path = "/v4/spreadsheets/sheet_123/values/%27%E7%95%99%E8%A8%80%27%21A1%3AF2"
        with patch.object(sheets.http.client, "HTTPSConnection",
                          return_value=connection) as factory:
            result = transport.request_json(
                "PUT", path, query={"valueInputOption": "RAW"},
                body={"range": "'留言'!A1:F2", "majorDimension": "ROWS",
                      "values": [["1", "2", "3", "4", "5", "6"],
                                 ["a", "b", "c", "d", "e", "f"]]},
                bearer="fictional-token", mutation=True)
        self.assertEqual(result.status, 200)
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(len(connection.calls), 1)
        self.assertTrue(connection.closed)
        self.assertIn("valueInputOption=RAW", connection.calls[0][1])

    def test_transport_setup_failure_becomes_fixed_error_without_unbound_connection(self):
        transport = sheets.OfficialSheetsHTTP()
        with patch.object(sheets.ssl, "create_default_context",
                          side_effect=OSError("fictional setup failure")):
            with self.assertRaisesRegex(sheets.SheetsAPIError,
                                        "remote_result_unknown"):
                transport.request_json(
                    "PUT", "/v4/spreadsheets/sheet_123/values/%27A%27%21A1%3AF2",
                    query={"valueInputOption": "RAW"}, body={"values": []},
                    bearer="fictional-token", mutation=True)


if __name__ == "__main__":
    unittest.main()
