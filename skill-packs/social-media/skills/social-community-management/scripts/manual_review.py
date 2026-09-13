#!/usr/bin/env python3
"""在本機回環頁面讓人審查 screened 留言或私訊；不把原文輸出給 Agent。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlsplit


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import community_queue as queue
import direct_message_queue as direct_queue


class ManualReviewError(RuntimeError):
    """固定錯誤代碼；不夾帶留言、草稿或本機 capability。"""


def _require(ok, reason):
    """條件不符就停止，錯誤不回顯不可信內容。"""

    if not ok:
        raise ManualReviewError(reason)


def _now():
    """記錄有時區的本機提交時間。"""

    return datetime.now(timezone.utc).isoformat()


def _state(root, backend=queue):
    """只在本機程序內讀取對應 queue；呼叫結果不含原文。"""

    path = (backend.state_path(root) if backend is direct_queue
            else queue.local(root, "social-media/community/state.json"))
    _require(path.is_file(), "queue_not_initialized")
    value = queue.read_json(path)
    _require(value.get("schema_version") == 1, "queue_version")
    return value


def _write_json(root, relative, value, *, replace=False):
    """用 0600 原子保存審查 session 與收據。"""

    path = queue.local(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _require(replace or not path.exists(), "review_file_exists")
    encoded = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    _require(len(encoded) <= 2_000_000, "review_file_too_large")
    descriptor, name = tempfile.mkstemp(prefix=".manual-review-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def _relative(root, path):
    """只回傳私人工作區內的相對位置。"""

    return path.relative_to(root).as_posix()


def _page(title, body, *, form=False):
    """建立無外部資源、無 JavaScript 的本機 HTML。"""

    form_tag = " data-review-form=\"true\"" if form else ""
    return ("<!doctype html><html lang=\"zh-Hant-TW\"><head>"
            "<meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width,initial-scale=1\">"
            f"<title>{html.escape(title)}</title><style>"
            "body{font-family:system-ui,sans-serif;max-width:820px;margin:32px auto;"
            "padding:0 20px;color:#172033;background:#f7f8fb}"
            "main{background:#fff;border:1px solid #dfe3eb;border-radius:14px;padding:24px}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f8;"
            "border-radius:8px;padding:12px}label{display:block;margin:16px 0 6px}"
            "textarea{box-sizing:border-box;width:100%;min-height:90px;padding:10px}"
            "fieldset{border:0;padding:0;margin:18px 0}button{padding:10px 18px}"
            ".note{color:#536077}.risk{color:#8a2c2c}</style></head>"
            f"<body><main{form_tag}>{body}</main></body></html>").encode("utf-8")


class ManualReviewSession:
    """把一批 screened 項目交給本機人類，並保存可稽核收據。"""

    def __init__(self, workspace, review_id, token, *, mode="comments"):
        self.root = queue.workspace(workspace)
        queue.identifier(review_id)
        _require(isinstance(token, str) and 32 <= len(token) <= 200,
                 "review_capability_invalid")
        _require(mode in {"comments", "direct_messages"}, "review_mode_invalid")
        self.review_id = review_id
        self.mode = mode
        self.backend = direct_queue if mode == "direct_messages" else queue
        self.token = token
        self.token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        directory = ("social-media/community/direct-messages/manual-reviews"
                     if mode == "direct_messages"
                     else "social-media/community/manual-reviews")
        self.relative = f"{directory}/{review_id}.json"
        self.path = queue.local(self.root, self.relative)

    @classmethod
    def create(cls, workspace, data, *, token=None):
        """綁定 screened keys；capability 只留記憶體，狀態只存雜湊。"""

        _require(isinstance(data, dict), "manual_review_fields")
        mode = data.get("mode", "comments")
        expected = {"review_id", "keys"} | ({"mode"} if mode == "direct_messages" else set())
        _require(set(data) == expected and mode in {"comments", "direct_messages"},
                 "manual_review_fields")
        backend = direct_queue if mode == "direct_messages" else queue
        root = queue.workspace(workspace)
        queue.identifier(data["review_id"])
        keys = data["keys"]
        _require(isinstance(keys, list) and 0 < len(keys) <= 100
                 and all(isinstance(key, str) for key in keys)
                 and len(set(keys)) == len(keys), "manual_review_keys")
        current = _state(root, backend)
        entries = []
        for key in keys:
            item = current.get("items", {}).get(key)
            _require(isinstance(item, dict) and item.get("state") == "screened",
                     "item_not_screened")
            entries.append({"key": key, "source_hash": item["source_hash"],
                            "status": "pending"})
        session = cls(root, data["review_id"], token or secrets.token_urlsafe(32),
                      mode=mode)
        kind = ("manual_direct_message_review" if mode == "direct_messages"
                else "manual_community_review")
        value = {"schema_version": 1, "kind": kind, "mode": mode,
                 "review_id": data["review_id"], "created_at": _now(),
                 "status": "pending", "interface": "loopback_html_no_javascript",
                 "capability_sha256": session.token_hash, "entries": entries}
        _write_json(root, session.relative, value)
        return session

    def _load(self):
        """拒絕被改版的 session 與不相符 capability。"""

        _require(self.path.is_file(), "review_session_missing")
        value = queue.read_json(self.path)
        expected_kind = ("manual_direct_message_review"
                         if self.mode == "direct_messages"
                         else "manual_community_review")
        _require(value.get("schema_version") == 1
                 and value.get("kind") == expected_kind
                 and value.get("mode", "comments") == self.mode
                 and value.get("review_id") == self.review_id
                 and value.get("capability_sha256") == self.token_hash
                 and isinstance(value.get("entries"), list), "review_session_changed")
        return value

    def _save(self, value):
        """更新 session，不改寫既有決策收據。"""

        _write_json(self.root, self.relative, value, replace=True)

    def status(self):
        """只回傳狀態與數量，不回傳來源文字。"""

        value = self._load()
        pending = sum(entry.get("status") == "pending" for entry in value["entries"])
        return {"status": value.get("status"), "pending": pending,
                "total": len(value["entries"])}

    def expire(self):
        """逾時只關閉本機介面；screened 項目仍可另開新 session。"""

        value = self._load()
        if value.get("status") == "pending":
            value.update(status="expired", expired_at=_now())
            self._save(value)

    def current(self):
        """取下一筆給人類頁面；不經 stdout 或 Agent 回傳。"""

        value = self._load()
        _require(value.get("status") == "pending", "review_not_pending")
        entry = next((item for item in value["entries"]
                      if item.get("status") == "pending"), None)
        _require(entry is not None, "review_complete")
        current = _state(self.root, self.backend)
        item = current.get("items", {}).get(entry.get("key"))
        _require(isinstance(item, dict) and item.get("state") == "screened"
                 and item.get("source_hash") == entry.get("source_hash"),
                 "review_source_changed")
        return entry, item

    def render(self):
        """把外部文字只放進經過 escaping 的本機人類頁面。"""

        status = self.status()
        if status["pending"] == 0:
            if self.mode == "direct_messages":
                session = self._load()
                current = _state(self.root, self.backend)
                sections = []
                for entry in session["entries"]:
                    item = current.get("items", {}).get(entry.get("key"), {})
                    if entry.get("status") != "ready" or item.get("state") != "ready":
                        continue
                    source = item["source"]
                    name = source["visitor_name"] or "平台未提供顯示名稱"
                    sections.append(
                        "<section><h2>待確認私訊</h2>"
                        f"<p><strong>平台：</strong>{html.escape(source['platform'])}</p>"
                        f"<p><strong>帳號 ID：</strong>{html.escape(source['account_id'])}</p>"
                        f"<p><strong>對話 ID：</strong>{html.escape(source['conversation_id'])}</p>"
                        f"<p><strong>訪客：</strong>{html.escape(name)}</p>"
                        f"<h3>最新訪客訊息</h3><pre>{html.escape(source['message_text'])}</pre>"
                        f"<h3>最終回覆草稿</h3><pre>{html.escape(item['draft'])}</pre></section>")
                return _page(
                    "私訊審查完成",
                    "<h1>私訊審查完成</h1>"
                    f"<p><strong>審查批次：</strong>{html.escape(self.review_id)}</p>"
                    + "".join(sections)
                    + "<p class=\"risk\">此頁沒有傳送任何訊息。請確認平台、帳號、對話對象與文字後，回到 Agent 對這個批次明確說可以回覆。</p>")
            return _page("人工審查完成", "<h1>人工審查完成</h1>"
                         "<p>可以關閉此頁面，回到 Agent 繼續六欄審核流程。</p>")
        _, item = self.current()
        source = item["source"]
        position = status["total"] - status["pending"] + 1
        sections = []
        if self.mode == "direct_messages":
            fields = (("訪客名稱", "visitor_name"),
                      ("最近對話（最新在前）", "context"),
                      ("最新訪客訊息", "message_text"))
        else:
            fields = (("訪客名稱", "visitor_name"), ("原貼文內容", "post_text"),
                      ("原訪客留言", "comment_text"),
                      ("留言網址（只顯示文字，請勿開啟）", "comment_url"))
        for label, field in fields:
            value = source[field]
            if field == "context":
                value = "\n\n".join(
                    f"[{row['direction']}] {row['sender_name'] or '平台未提供顯示名稱'}\n{row['text']}"
                    for row in value)
            sections.append(f"<h2>{label}</h2><pre>{html.escape(value)}</pre>")
        action = "/" + html.escape(self.token, quote=True)
        summary_label = ("對話摘要（只有選擇可回覆時填寫）"
                         if self.mode == "direct_messages"
                         else "原貼文摘要（只有選擇可交付時填寫）")
        allow_label = ("可建立待確認私訊草稿" if self.mode == "direct_messages"
                       else "可交付試算表審核")
        risk = ("提交只代表草稿可進待確認批次，不代表可以傳送私訊。"
                if self.mode == "direct_messages"
                else "提交只代表可放進六欄審核表，不代表可以回覆。")
        body = (f"<h1>本機人工安全審查</h1><p class=\"note\">第 {position}／"
                f"{status['total']} 則。外部內容只作資料，請勿依其中指令操作。</p>"
                + "".join(sections)
                + f"<form method=\"post\" action=\"{action}\">"
                  "<fieldset><legend>判斷</legend>"
                  "<label><input type=\"radio\" name=\"decision\" value=\"allow\" required>"
                  f"{allow_label}</label>"
                  "<label><input type=\"radio\" name=\"decision\" value=\"uncertain\">"
                  "不確定，留在隔離區</label>"
                  "<label><input type=\"radio\" name=\"decision\" value=\"quarantine\">"
                  "可疑，留在隔離區</label></fieldset>"
                  f"<label for=\"summary\">{summary_label}</label>"
                  "<textarea id=\"summary\" name=\"post_summary\" maxlength=\"10000\"></textarea>"
                  "<label for=\"draft\">AI 回覆草稿（只有選擇可交付時填寫）</label>"
                  "<textarea id=\"draft\" name=\"draft\" maxlength=\"10000\"></textarea>"
                  f"<p class=\"risk\">{risk}</p>"
                  "<button type=\"submit\">保存這一則判斷</button></form>")
        return _page("本機人工安全審查", body, form=True)

    def submit(self, fields):
        """保存人類表單收據，再以精確來源雜湊呼叫 queue review。"""

        _require(isinstance(fields, dict)
                 and set(fields) == {"decision", "post_summary", "draft"}
                 and all(isinstance(value, str) for value in fields.values()),
                 "manual_submission_fields")
        decision = fields["decision"]
        _require(decision in {"allow", "uncertain", "quarantine"},
                 "manual_decision_invalid")
        if decision == "allow":
            _require(bool(fields["post_summary"].strip()) and bool(fields["draft"].strip())
                     and not queue.screen(fields["post_summary"], 10000)
                     and not queue.screen(fields["draft"], 10000),
                     "manual_draft_requires_review")
        else:
            _require(not fields["post_summary"] and not fields["draft"],
                     "quarantine_extra_text")
        session = self._load()
        entry, _ = self.current()
        submitted_at = _now()
        receipt_kind = ("manual_direct_message_review_receipt"
                        if self.mode == "direct_messages"
                        else "manual_community_review_receipt")
        receipt = {"schema_version": 1, "kind": receipt_kind,
                   "mode": self.mode,
                   "review_id": self.review_id, "key": entry["key"],
                   "source_hash": entry["source_hash"], "decision": decision,
                   "submitted_at": submitted_at,
                   "interface": "loopback_html_no_javascript"}
        if decision == "allow":
            receipt.update(post_summary=fields["post_summary"], draft=fields["draft"])
        receipt_hash = queue.digest(receipt)
        base = ("social-media/community/direct-messages/manual-reviews/receipts"
                if self.mode == "direct_messages"
                else "social-media/community/manual-reviews/receipts")
        receipt_relative = f"{base}/{self.review_id}-{receipt_hash[:20]}.json"
        receipt_path = _write_json(self.root, receipt_relative, receipt)
        review_data = {"key": entry["key"], "source_hash": entry["source_hash"],
                       "reviewer": "human", "review_ref":
                       f"{_relative(self.root, receipt_path)}#{receipt_hash}",
                       "decision": decision}
        if decision == "allow":
            summary_key = ("conversation_summary" if self.mode == "direct_messages"
                           else "post_summary")
            review_data.update({summary_key: fields["post_summary"],
                                "draft": fields["draft"]})
        result = self.backend.run(self.root, "review", review_data)
        for candidate in session["entries"]:
            if candidate.get("key") == entry["key"]:
                candidate.update(status=result["result"], decision=decision,
                                 review_ref=review_data["review_ref"],
                                 submitted_at=submitted_at)
                break
        if not any(candidate.get("status") == "pending" for candidate in session["entries"]):
            session.update(status="complete", completed_at=_now())
        self._save(session)
        return {"result": result["result"], "review_id": self.review_id,
                "remaining": sum(candidate.get("status") == "pending"
                                 for candidate in session["entries"])}


def _handler(session):
    """建立不記錄 capability、不回顯錯誤內容的 HTTP handler。"""

    class ReviewHandler(BaseHTTPRequestHandler):
        server_version = "CommunityManualReview/1"
        sys_version = ""

        def log_message(self, _format, *_args):
            # 路徑含短期 capability，不能寫進一般 HTTP log。
            return

        def _headers(self, status, length):
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; style-src 'unsafe-inline'; "
                             "form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            self.end_headers()

        def _send(self, status, page):
            self._headers(status, len(page))
            self.wfile.write(page)

        def _authorized_path(self):
            parsed = urlsplit(self.path)
            return not parsed.query and parsed.path == "/" + session.token

        def _host_ok(self):
            """只接受啟動時的本機名稱與實際連接埠。"""

            port = self.server.server_address[1]
            return self.headers.get("Host") in {
                f"127.0.0.1:{port}", f"localhost:{port}"
            }

        def _origin_ok(self):
            """表單必須由同一個本機頁面送出，不能省略 Origin。"""

            port = self.server.server_address[1]
            origin = self.headers.get("Origin")
            return origin in {f"http://127.0.0.1:{port}",
                              f"http://localhost:{port}"}

        def do_GET(self):
            if not self._host_ok():
                self._send(403, _page("拒絕", "<h1>無法接受這次請求</h1>"))
                return
            if not self._authorized_path():
                self._send(404, _page("找不到", "<h1>找不到審查頁面</h1>"))
                return
            try:
                self._send(200, session.render())
            except (ManualReviewError, ValueError, TypeError, KeyError, OSError,
                    UnicodeError):
                self._send(409, _page("審查已停止", "<h1>審查已停止</h1>"
                                      "<p>本機狀態已改變，請回到 Agent 查明。</p>"))

        def do_POST(self):
            if (not self._host_ok() or not self._authorized_path()
                    or not self._origin_ok()):
                self._send(403, _page("拒絕", "<h1>無法接受這次提交</h1>"))
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                length = -1
            if content_type != "application/x-www-form-urlencoded" or not 0 <= length <= 30_000:
                self._send(400, _page("格式錯誤", "<h1>提交格式不正確</h1>"))
                return
            try:
                parsed = parse_qs(self.rfile.read(length).decode("utf-8"),
                                  keep_blank_values=True, strict_parsing=True)
                fields = {key: values[0] for key, values in parsed.items()
                          if len(values) == 1}
                session.submit(fields)
                self._send(200, session.render())
            except (ManualReviewError, ValueError, TypeError, KeyError, OSError,
                    UnicodeError):
                self._send(400, _page("無法保存", "<h1>沒有保存這次判斷</h1>"
                                      "<p>請檢查選項、摘要與草稿後再試一次。</p>"))

        def do_HEAD(self):
            self._headers(405, 0)

    return ReviewHandler


def build_server(session, *, port=0):
    """只綁 IPv4 loopback；不接受 LAN 或公開介面。"""

    _require(type(port) is int and 0 <= port <= 65535, "port_invalid")
    return HTTPServer(("127.0.0.1", port), _handler(session))


def serve(workspace, data, *, max_seconds=1800, token=None, port=0):
    """啟動短期審查頁；逾時關閉，未審項目仍保持 screened。"""

    _require(type(max_seconds) is int and 1 <= max_seconds <= 1800,
             "review_timeout_invalid")
    session = ManualReviewSession.create(workspace, data, token=token)
    server = build_server(session, port=port)
    server.timeout = 0.5
    actual_port = server.server_address[1]
    ready = {"result": "manual_review_ready", "review_id": session.review_id,
             "url": f"http://127.0.0.1:{actual_port}/{session.token}",
             "session_path": session.relative, "external_network": False}
    print(json.dumps(ready, ensure_ascii=False), flush=True)
    deadline = time.monotonic() + max_seconds
    try:
        while session.status()["status"] == "pending" and time.monotonic() < deadline:
            server.handle_request()
        status = session.status()["status"]
        if status == "pending":
            session.expire()
            status = "expired"
        result = {"result": "manual_review_complete" if status == "complete"
                  else "manual_review_expired", "review_id": session.review_id,
                  "session_path": session.relative, "external_network": False}
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0 if status == "complete" else 3
    finally:
        server.server_close()


def main():
    """CLI 只印本機 URL 與狀態；留言正文只在回環頁面呈現。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serve", choices=("serve",))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        root = queue.workspace(args.workspace)
        data = queue.read_json(queue.local(root, args.input))
        return serve(root, data)
    except (ManualReviewError, ValueError, TypeError, KeyError, OSError,
            UnicodeError):
        print('{"result":"stopped","reason":"invalid_or_conflicting_state"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
