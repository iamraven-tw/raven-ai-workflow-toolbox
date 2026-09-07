"""自有 YouTube 內容唯讀取樣；與成效 adapter 共用 OAuth Runtime。"""

import http.client
import json
import ssl
from urllib.parse import urlencode

from oauth_runtime import Runtime
from oauth_http import OAuthError, classify_response


class ContentHTTP:
    """只允許兩個 Data API GET 端點；不跟隨轉址、不輸出秘密。"""

    def get(self, resource, query, token):
        if resource not in {"channels", "playlistItems"}:
            raise OAuthError("invalid_configuration")
        if not isinstance(token, str) or not token or any(ord(c) < 32 for c in token):
            raise OAuthError("reauth_required")
        connection = http.client.HTTPSConnection(
            "www.googleapis.com", timeout=20, context=ssl.create_default_context())
        try:
            connection.request("GET", "/youtube/v3/" + resource + "?" + urlencode(query),
                               headers={"Authorization": "Bearer " + token,
                                        "Accept": "application/json"})
            response = connection.getresponse()
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise OAuthError("read_failed")
            return classify_response(response.status, json.loads(raw))
        except OAuthError:
            raise
        except Exception:
            raise OAuthError("read_failed") from None
        finally:
            connection.close()


def sample(workspace, target_id, *, connection="main", confirmed_read=False,
           allow_refresh=False, runtime_factory=Runtime, transport=None):
    """固定最多五筆，不聲稱完整歷史；回傳值僅供私人產物。"""
    if confirmed_read is not True:
        raise OAuthError("authorization_required")
    runtime = runtime_factory(workspace, "youtube", connection=connection)
    config = runtime.config()
    if config.get("target_id") != target_id or not isinstance(target_id, str) or not target_id:
        raise OAuthError("target_mismatch")
    if (config.get("login_route") != "youtube_desktop" or
            "https://www.googleapis.com/auth/youtube.readonly" not in config.get("scopes", [])):
        raise OAuthError("permission_mismatch")
    token = runtime.access(confirmed_read=True, allow_refresh=allow_refresh)
    context = runtime.resource_context(confirmed_read=True)
    if context.get("target_id") != target_id or context.get("login_route") != "youtube_desktop":
        raise OAuthError("target_mismatch")
    http = transport or ContentHTTP()
    try:
        payload = http.get("channels", {"part": "id,snippet,contentDetails", "mine": "true"}, token)
        channels = payload.get("items")
        if (not isinstance(channels, list) or len(channels) != 1 or
                channels[0].get("id") != target_id or payload.get("nextPageToken")):
            raise OAuthError("target_mismatch")
        channel = channels[0]
        uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]
        if not isinstance(uploads, str) or not uploads:
            raise OAuthError("read_failed")
        listing = http.get("playlistItems", {"part": "snippet,contentDetails",
                           "playlistId": uploads, "maxResults": 5}, token)
        items = listing.get("items")
        if not isinstance(items, list) or len(items) > 5:
            raise OAuthError("read_failed")
        videos = []
        for item in items:
            snippet, details = item["snippet"], item["contentDetails"]
            if snippet.get("channelId") != target_id:
                raise OAuthError("target_mismatch")
            video_id = details["videoId"]
            title = snippet["title"]
            if not isinstance(video_id, str) or not isinstance(title, str):
                raise OAuthError("read_failed")
            videos.append({"video_id": video_id, "title": title,
                           "description": snippet.get("description", ""),
                           "published_at": details.get("videoPublishedAt")})
        result = {"interface": "youtube_data_api_v3", "sample_only": True,
                  "has_more": bool(listing.get("nextPageToken")),
                  "status": "available" if videos else "empty",
                  "videos": videos}
        # 不允許回應反射秘密進入私人產物或模型內容。
        if token in json.dumps(result, ensure_ascii=False):
            raise OAuthError("read_failed")
        return result
    except OAuthError:
        raise
    except Exception:
        raise OAuthError("read_failed") from None
