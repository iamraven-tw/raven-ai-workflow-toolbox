#!/usr/bin/env python3
"""四平台成效的受限官方唯讀 adapter；不寫報告、不保存 Token。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import http.client
import importlib
import json
import math
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urlencode, urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import metric_catalog


class PerformanceAPIError(RuntimeError):
    """固定錯誤代碼，不讓 Token 或平台回應文字進一般輸出。"""

    ALLOWED = {
        "authorization_required", "invalid_request", "adapter_unavailable",
        "reauth_required", "permission_denied", "target_mismatch",
        "rate_limited", "invalid_metric", "read_failed",
        "unsupported_response", "pagination_incomplete",
    }

    def __init__(self, kind):
        self.kind = kind if kind in self.ALLOWED else "read_failed"
        super().__init__(self.kind)


class HTTPResult:
    """在可信程序記憶體中保存一次官方 JSON 回應。"""

    __slots__ = ("status", "payload", "headers")

    def __init__(self, status, payload, headers=None):
        self.status = status
        self.payload = payload
        self.headers = {str(key).lower(): str(value)
                        for key, value in (headers or {}).items()}


def _identifier(value):
    """限制平台資源 ID，拒絕路徑與查詢注入。"""

    if type(value) not in {str, int}:
        raise PerformanceAPIError("invalid_request")
    value = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,500}", value):
        raise PerformanceAPIError("invalid_request")
    return value


def _metric(value):
    """第一版一次只查一個官方 metric，避免錯誤組合難以判讀。"""

    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,100}", value):
        raise PerformanceAPIError("invalid_request")
    return value


def _number(value):
    """只接受有限數值；布林值不是成效數字。"""

    if type(value) not in {int, float} or not math.isfinite(value):
        raise PerformanceAPIError("unsupported_response")
    return value


def _window(value):
    """驗證不含尾日的完整曆期，單次最多 366 天。"""

    if not isinstance(value, dict) or set(value) != {"start", "end"}:
        raise PerformanceAPIError("invalid_request")
    try:
        start, end = date.fromisoformat(value["start"]), date.fromisoformat(value["end"])
    except (TypeError, ValueError):
        raise PerformanceAPIError("invalid_request") from None
    if not start < end or (end - start).days > 366:
        raise PerformanceAPIError("invalid_request")
    return start, end


def _payload(value):
    """唯讀空 body 或非物件回應不能當成零。"""

    if not isinstance(value, dict):
        raise PerformanceAPIError("read_failed")
    return value


def _classify(status, value):
    """把外部錯誤收斂為資料契約可分辨的狀態。"""

    error = value.get("error") if isinstance(value, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    if status == 401 or code in {102, 190}:
        raise PerformanceAPIError("reauth_required")
    if status == 429 or code in {4, 17, 32, 613}:
        raise PerformanceAPIError("rate_limited")
    if status == 403 or code in {10, 200}:
        raise PerformanceAPIError("permission_denied")
    if status == 400 or code == 100:
        raise PerformanceAPIError("invalid_metric")
    if not 200 <= status < 300 or error:
        raise PerformanceAPIError("read_failed")


class OfficialPerformanceHTTP:
    """只允許四個官方主機的固定唯讀 insights／reports 端點。"""

    MAX_RESPONSE = 4 * 1024 * 1024

    @staticmethod
    def _allowed(endpoint):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != "https" or parsed.query or parsed.fragment
                or parsed.username or parsed.password):
            return False
        identifier = r"[A-Za-z0-9_.-]{1,500}"
        version = r"v[0-9]+\.0"
        if parsed.netloc == "youtubeanalytics.googleapis.com":
            return parsed.path == "/v2/reports"
        if parsed.netloc in {"graph.facebook.com", "graph.instagram.com"}:
            return bool(re.fullmatch(rf"/{version}/{identifier}/insights", parsed.path))
        if parsed.netloc == "graph.threads.net":
            return bool(re.fullmatch(
                rf"/{version}/(?:{identifier}|me)/threads_insights", parsed.path))
        return False

    @staticmethod
    def _bearer(value):
        """Token 只進 Authorization header。"""

        if (not isinstance(value, str) or not value or len(value) > 32_768
                or "\r" in value or "\n" in value):
            raise PerformanceAPIError("authorization_required")
        return value

    @staticmethod
    def _value(value):
        """查詢參數只接受可預期純量。"""

        if isinstance(value, bool):
            return "true" if value else "false"
        if type(value) in {str, int}:
            return str(value)
        raise PerformanceAPIError("invalid_request")

    def request_json(self, endpoint, *, query, bearer):
        """送出一次 GET，不跟隨重新導向、不把 Token 放進 query。"""

        if (not self._allowed(endpoint) or not isinstance(query, dict)
                or any(str(key).lower() in {"access_token", "token", "authorization"}
                       for key in query)):
            raise PerformanceAPIError("invalid_request")
        parsed = urlsplit(endpoint)
        path = parsed.path
        if query:
            path += "?" + urlencode({key: self._value(value)
                                      for key, value in query.items()})
        connection = http.client.HTTPSConnection(
            parsed.hostname, timeout=60, context=ssl.create_default_context())
        headers = {"Accept": "application/json", "Cache-Control": "no-store",
                   "Authorization": "Bearer " + self._bearer(bearer)}
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            raw = response.read(self.MAX_RESPONSE + 1)
            if len(raw) > self.MAX_RESPONSE:
                raise PerformanceAPIError("read_failed")
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                value = None
            _classify(response.status, value)
            return HTTPResult(response.status, value, dict(response.getheaders()))
        except PerformanceAPIError:
            raise
        except Exception:
            raise PerformanceAPIError("read_failed") from None
        finally:
            connection.close()


def _default_runtime(workspace, platform, connection):
    """由 setup Runtime 取用既有連線；不直接讀秘密庫分段。"""

    scripts = Path(__file__).resolve().parents[2] / "social-media-setup" / "scripts"
    if not scripts.is_dir():
        raise PerformanceAPIError("adapter_unavailable")
    added = str(scripts) not in sys.path
    if added:
        sys.path.insert(0, str(scripts))
    try:
        module = importlib.import_module("oauth_runtime")
        return module.Runtime(workspace, platform, connection=connection)
    except PerformanceAPIError:
        raise
    except Exception:
        raise PerformanceAPIError("adapter_unavailable") from None
    finally:
        if added and sys.path and sys.path[0] == str(scripts):
            sys.path.pop(0)


class OfficialPerformanceAdapter:
    """讀取單一平台、單一指標與單一期間，回傳可稽核觀測。"""

    SCOPE_KEYS = {
        "platform", "account_id", "approval_ref", "confirmed_read",
        "allow_token_refresh",
    }
    QUERY_KEYS = {"metric", "api_period", "metric_type", "filters",
                  "coverage_probe", "show_description_from_api_doc"}

    def __init__(self, workspace, *, connection="main", runtime_factory=None,
                 http_transport=None, clock=None):
        self.workspace = Path(workspace).expanduser().resolve()
        if (not self.workspace.is_dir()
                or not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", connection)):
            raise PerformanceAPIError("invalid_request")
        self.connection = connection
        self.runtime_factory = runtime_factory or _default_runtime
        self.http = http_transport or OfficialPerformanceHTTP()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self):
        """取得可測試且有時區的 UTC 時間。"""

        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise PerformanceAPIError("adapter_unavailable")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _scope(scope):
        """每次讀取都綁平台、帳號與使用者確認。"""

        if not isinstance(scope, dict) or set(scope) != OfficialPerformanceAdapter.SCOPE_KEYS:
            raise PerformanceAPIError("authorization_required")
        if (scope.get("platform") not in {"youtube", "facebook", "instagram", "threads"}
                or scope.get("confirmed_read") is not True
                or scope.get("allow_token_refresh") not in {True, False}
                or not isinstance(scope.get("approval_ref"), str)
                or not scope["approval_ref"].strip()
                or len(scope["approval_ref"]) > 300):
            raise PerformanceAPIError("authorization_required")
        _identifier(scope["account_id"])
        return scope

    @staticmethod
    def _query(platform, query):
        """平台差異只允許文件化的少量查詢參數。"""

        if not isinstance(query, dict) or not set(query).issubset(
                OfficialPerformanceAdapter.QUERY_KEYS):
            raise PerformanceAPIError("invalid_request")
        metric = _metric(query.get("metric"))
        api_period = query.get("api_period")
        metric_type = query.get("metric_type")
        filters = query.get("filters", "")
        probe = query.get("coverage_probe", False)
        show_description = query.get("show_description_from_api_doc", False)
        if not isinstance(filters, str) or len(filters) > 1000 or any(
                ord(char) < 32 for char in filters):
            raise PerformanceAPIError("invalid_request")
        if probe not in {True, False} or show_description not in {True, False}:
            raise PerformanceAPIError("invalid_request")
        if platform == "youtube":
            if (api_period is not None or metric_type is not None or not probe
                    or show_description):
                raise PerformanceAPIError("invalid_request")
        elif platform == "facebook":
            if api_period not in {"day", "week", "days_28", "month"} \
                    or metric_type is not None or filters or probe \
                    or not show_description:
                raise PerformanceAPIError("invalid_request")
        elif platform == "instagram":
            if api_period not in {"day", "week", "days_28", "month", "lifetime",
                                  "total_over_range"} \
                    or metric_type not in {None, "time_series", "total_value"} \
                    or filters or probe or show_description:
                raise PerformanceAPIError("invalid_request")
        else:
            if any(value not in {None, "", False}
                   for value in (api_period, metric_type, filters, probe,
                                 show_description)):
                raise PerformanceAPIError("invalid_request")
        return {"metric": metric, "api_period": api_period,
                "metric_type": metric_type, "filters": filters,
                "coverage_probe": probe,
                "show_description_from_api_doc": show_description}

    def _context(self, scope):
        """核對 setup 目標、登入路徑及最小成效 permission。"""

        scope = self._scope(scope)
        try:
            runtime = self.runtime_factory(
                self.workspace, scope["platform"], self.connection)
            config = runtime.config()
            if str(config.get("target_id")) != scope["account_id"]:
                raise PerformanceAPIError("target_mismatch")
            route = config.get("login_route")
            scopes = set(config.get("scopes", []))
            required = {
                "youtube_desktop": {
                    "https://www.googleapis.com/auth/youtube.readonly",
                    "https://www.googleapis.com/auth/yt-analytics.readonly",
                },
                "facebook_pages": {"pages_read_engagement", "read_insights"},
                "instagram_login": {"instagram_business_basic",
                                     "instagram_business_manage_insights"},
                "instagram_facebook_login": {"instagram_basic",
                                             "instagram_manage_insights",
                                             "pages_read_engagement"},
                "threads_login": {"threads_basic", "threads_manage_insights"},
            }.get(route)
            if required is None or not required.issubset(scopes):
                raise PerformanceAPIError("permission_denied")
            token = runtime.access(
                confirmed_read=True,
                allow_refresh=scope["allow_token_refresh"])
            details = runtime.resource_context(confirmed_read=True)
            if (details.get("target_id") != scope["account_id"]
                    or details.get("login_route") != route):
                raise PerformanceAPIError("target_mismatch")
            if not isinstance(token, str) or not token:
                raise PerformanceAPIError("reauth_required")
            version = config.get("graph_version")
            if scope["platform"] == "youtube":
                base = "https://youtubeanalytics.googleapis.com/v2"
                version = "v2"
            else:
                if not isinstance(version, str) or not re.fullmatch(r"v[0-9]+\.0", version):
                    raise PerformanceAPIError("adapter_unavailable")
                host = {
                    "facebook": "graph.facebook.com",
                    "threads": "graph.threads.net",
                    "instagram": ("graph.instagram.com" if route == "instagram_login"
                                  else "graph.facebook.com"),
                }[scope["platform"]]
                base = f"https://{host}/{version}"
            return scope, {"route": route, "token": token, "base": base,
                           "version": version, "account_id": scope["account_id"]}
        except PerformanceAPIError:
            raise
        except Exception as error:
            mapping = {
                "authorization_required": "authorization_required",
                "reauth_required": "reauth_required", "refresh_required": "reauth_required",
                "permission_mismatch": "permission_denied",
                "target_mismatch": "target_mismatch", "rate_limited": "rate_limited",
            }
            raise PerformanceAPIError(
                mapping.get(getattr(error, "kind", None), "adapter_unavailable")) from None

    def verify_access(self, scope):
        """只回傳非敏感的連線摘要。"""

        scope, context = self._context(scope)
        return {"platform": scope["platform"], "account_id": scope["account_id"],
                "login_route": context["route"], "ready": True}

    @staticmethod
    def _redact(value, secret, depth=0):
        """保存證據前移除 Token／Cookie；不改動平台數值與欄位定義。"""

        if depth > 40:
            raise PerformanceAPIError("unsupported_response")
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise PerformanceAPIError("unsupported_response")
                lowered = key.lower()
                if any(term in lowered for term in (
                        "access_token", "authorization", "cookie", "client_secret")):
                    result[key] = "[REDACTED]"
                else:
                    result[key] = OfficialPerformanceAdapter._redact(
                        item, secret, depth + 1)
            return result
        if isinstance(value, list):
            return [OfficialPerformanceAdapter._redact(item, secret, depth + 1)
                    for item in value]
        if isinstance(value, str):
            return value.replace(secret, "[REDACTED]")
        if value is None or type(value) in {bool, int, float}:
            return value
        raise PerformanceAPIError("unsupported_response")

    @staticmethod
    def _youtube_value(payload, metric, *, daily=False):
        """核對 resultTable 欄位及有限數值。"""

        payload = _payload(payload)
        if payload.get("kind") != "youtubeAnalytics#resultTable":
            raise PerformanceAPIError("unsupported_response")
        headers = payload.get("columnHeaders")
        expected = (["day", metric] if daily else [metric])
        if (not isinstance(headers, list)
                or [header.get("name") for header in headers
                    if isinstance(header, dict)] != expected):
            raise PerformanceAPIError("unsupported_response")
        rows = payload.get("rows")
        if rows is None:
            return [] if daily else None
        if not isinstance(rows, list):
            raise PerformanceAPIError("unsupported_response")
        if daily:
            values = []
            for row in rows:
                if not isinstance(row, list) or len(row) != 2:
                    raise PerformanceAPIError("unsupported_response")
                try:
                    day = date.fromisoformat(row[0])
                except (TypeError, ValueError):
                    raise PerformanceAPIError("unsupported_response") from None
                values.append((day, _number(row[1])))
            return values
        if len(rows) != 1 or not isinstance(rows[0], list) or len(rows[0]) != 1:
            raise PerformanceAPIError("unsupported_response")
        return _number(rows[0][0])

    def _youtube(self, context, query, start, end):
        """用聚合值加 day probe，避免把最新資料延遲當完整期間。"""

        end_inclusive = end - timedelta(days=1)
        common = {"ids": "channel==MINE", "startDate": start.isoformat(),
                  "endDate": end_inclusive.isoformat(), "metrics": query["metric"]}
        if query["filters"]:
            common["filters"] = query["filters"]
        aggregate = _payload(self.http.request_json(
            context["base"] + "/reports", query=common,
            bearer=context["token"]).payload)
        value = self._youtube_value(aggregate, query["metric"])
        if value is None:
            return {"status": "unavailable", "value": None, "coverage": "unknown",
                    "response_definition": "", "raw": {"aggregate": aggregate}}
        probe_query = dict(common, dimensions="day", sort="day",
                           maxResults=(end - start).days + 1)
        probe = _payload(self.http.request_json(
            context["base"] + "/reports", query=probe_query,
            bearer=context["token"]).payload)
        daily = self._youtube_value(probe, query["metric"], daily=True)
        expected = [start + timedelta(days=offset)
                    for offset in range((end - start).days)]
        actual = [day for day, _ in daily]
        if len(actual) != len(set(actual)) or any(day < start or day >= end for day in actual):
            raise PerformanceAPIError("unsupported_response")
        coverage = "complete" if actual == expected else ("partial" if actual else "unknown")
        return {"status": "available", "value": value, "coverage": coverage,
                "response_definition": "YouTube Analytics API v2 resultTable",
                "raw": {"aggregate": aggregate, "coverage_probe": probe}}

    @staticmethod
    def _meta_value(payload, metric, aggregation, expected_period, *,
                    require_api_description=False):
        """讀取單一 Meta insight；不能安全加總 unique／rate／average。"""

        payload = _payload(payload)
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise PerformanceAPIError("unsupported_response")
        if not rows:
            return {"status": "unavailable", "value": None,
                    "response_definition": "", "response_period": ""}
        matches = [row for row in rows
                   if isinstance(row, dict) and row.get("name") == metric]
        if len(matches) != 1:
            raise PerformanceAPIError("unsupported_response")
        row = matches[0]
        period = row.get("period")
        if period != expected_period:
            raise PerformanceAPIError("invalid_metric")
        description = (row.get("description_from_api_doc")
                       if require_api_description else row.get("description"))
        if not description and not require_api_description:
            description = row.get("description_from_api_doc")
        if (not isinstance(description, str) or not description.strip()
                or len(description) > 10_000):
            raise PerformanceAPIError("invalid_metric")
        total = row.get("total_value")
        if isinstance(total, dict) and "value" in total:
            value = _number(total["value"])
        else:
            values = row.get("values")
            if not isinstance(values, list) or not values:
                return {"status": "unavailable", "value": None,
                        "response_definition": description,
                        "response_period": period}
            numbers = []
            for point in values:
                if not isinstance(point, dict) or "value" not in point:
                    raise PerformanceAPIError("unsupported_response")
                numbers.append(_number(point["value"]))
            if len(numbers) == 1:
                value = numbers[0]
            elif aggregation == "total":
                value = sum(numbers)
                _number(value)
            elif aggregation == "snapshot":
                value = numbers[-1]
            else:
                raise PerformanceAPIError("unsupported_response")
        return {"status": "available", "value": value,
                "response_definition": description.strip(),
                "response_period": period}

    def fetch(self, scope, query, window, *, aggregation):
        """取得一個觀測；回應正文由上層立即保存為私人證據。"""

        scope, context = self._context(scope)
        query = self._query(scope["platform"], query)
        start, end = _window(window)
        if aggregation not in {"total", "unique", "snapshot", "average", "rate"}:
            raise PerformanceAPIError("invalid_request")
        try:
            metric_catalog.validate_adapter_query(
                scope["platform"], query, aggregation)
        except metric_catalog.MetricCatalogError:
            raise PerformanceAPIError("invalid_metric") from None
        if scope["platform"] == "youtube":
            result = self._youtube(context, query, start, end)
        else:
            endpoint = (f"{context['base']}/{context['account_id']}/threads_insights"
                        if scope["platform"] == "threads"
                        else f"{context['base']}/{context['account_id']}/insights")
            params = {"metric": query["metric"]}
            if scope["platform"] in {"facebook", "instagram"}:
                params.update(period=query["api_period"], since=start.isoformat(),
                              until=end.isoformat())
            if query["show_description_from_api_doc"]:
                params["show_description_from_api_doc"] = True
            if query["metric_type"]:
                params["metric_type"] = query["metric_type"]
            payload = _payload(self.http.request_json(
                endpoint, query=params, bearer=context["token"]).payload)
            expected_period = (query["api_period"] if scope["platform"] != "threads"
                               else metric_catalog.load_catalog()["platforms"]
                               ["threads"]["required_period"])
            result = self._meta_value(
                payload, query["metric"], aggregation, expected_period,
                require_api_description=(scope["platform"] == "facebook"))
            result.update(coverage="unknown", raw=payload)
        result["raw"] = self._redact(result["raw"], context["token"])
        return {
            "platform": scope["platform"], "account_id": scope["account_id"],
            "interface": "official_api", "login_route": context["route"],
            "api_version": context["version"], "metric": query["metric"],
            "requested_period": window, "observed_at": self._now().isoformat(),
            **result,
        }
