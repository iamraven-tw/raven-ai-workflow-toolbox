#!/usr/bin/env python3
"""唯讀檢查文案格式、媒體分流與核准一致性；不執行外部操作。"""

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

FORMATS = {
    "youtube": {"video", "short"},
    "instagram": {"caption", "carousel", "reel"},
    "facebook": {"post", "image", "video"},
    "threads": {"post"},
    "substack": {"article"},
}
ROUTES = {
    "image": "social-image-production",
    "edit_video": "existing-ai-video",
    "record_video": "human-recording-brief",
    "generate_video": "generation-tool-and-authorization-required",
}


class InvalidDraft(ValueError):
    """固定錯誤代稱，避免將私人草稿印入例外。"""


def require(condition, code):
    """中止不符合契約的紀錄。"""
    if not condition:
        raise InvalidDraft(code)


def texts(value, names):
    """驗證必要非空文字欄位。"""
    require(isinstance(value, dict), "object_required")
    require(all(isinstance(value.get(k), str) and value[k].strip() for k in names), "missing_text")


def string_list(value):
    """來源只檢查型別，絕不開啟來源參照。"""
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)


def digest(draft, origin):
    """內容修改會使核准失效，包含額外欄位與媒體簡報。"""
    content = {k: v for k, v in draft.items() if k not in {"approval", "status"}}
    return hashlib.sha256(json.dumps({"input": origin, "draft": content}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def validate(record, *, handoff=False, ids=None):
    """驗證可觀察的資料限制；不證明來源真實或人類同意。"""
    require(isinstance(record, dict) and record.get("schema_version") == 1, "schema_version")
    texts(record.get("input"), ("kind", "evidence_ref"))
    require(record["input"]["kind"] in {"planning", "direct_user"}, "input_kind")
    drafts = record.get("drafts")
    require(isinstance(drafts, list) and drafts, "drafts_required")
    seen, results = set(), []
    for draft in drafts:
        texts(draft, ("id", "platform", "format", "body", "cta_goal", "voice_basis", "status"))
        require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", draft["id"]), "invalid_id")
        require(draft["id"] not in seen, "duplicate_id")
        seen.add(draft["id"])
        platform = draft["platform"]
        require(platform in FORMATS and draft["format"] in FORMATS[platform], "unsupported_format")
        title = draft.get("title")
        require(isinstance(title, str), "title_required")
        if platform in {"youtube", "substack"}:
            require(title.strip(), "title_required")
        body = draft["body"]
        warnings = []
        if platform == "youtube":
            require(len(title) <= 100 and len(body.encode("utf-8")) <= 5000, "youtube_limit")
            require(not any(c in title + body for c in "<>"), "youtube_angle_brackets")
        elif platform == "threads":
            require(len(body) <= 500, "threads_base_limit")
        elif platform == "instagram":
            require(len(body) <= 2200, "instagram_caption_limit")
            warnings.append("instagram_tags_and_selected_route_require_review")
        else:
            warnings.append("platform_hard_limit_not_verified")
        require(string_list(draft.get("sources")) and string_list(draft.get("unresolved")), "reference_lists")
        media = draft.get("media")
        require(isinstance(media, list), "media_required")
        routes = []
        for item in media:
            texts(item, ("kind", "status", "rights"))
            kind = item["kind"]
            require(kind in ROUTES and item["status"] in {"needed", "provided"}, "media_kind_or_status")
            require(string_list(item.get("references")), "media_references")
            if item["status"] == "provided" or kind == "edit_video":
                require(item["references"], "media_source_required")
            brief = item.get("brief")
            if kind == "image":
                texts(brief, ("visual", "aspect_ratio", "alt_text"))
                require(string_list(brief.get("exact_text")), "image_text_required")
            else:
                texts(brief, ("script", "duration_target", "aspect_ratio"))
                require(string_list(brief.get("shots")) and brief["shots"], "shots_required")
            routes.append(ROUTES[kind])
        require(draft["status"] in {"draft", "approved"}, "invalid_status")
        approval = draft.get("approval")
        fingerprint = digest(draft, record["input"])
        if draft["status"] == "draft":
            require(approval is None, "draft_has_approval")
        else:
            texts(approval, ("scope", "digest", "user_response", "evidence_ref", "confirmed_at"))
            require(approval["scope"] == "copy_only" and approval["digest"] == fingerprint, "stale_or_wrong_approval")
            try:
                require(datetime.fromisoformat(approval["confirmed_at"]).tzinfo is not None, "approval_timezone")
            except ValueError:
                raise InvalidDraft("approval_time") from None
        selected = ids is None or draft["id"] in ids
        if handoff and selected:
            require(draft["status"] == "approved" and not draft["unresolved"], "handoff_not_approved_or_unresolved")
        results.append({"id": draft["id"], "digest": fingerprint, "characters": len(body),
                        "utf8_bytes": len(body.encode("utf-8")), "title_characters": len(title),
                        "routes": routes, "warnings": warnings})
    if ids is not None:
        require(bool(ids) and len(ids) == len(set(ids)) and set(ids) <= seen, "unknown_or_duplicate_selection")
    return {"valid": True, "drafts": results, "publishing_authorized": False,
            "human_approval_verified": False, "network_accessed": False}


def main():
    """只讀一個本機紀錄；不輸出文案、路徑或原始例外。"""
    parser = argparse.ArgumentParser(description="社群文案唯讀預檢")
    parser.add_argument("record")
    parser.add_argument("--handoff", action="store_true")
    parser.add_argument("--ids", nargs="+")
    args = parser.parse_args()
    try:
        path = Path(args.record)
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024 * 1024, "invalid_file")
        result = validate(json.loads(path.read_text(encoding="utf-8")), handoff=args.handoff, ids=args.ids)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except InvalidDraft as error:
        print(json.dumps({"valid": False, "error": str(error)}))
    except Exception:
        print(json.dumps({"valid": False, "error": "invalid_record"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
