#!/usr/bin/env python3
"""六欄審核表的受限 Google Sheets v4 adapter；不建立或保存 OAuth。"""

from __future__ import annotations

from datetime import datetime, timezone
import http.client
import json
import re
import ssl
from urllib.parse import quote, urlencode


SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
FIELDS = ("spreadsheetId,sheets(properties(sheetId,title),"
          "data(startRow,startColumn,rowData(values(userEnteredValue))))")


class SheetsAPIError(RuntimeError):
    """只回傳固定錯誤類型，不夾帶儲存格、Token 或平台回應。"""

    ALLOWED = {
        "authorization_required", "adapter_unavailable", "reauth_required",
        "permission_mismatch", "target_mismatch", "sheet_not_empty",
        "rate_limited", "read_failed", "rejected", "remote_result_unknown",
        "response_too_large",
    }

    def __init__(self, kind):
        self.kind = kind if kind in self.ALLOWED else "read_failed"
        super().__init__(self.kind)


class HTTPResult:
    """只在可信程序記憶體保存必要回應。"""

    __slots__ = ("status", "payload")

    def __init__(self, status, payload):
        self.status = status
        self.payload = payload


def _now():
    """產生帶時區的實際觀測時間。"""

    return datetime.now(timezone.utc).isoformat()


def _identifier(value):
    """限制試算表識別，避免路徑與查詢字串注入。"""

    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{3,200}", value):
        raise SheetsAPIError("target_mismatch")
    return value


def _title(value):
    """限制工作表標題；A1 引用時再將單引號加倍。"""

    if (not isinstance(value, str) or not value or len(value) > 100
            or any(ord(char) < 32 for char in value)):
        raise SheetsAPIError("target_mismatch")
    return value


def _binding(value):
    """驗證本機保存的試算表與分頁綁定。"""

    if not isinstance(value, dict) or set(value) != {"spreadsheet_id", "sheet_id", "title"}:
        raise SheetsAPIError("target_mismatch")
    _identifier(value["spreadsheet_id"])
    if type(value["sheet_id"]) is not int or value["sheet_id"] < 0:
        raise SheetsAPIError("target_mismatch")
    _title(value["title"])
    return value


def _a1_title(title):
    """建立不受標題特殊字元影響的 A1 工作表引用。"""

    return "'" + _title(title).replace("'", "''") + "'"


def _token(value):
    """拒絕空白與可注入 HTTP header 的 Token。"""

    if not isinstance(value, str) or not value or "\r" in value or "\n" in value:
        raise SheetsAPIError("authorization_required")
    return value


def _payload(value, *, mutation=False):
    """空白或非 JSON 物件不能被當作成功。"""

    if not isinstance(value, dict):
        raise SheetsAPIError("remote_result_unknown" if mutation else "read_failed")
    return value


