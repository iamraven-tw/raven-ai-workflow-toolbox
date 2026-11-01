"""測試替身：只提供 ingest.py／query.py 用到的 requests.post，以標準函式庫送出 JSON。"""

import json as _json
import urllib.error
import urllib.request


class HTTPError(Exception):
    """對應 requests.HTTPError。"""


class _Response:
    def __init__(self, status: int, body: bytes) -> None:
        self.status_code, self._body = status, body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return _json.loads(self._body)


def post(url, json=None, timeout=None):
    """送出 JSON POST；連線失敗時讓 urllib 的例外往上丟，模擬 Ollama 沒有在執行。"""

    if not url.startswith(("http://", "https://")):
        raise ValueError(f"No connection adapters were found for {url!r}")
    request = urllib.request.Request(
        url, data=_json.dumps(json).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _Response(response.status, response.read())
    except urllib.error.HTTPError as error:
        return _Response(error.code, error.read())
