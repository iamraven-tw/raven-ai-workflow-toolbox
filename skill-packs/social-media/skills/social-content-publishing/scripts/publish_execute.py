#!/usr/bin/env python3
"""串接已核准發布帳本與正式 adapter；只有 execute-api 會產生外部寫入。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import official_publish_api as official  # noqa: E402
import publish_job as job  # noqa: E402


class ExecutionStopped(RuntimeError):
    """代表已安全落地狀態，呼叫端不得再送出同一寫入。"""

    def __init__(self, result):
        self.result = result
        super().__init__(result.get("result", "blocked"))


def _operation(context, stage):
    """找出單一階段的既有一次性操作。"""

    matches = [item for item in context["attempt"].get("operations", [])
               if item.get("stage") == stage]
    if len(matches) > 1:
        raise ValueError("ledger_invalid")
    return matches[0] if matches else None


def _timestamp_seconds(value):
    """將已由 plan 驗證的時間轉成平台使用的整數秒。"""

    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def _iso_time(value):
    """將平台可能回傳的 epoch 秒正規化為含時區 ISO；未知格式原樣交驗證。"""

    if type(value) in (int, float):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return value


class PublishExecutor:
    """每次只處理一個平台項目，未知結果立即停止整串工作。"""

    API_PLATFORMS = {"youtube", "facebook", "instagram", "threads"}

    def __init__(self, workspace, plan, *, connection="main", adapter=None,
                 allow_token_refresh=True):
        self.root = job.workspace_path(workspace)
        self.plan = plan
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", connection):
            raise ValueError("connection_invalid")
        if type(allow_token_refresh) is not bool:
            raise ValueError("refresh_policy_invalid")
        self.connection = connection
        self.allow_token_refresh = allow_token_refresh
        self.adapter = adapter or official.OfficialAPIAdapter(
            self.root, connection=connection,
        )

    def context(self, item_id, *, executable=True):
        """每次從最新帳本重建 grant，避免沿用過期記憶體狀態。"""

        return job.attempt_context(
            self.root, self.plan, item_id,
            require_executable=executable,
            allow_token_refresh=self.allow_token_refresh,
        )

    def _claim(self, item_id, stage):
        """任何非冪等遠端動作之前先原子宣告一次。"""

        return job.transaction(
            self.root, self.plan, "claim", item_id=item_id, stage=stage,
        )

    def _checkpoint(self, item_id, stage, *, remote_id=None, outcome="remote-id-saved"):
        """只保存安全 ID；具授權性的 session 不得進帳本。"""

        return job.transaction(
            self.root, self.plan, "checkpoint", item_id=item_id, stage=stage,
            remote_id=remote_id, checkpoint_outcome=outcome,
        )

    def _save_record(self, item, *, state, source, reason, platform_id=None,
                     url=None, platform_time=None, content_matches=False,
                     media_matches=False, settings_readback=None, selected=None,
                     observed_at=None):
        """只保存已挑選、去敏感的證據與 receipt，絕不保存原始回應。"""

        observed_at = observed_at or job.now()
        evidence = {
            "schema_version": 1,
            "source": source,
            "item_id": item["id"],
            "platform": item["platform"],
            "reason": reason,
            "observed_at": observed_at,
            "selected": selected or {},
        }
        job.secrets(evidence)
        token = job.digest(evidence)[:16]
        plan = job.preview(self.root, self.plan)["plan"]
        folder_relative = f'social-media/publishing/{plan["job_id"]}'
        evidence_dir = job.local(self.root, folder_relative + "/evidence",
                                 must_exist=False)
        receipt_dir = job.local(self.root, folder_relative + "/receipts",
                                must_exist=False)
        evidence_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        receipt_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        evidence_path = evidence_dir / f'{item["id"]}-{token}.json'
        job.save(evidence_path, evidence)
        receipt = {
            "item_id": item["id"], "target_id": item["target_id"],
            "state": state, "platform_id": platform_id, "url": url,
            "platform_time": platform_time, "observed_at": observed_at,
            "content_matches": content_matches, "media_matches": media_matches,
            "settings_readback": settings_readback or {},
            "evidence_path": evidence_path.relative_to(self.root).as_posix(),
            "evidence_sha256": job.file_hash(evidence_path),
        }
        receipt_path = receipt_dir / f'{item["id"]}-{token}.json'
        job.save(receipt_path, receipt)
        result = job.transaction(
            self.root, self.plan, "record", item_id=item["id"],
            receipt_path=receipt_path.relative_to(self.root).as_posix(),
        )
        return result | {
            "receipt": receipt_path.relative_to(self.root).as_posix(),
            "external_actions": source == "official_api",
        }

    def _stop_after_mutation(self, item, kind, *, platform_id=None):
        """寫入階段出錯後形成不可重送的終止紀錄。"""

        unknown = kind in {"remote_result_unknown", "read_failed"}
        result = self._save_record(
            item, state="unknown" if unknown else "failed",
            source="official_api", reason=kind, platform_id=platform_id,
            selected={"error_category": kind},
        )
        raise ExecutionStopped(result)

    def _mutate(self, context, stage, callback, *, sensitive=False):
        """已完成階段可重用安全 ID；claimed 未完成則視為結果不明。"""

        item = context["item"]
        operation = _operation(context, stage)
        if operation:
            if operation.get("state") != "completed":
                self._stop_after_mutation(item, "remote_result_unknown")
            if operation.get("outcome") == "remote-id-saved":
                return {"stage": stage, "remote_id": operation.get("remote_id"),
                        "status": "recovered_checkpoint"}
            self._stop_after_mutation(item, "remote_result_unknown")
        self._claim(item["id"], stage)
        try:
            result = callback()
        except official.PublishAPIError as error:
            self._stop_after_mutation(item, error.kind)
        except Exception:
            self._stop_after_mutation(item, "remote_result_unknown")
        if sensitive:
            self._checkpoint(
                item["id"], stage,
                outcome="sensitive-reference-memory-only",
            )
            return result
        if not isinstance(result, dict):
            self._stop_after_mutation(item, "remote_result_unknown")
        remote_id = result.get("remote_id")
        if remote_id is None:
            self._checkpoint(
                item["id"], stage, outcome="pending-without-remote-id",
            )
            stopped = self._save_record(
                item, state="pending", source="official_api",
                reason=str(result.get("stage") or "remote_id_missing"),
                selected={"stage": stage, "status": result.get("status")},
            )
            raise ExecutionStopped(stopped)
        self._checkpoint(item["id"], stage, remote_id=str(remote_id))
        return result

    def execute_api(self, item_id):
        """執行一個已 begin 的 API 項目；不自動開始下一平台。"""

        context = self.context(item_id)
        item, grant = context["item"], context["grant"]
        if item["platform"] not in self.API_PLATFORMS or item["interface"] != "official_api":
            raise ValueError("interface_not_api")
        # 先驗證身分與既有權限，再 claim 發布寫入；此步驟不發布內容。
        self.adapter.verify_access(grant)
        try:
            if item["platform"] == "youtube":
                return self._youtube(context)
            if item["platform"] == "facebook":
                return self._facebook(context)
            if item["platform"] == "instagram":
                return self._instagram(context)
            return self._threads(context)
        except ExecutionStopped as stopped:
            return stopped.result
        except official.PublishAPIError as error:
            # 只有讀取發生在最後一個 checkpoint 之後才進此分支。
            return self._save_record(
                item, state=("unknown" if error.kind in {
                    "remote_result_unknown", "read_failed"
                } else "failed"), source="official_api",
                reason=error.kind, selected={"error_category": error.kind},
            )

    def _youtube(self, context):
        """建立一次上傳 session、送一次檔案，再獨立讀回影片。"""

        item, grant, settings = context["item"], context["grant"], context["item"]["settings"]
        required = {"category_id", "tags", "privacy_status", "notify_subscribers",
                    "made_for_kids", "contains_synthetic_media"}
        allowed = required | {"default_language", "embeddable", "license",
                              "public_stats_viewable"}
        if (not required.issubset(settings) or set(settings) - allowed
                or len(item["assets"]) != 1
                or type(settings["notify_subscribers"]) is not bool
                or type(settings["made_for_kids"]) is not bool
                or type(settings["contains_synthetic_media"]) is not bool):
            raise official.PublishAPIError("invalid_request")
        snippet = {"title": item["title"], "description": item["body"],
                   "categoryId": str(settings["category_id"]), "tags": settings["tags"]}
        if settings.get("default_language"):
            snippet["defaultLanguage"] = settings["default_language"]
        status = {"privacyStatus": settings["privacy_status"],
                  "selfDeclaredMadeForKids": settings["made_for_kids"],
                  "containsSyntheticMedia": settings["contains_synthetic_media"]}
        for plan_key, api_key in (("embeddable", "embeddable"), ("license", "license"),
                                  ("public_stats_viewable", "publicStatsViewable")):
            if plan_key in settings:
                status[api_key] = settings[plan_key]
        if item["action"] == "native_schedule":
            status["privacyStatus"] = "private"
            status["publishAt"] = item["scheduled_at"]
        session = self._mutate(
            context, "youtube-upload-session",
            lambda: self.adapter.youtube_start_upload(
                grant, asset_path=item["assets"][0]["path"],
                metadata={"snippet": snippet, "status": status},
                notify_subscribers=settings["notify_subscribers"],
            ), sensitive=True,
        )
        context = self.context(item["id"])
        uploaded = self._mutate(
            context, "youtube-video-upload",
            lambda: self.adapter.youtube_upload(
                grant, session, asset_path=item["assets"][0]["path"],
            ),
        )
        video_id = uploaded["remote_id"]
        readback = self.adapter.youtube_readback(grant, video_id)
        snippet_back = readback.get("snippet") or {}
        status_back = readback.get("status") or {}
        processing = (readback.get("processingDetails") or {}).get("processingStatus")
        content_matches = (snippet_back.get("title") == item["title"]
                           and snippet_back.get("description") == item["body"])
        settings_back = {}
        mapping = (("category_id", snippet_back.get("categoryId")),
                   ("tags", snippet_back.get("tags", [])),
                   ("privacy_status", status_back.get("privacyStatus")),
                   ("made_for_kids", status_back.get("selfDeclaredMadeForKids")),
                   ("contains_synthetic_media", status_back.get("containsSyntheticMedia")),
                   ("default_language", snippet_back.get("defaultLanguage")),
                   ("embeddable", status_back.get("embeddable")),
                   ("license", status_back.get("license")),
                   ("public_stats_viewable", status_back.get("publicStatsViewable")))
        for key, value in mapping:
            if key in settings and value is not None:
                settings_back[key] = value
        final_state = "scheduled" if item["action"] == "native_schedule" else "published"
        platform_time = status_back.get("publishAt") if final_state == "scheduled" else snippet_back.get("publishedAt")
        media_matches = processing == "succeeded"
        # videos.list 沒有正式 permalink；未由管理介面實際讀回網址前一律 pending。
        complete = False
        return self._save_record(
            item, state=final_state if complete else "pending",
            source="official_api", reason="verified" if complete else "supplemental_readback_required",
            platform_id=video_id, url=None, platform_time=platform_time,
            content_matches=content_matches, media_matches=media_matches,
            settings_readback=settings_back, selected=readback,
        )

    def _facebook(self, context):
        """支援文字、連結與 HTTPS 圖片；影片留待 PUB-03。"""

        item, grant, settings = context["item"], context["grant"], context["item"]["settings"]
        if (set(settings) - {"visibility", "crosspost", "link", "media_urls"}
                or settings.get("visibility") != "public"
                or settings.get("crosspost", False) is not False):
            raise official.PublishAPIError("adapter_unavailable")
        if item["format"] == "video":
            raise official.PublishAPIError("adapter_unavailable")
        media_urls = settings.get("media_urls", [])
        if item["assets"] and (not isinstance(media_urls, list)
                               or len(media_urls) != len(item["assets"])):
            raise official.PublishAPIError("invalid_request")
        photo_ids = []
        for index, (asset, source_url) in enumerate(zip(item["assets"], media_urls), start=1):
            stage = f"facebook-photo-{index}"
            current = self.context(item["id"])
            result = self._mutate(
                current, stage,
                lambda asset=asset, source_url=source_url: self.adapter.facebook_upload_photo(
                    grant, source_url=source_url, caption="",
                    alt_text=asset["alt_text"], published=False,
                ),
            )
            photo_ids.append(result["remote_id"])
        scheduled = (_timestamp_seconds(item["scheduled_at"])
                     if item["action"] == "native_schedule" else None)
        current = self.context(item["id"])
        result = self._mutate(
            current, "facebook-post",
            lambda: self.adapter.facebook_create_feed(
                grant, message=item["body"], link=settings.get("link"),
                attached_media=photo_ids or None,
                scheduled_publish_time=scheduled,
            ),
        )
        post_id = result["remote_id"]
        readback = self.adapter.facebook_readback(grant, post_id)
        content_matches = readback.get("message", "") == item["body"]
        media_matches = not item["assets"]
        settings_back = {}
        if "visibility" in settings and readback.get("is_published") is True:
            settings_back["visibility"] = "public"
        final_state = "scheduled" if item["action"] == "native_schedule" else "published"
        platform_time = _iso_time(readback.get("scheduled_publish_time")
                                  if final_state == "scheduled"
                                  else readback.get("created_time"))
        complete = (readback.get("id") == post_id and readback.get("permalink_url")
                    and platform_time and content_matches and media_matches
                    and settings_back == settings
                    and ((final_state == "published" and readback.get("is_published") is True)
                         or (final_state == "scheduled" and readback.get("is_published") is False)))
        return self._save_record(
            item, state=final_state if complete else "pending", source="official_api",
            reason="verified" if complete else "supplemental_readback_required",
            platform_id=post_id, url=readback.get("permalink_url"),
            platform_time=platform_time, content_matches=content_matches,
            media_matches=media_matches, settings_readback=settings_back,
            selected=readback,
        )

    def _instagram(self, context):
        """建立單圖、輪播或 Reel 容器；處理中只做下次唯讀續查。"""

        item, grant, settings = context["item"], context["grant"], context["item"]["settings"]
        if set(settings) - {"media_urls", "share_to_feed", "cover_url"}:
            raise official.PublishAPIError("adapter_unavailable")
        media_urls = settings.get("media_urls")
        if not isinstance(media_urls, list) or len(media_urls) != len(item["assets"]):
            raise official.PublishAPIError("invalid_request")
        if item["format"] == "carousel":
            children = []
            for index, (asset, source_url) in enumerate(zip(item["assets"], media_urls), start=1):
                current = self.context(item["id"])
                result = self._mutate(
                    current, f"instagram-child-{index}",
                    lambda asset=asset, source_url=source_url: self.adapter.instagram_create_media(
                        grant, {"image_url": source_url, "alt_text": asset["alt_text"],
                                "is_carousel_item": True},
                    ),
                )
                children.append(result["remote_id"])
            params = {"media_type": "CAROUSEL", "children": children,
                      "caption": item["body"]}
        elif item["format"] == "reel":
            params = {"media_type": "REELS", "video_url": media_urls[0],
                      "caption": item["body"],
                      "share_to_feed": settings.get("share_to_feed", True)}
            if settings.get("cover_url"):
                params["cover_url"] = settings["cover_url"]
        else:
            params = {"image_url": media_urls[0], "caption": item["body"],
                      "alt_text": item["assets"][0]["alt_text"]}
        current = self.context(item["id"])
        container = self._mutate(
            current, "instagram-parent-container",
            lambda: self.adapter.instagram_create_media(grant, params),
        )
        container_id = container["remote_id"]
        status = self.adapter.instagram_container_status(grant, container_id)
        if status.get("status_code") != "FINISHED":
            if status.get("status_code") in {"ERROR", "EXPIRED"}:
                return self._save_record(
                    item, state="failed", source="official_api",
                    reason="container_failed", platform_id=container_id,
                    selected=status,
                )
            return {"result": "pending", "item_id": item["id"],
                    "ledger_state": "in_progress", "external_actions": True,
                    "next_action": "readback_same_container_only"}
        current = self.context(item["id"])
        published = self._mutate(
            current, "instagram-publish",
            lambda: self.adapter.instagram_publish(grant, container_id),
        )
        media_id = published["remote_id"]
        readback = self.adapter.instagram_readback(grant, media_id)
        content_matches = (readback.get("caption") or "") == item["body"]
        settings_back = {}
        if "share_to_feed" in settings and readback.get("media_product_type") is not None:
            settings_back["share_to_feed"] = readback.get("media_product_type") == "FEED"
        return self._save_record(
            item, state="pending", source="official_api",
            reason="supplemental_media_and_settings_readback_required",
            platform_id=media_id, url=readback.get("permalink"),
            platform_time=readback.get("timestamp"), content_matches=content_matches,
            media_matches=False, settings_readback=settings_back, selected=readback,
        )

    def _threads(self, context):
        """支援文字、單圖與單影片；輪播等 PUB-03 查證後再開。"""

        item, grant, settings = context["item"], context["grant"], context["item"]["settings"]
        if set(settings) - {"media_urls", "reply_control", "link_attachment",
                            "topic_tag", "is_spoiler_media"}:
            raise official.PublishAPIError("adapter_unavailable")
        if item["format"] == "carousel":
            raise official.PublishAPIError("adapter_unavailable")
        params = {"text": item["body"]}
        media_urls = settings.get("media_urls", [])
        if item["format"] == "text":
            params["media_type"] = "TEXT"
        elif len(item["assets"]) == 1 and len(media_urls) == 1:
            params.update(media_type="IMAGE" if item["format"] == "image" else "VIDEO",
                          **{"image_url" if item["format"] == "image" else "video_url": media_urls[0]})
            if item["assets"][0]["alt_text"]:
                params["alt_text"] = item["assets"][0]["alt_text"]
        else:
            raise official.PublishAPIError("invalid_request")
        for key in ("reply_control", "link_attachment", "topic_tag", "is_spoiler_media"):
            if key in settings and settings[key] is not None:
                params[key] = settings[key]
        current = self.context(item["id"])
        container = self._mutate(
            current, "threads-container",
            lambda: self.adapter.threads_create_container(grant, params),
        )
        container_id = container["remote_id"]
        status = self.adapter.threads_container_status(grant, container_id)
        if status.get("status") != "FINISHED":
            if status.get("status") in {"ERROR", "EXPIRED"}:
                return self._save_record(
                    item, state="failed", source="official_api",
                    reason="container_failed", platform_id=container_id,
                    selected=status,
                )
            return {"result": "pending", "item_id": item["id"],
                    "ledger_state": "in_progress", "external_actions": True,
                    "next_action": "readback_same_container_only"}
        current = self.context(item["id"])
        published = self._mutate(
            current, "threads-publish",
            lambda: self.adapter.threads_publish(grant, container_id),
        )
        thread_id = published["remote_id"]
        readback = self.adapter.threads_readback(grant, thread_id)
        content_matches = (readback.get("text") or "") == item["body"]
        media_matches = not item["assets"]
        return self._save_record(
            item, state="pending", source="official_api",
            reason="supplemental_media_and_settings_readback_required",
            platform_id=thread_id, url=readback.get("permalink"),
            platform_time=readback.get("timestamp"), content_matches=content_matches,
            media_matches=media_matches, settings_readback={}, selected=readback,
        )

    def prepare_browser_handoff(self, item_id):
        """為 Substack 或已預覽的瀏覽器路徑建立本機交接，不操作瀏覽器。"""

        context = self.context(item_id)
        item = context["item"]
        if item["interface"] != "controlled_browser":
            raise ValueError("interface_not_browser")
        handoff = {
            "schema_version": 1, "job_id": context["job_id"],
            "item_id": item["id"], "preview_sha256": context["preview_sha256"],
            "approval_ref": context["attempt"]["approval_ref"],
            "platform": item["platform"], "target_label": item["target_label"],
            "target_id": item["target_id"], "target_url": item["target_url"],
            "title": item["title"], "body": item["body"], "assets": item["assets"],
            "action": item["action"], "scheduled_at": item["scheduled_at"],
            "settings": item["settings"],
            "write_claim_stage": "browser-write",
            "rules": ["claim_before_first_remote_edit", "submit_once",
                      "reload_and_record_observation", "stop_on_unknown"],
        }
        job.secrets(handoff)
        path = job.local(
            self.root,
            f'social-media/publishing/{context["job_id"]}/browser-handoff.json',
            must_exist=False,
        )
        job.save(path, handoff)
        return {"result": "browser_handoff_ready", "item_id": item_id,
                "handoff": path.relative_to(self.root).as_posix(),
                "external_actions": False}

    def claim_browser_write(self, item_id):
        """Agent 在首次編輯遠端草稿前呼叫；本函式本身不操作瀏覽器。"""

        context = self.context(item_id)
        if context["item"]["interface"] != "controlled_browser":
            raise ValueError("interface_not_browser")
        self._claim(item_id, "browser-write")
        return {"result": "browser_write_claimed", "item_id": item_id,
                "external_actions": False}

    def record_observation(self, item_id, relative):
        """將 Agent 的獨立 GET／重載觀測正規化並交給同一 receipt 護欄。"""

        context = self.context(item_id, executable=False)
        item = context["item"]
        observation = job.read(job.local(self.root, relative))
        expected = {"source", "state", "platform_id", "url", "platform_time",
                    "observed_at", "content_matches", "media_matches",
                    "settings_readback", "selected"}
        job.exact(observation, expected)
        if observation["source"] not in {"official_api", "official_connector",
                                         "controlled_browser", "manual_readback"}:
            raise ValueError("observation_source_invalid")
        if observation["state"] not in job.FINAL | {"pending", "unknown", "failed"}:
            raise ValueError("state_invalid")
        if type(observation["content_matches"]) is not bool or type(observation["media_matches"]) is not bool:
            raise ValueError("comparison_invalid")
        return self._save_record(
            item, state=observation["state"], source=observation["source"],
            reason="independent_observation", platform_id=observation["platform_id"],
            url=observation["url"], platform_time=observation["platform_time"],
            observed_at=observation["observed_at"],
            content_matches=observation["content_matches"],
            media_matches=observation["media_matches"],
            settings_readback=observation["settings_readback"],
            selected=observation["selected"],
        )


def main():
    """CLI 永不輸出 Token、原始平台回應或例外本文。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("execute-api", "prepare-browser",
                                            "claim-browser", "record-observation"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--item", required=True)
    parser.add_argument("--connection", default="main")
    parser.add_argument("--observation")
    parser.add_argument("--execute-external-write", action="store_true")
    parser.add_argument("--no-token-refresh", action="store_true")
    args = parser.parse_args()
    try:
        executor = PublishExecutor(
            args.workspace, args.plan, connection=args.connection,
            allow_token_refresh=not args.no_token_refresh,
        )
        if args.command == "execute-api":
            if not args.execute_external_write:
                raise ValueError("external_write_flag_required")
            result = executor.execute_api(args.item)
        elif args.command == "prepare-browser":
            result = executor.prepare_browser_handoff(args.item)
        elif args.command == "claim-browser":
            result = executor.claim_browser_write(args.item)
        else:
            if not args.observation:
                raise ValueError("observation_required")
            result = executor.record_observation(args.item, args.observation)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            official.PublishAPIError):
        print(json.dumps({"result": "blocked", "external_actions": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