def _classify(status, value, *, mutation):
    """分類錯誤而不保留外部錯誤內容；寫入不自動重試。"""

    error = value.get("error") if isinstance(value, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    if status == 401:
        raise SheetsAPIError("reauth_required")
    if status == 403:
        raise SheetsAPIError("permission_mismatch")
    if status == 429:
        raise SheetsAPIError("rate_limited")
    if not 200 <= status < 300 or error:
        if mutation and (300 <= status < 400 or status >= 500):
            raise SheetsAPIError("remote_result_unknown")
        if code in {401, 403, 429}:
            raise SheetsAPIError({401: "reauth_required", 403: "permission_mismatch",
                                  429: "rate_limited"}[code])
        raise SheetsAPIError("rejected" if mutation else "read_failed")


class GoogleAuthTokenProvider:
    """沿用既有 Application Default Credentials，不建立或匯出憑證。"""

    def access(self):
        """只在真正執行時匯入 google-auth，刷新值留在記憶體。"""

        try:
            import google.auth
            from google.auth.transport.requests import Request

            credentials, _ = google.auth.default(scopes=[SHEETS_SCOPE])
            if not credentials.valid:
                credentials.refresh(Request())
            return _token(credentials.token)
        except SheetsAPIError:
            raise
        except Exception:
            raise SheetsAPIError("reauth_required") from None


class OfficialSheetsHTTP:
    """只連 sheets.googleapis.com 的 spreadsheets.get 與 values.update。"""

    MAX_RESPONSE = 4 * 1024 * 1024

    def request_json(self, method, path, *, query=None, body=None, bearer=None,
                     mutation=False):
        """送出單次 API 請求；不跟隨重新導向、不重試。"""

        method = str(method).upper()
        allowed_get = bool(re.fullmatch(r"/v4/spreadsheets/[A-Za-z0-9_-]{3,200}", path))
        allowed_put = bool(re.fullmatch(
            r"/v4/spreadsheets/[A-Za-z0-9_-]{3,200}/values/[A-Za-z0-9%_.~'-]+", path))
        if not ((method == "GET" and allowed_get) or (method == "PUT" and allowed_put)):
            raise SheetsAPIError("target_mismatch")
        if not isinstance(query, dict) or any(str(key).lower() in {
                "access_token", "token", "authorization"} for key in query):
            raise SheetsAPIError("authorization_required")
        headers = {
            "Accept": "application/json", "Cache-Control": "no-store",
            "Authorization": "Bearer " + _token(bearer),
        }
        encoded = None
        if body is not None:
            if not isinstance(body, dict):
                raise SheetsAPIError("remote_result_unknown")
            encoded = json.dumps(body, ensure_ascii=False,
                                 separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=UTF-8"
            headers["Content-Length"] = str(len(encoded))
        request_path = path + "?" + urlencode(query, doseq=True)
        connection = None
        try:
            connection = http.client.HTTPSConnection(
                "sheets.googleapis.com", timeout=60, context=ssl.create_default_context())
            connection.request(method, request_path, body=encoded, headers=headers)
            response = connection.getresponse()
            raw = response.read(self.MAX_RESPONSE + 1)
            if len(raw) > self.MAX_RESPONSE:
                raise SheetsAPIError("response_too_large")
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                value = None
            _classify(response.status, value, mutation=mutation)
            return HTTPResult(response.status, value)
        except SheetsAPIError:
            raise
        except Exception:
            raise SheetsAPIError("remote_result_unknown" if mutation else "read_failed") from None
        finally:
            if connection is not None:
                connection.close()


class OfficialSheetsAdapter:
    """驗證專用分頁、RAW 寫入六欄，並讀回 userEnteredValue 型別。"""

    def __init__(self, *, token_provider=None, http_transport=None):
        self.token_provider = token_provider or GoogleAuthTokenProvider()
        self.http = http_transport or OfficialSheetsHTTP()
        self._access_token = None

    def _access(self):
        """單次程序只取得一次 Token，避免把刷新混入每個 GET。"""

        if self._access_token is None:
            self._access_token = _token(self.token_provider.access())
        return self._access_token

    def _get(self, binding, range_a1):
        """只讀指定分頁與必要 CellData 欄位。"""

        binding = _binding(binding)
        path = "/v4/spreadsheets/" + binding["spreadsheet_id"]
        result = self.http.request_json(
            "GET", path,
            query={"ranges": range_a1, "includeGridData": "true", "fields": FIELDS},
            bearer=self._access())
        payload = _payload(result.payload)
        if payload.get("spreadsheetId") != binding["spreadsheet_id"]:
            raise SheetsAPIError("target_mismatch")
        sheets = payload.get("sheets")
        if not isinstance(sheets, list) or len(sheets) != 1:
            raise SheetsAPIError("target_mismatch")
        sheet = sheets[0]
        properties = sheet.get("properties") if isinstance(sheet, dict) else None
        if (not isinstance(properties, dict)
                or properties.get("sheetId") != binding["sheet_id"]
                or properties.get("title") != binding["title"]):
            raise SheetsAPIError("target_mismatch")
        data = sheet.get("data", [])
        if not isinstance(data, list):
            raise SheetsAPIError("read_failed")
        return data

    @staticmethod
    def _cells(data, row_count, column_count):
        """將稀疏 GridData 還原成固定欄列，保留原始 ExtendedValue 型別。"""

        rows = [[{} for _ in range(column_count)] for _ in range(row_count)]
        for block in data:
            if not isinstance(block, dict):
                raise SheetsAPIError("read_failed")
            start_row, start_column = block.get("startRow", 0), block.get("startColumn", 0)
            row_data = block.get("rowData", [])
            if (type(start_row) is not int or type(start_column) is not int
                    or start_row < 0 or start_column < 0 or not isinstance(row_data, list)):
                raise SheetsAPIError("read_failed")
            for row_offset, row in enumerate(row_data):
                values = row.get("values", []) if isinstance(row, dict) else None
                if not isinstance(values, list):
                    raise SheetsAPIError("read_failed")
                for column_offset, cell in enumerate(values):
                    target_row, target_column = start_row + row_offset, start_column + column_offset
                    if target_row >= row_count or target_column >= column_count:
                        continue
                    if not isinstance(cell, dict):
                        raise SheetsAPIError("read_failed")
                    entered = cell.get("userEnteredValue", {})
                    if not isinstance(entered, dict):
                        raise SheetsAPIError("read_failed")
                    rows[target_row][target_column] = entered
        return rows

    def require_empty(self, binding):
        """確認整個專用分頁沒有任何使用者輸入值。"""

        binding = _binding(binding)
        data = self._get(binding, _a1_title(binding["title"]))
        for block in data:
            if not isinstance(block, dict):
                raise SheetsAPIError("read_failed")
            row_data = block.get("rowData", [])
            if not isinstance(row_data, list):
                raise SheetsAPIError("read_failed")
            for row in row_data:
                if not isinstance(row, dict) or not isinstance(row.get("values", []), list):
                    raise SheetsAPIError("read_failed")
                for cell in row.get("values", []):
                    if not isinstance(cell, dict):
                        raise SheetsAPIError("read_failed")
                    if isinstance(cell, dict) and "userEnteredValue" in cell:
                        raise SheetsAPIError("sheet_not_empty")
        return {"result": "empty", "observed_at": _now()}

    def write_values(self, grant):
        """只接受 queue 的已 claim 六欄 RAW 執行包，寫入一次。"""

        required = {"binding", "valueInputOption", "range", "majorDimension", "values",
                    "transaction_status", "approval_ref"}
        if (not isinstance(grant, dict) or set(grant) != required
                or grant.get("transaction_status") != "claimed"
                or grant.get("valueInputOption") != "RAW"
                or grant.get("majorDimension") != "ROWS"
                or not isinstance(grant.get("approval_ref"), str)
                or not grant["approval_ref"]):
            raise SheetsAPIError("authorization_required")
        binding = _binding(grant["binding"])
        expected_range = f"{_a1_title(binding['title'])}!A1:F{len(grant.get('values', []))}"
        values = grant.get("values")
        if (not isinstance(values, list) or not 1 < len(values) <= 101
                or grant["range"] != expected_range
                or any(not isinstance(row, list) or len(row) != 6
                       or any(not isinstance(value, str) for value in row) for row in values)):
            raise SheetsAPIError("target_mismatch")
        encoded_range = quote(grant["range"], safe="")
        path = ("/v4/spreadsheets/" + binding["spreadsheet_id"]
                + "/values/" + encoded_range)
        result = self.http.request_json(
            "PUT", path, query={"valueInputOption": "RAW"},
            body={"range": grant["range"], "majorDimension": "ROWS", "values": values},
            bearer=self._access(), mutation=True)
        payload = _payload(result.payload, mutation=True)
        if (payload.get("spreadsheetId") != binding["spreadsheet_id"]
                or payload.get("updatedRows") != len(values)
                or payload.get("updatedColumns") != 6
                or payload.get("updatedCells") != len(values) * 6):
            raise SheetsAPIError("remote_result_unknown")
        return {"result": "request_accepted", "updated_rows": len(values),
                "updated_columns": 6, "updated_cells": len(values) * 6}

    def read_snapshot(self, binding, row_count):
        """讀回 A:F 的 userEnteredValue；不取其他分頁或格式化內容。"""

        binding = _binding(binding)
        if type(row_count) is not int or not 1 < row_count <= 101:
            raise SheetsAPIError("target_mismatch")
        range_a1 = f"{_a1_title(binding['title'])}!A1:F{row_count}"
        data = self._get(binding, range_a1)
        return {"binding": binding, "observed_at": _now(),
                "rows": self._cells(data, row_count, 6)}
