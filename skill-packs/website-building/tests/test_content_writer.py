#!/usr/bin/env python3
"""以虛構工作區驗證文案工具：骨架、事實邊界、預覽與寫入、同步、與 scaffold 的銜接。"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "skills/website-content-writing/scripts/content_writer.py"
SCAFFOLD = ROOT / "skills/website-build/scripts/scaffold_site.py"
DEFAULT = ROOT / "skills/website-setup/assets/default-config.json"

POST = """---
title: "虛構的第一篇文章"
date: "2026-01-02"
description: "說明我為什麼做這件事，以及第一次合作會發生什麼。"
tags: ["虛構"]
---

## 為什麼做這件事

{body}

## 第一次合作會發生什麼

先聊三十分鐘釐清目標，再決定要不要做。每一步都交付你可以自己維護的成果，不綁定任何我才能操作的工具。這是虛構文章的內文，用來確認長度與格式檢查。
"""


def configured_config() -> dict:
    payload = json.loads(DEFAULT.read_text(encoding="utf-8"))
    payload["pages"]["required"] = ["home", "about", "services", "blog", "contact", "not_found"]
    payload["business"].update(
        {
            "status": "configured", "site_name": "虛構工作室", "one_line_positioning": "幫虛構的小店把流程交給 AI",
            "audience_summary": "沒有技術團隊的虛構店主", "offerings": [{"name": "虛構諮詢", "summary": "一次會談釐清可自動化的流程"}],
            "trust_signals": ["虛構的三年顧問經驗"],
            "primary_call_to_action": {"kind": "mailto", "label": "寫信給我", "target": "mailto:hello@example.invalid"},
            "contact_channels": [{"kind": "email", "label": "Email", "target": "mailto:hello@example.invalid"}],
        }
    )
    return payload


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *arguments], capture_output=True, text=True)


class ContentWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="fictional-website-copy-")
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "ws"
        (self.workspace / "website").mkdir(parents=True)
        self.config = self.workspace / "website/config.json"
        self.config.write_text(json.dumps(configured_config(), ensure_ascii=False), encoding="utf-8")
        self.candidate = self.root / "candidate.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def draft(self) -> dict:
        result = run(str(WRITER), "draft", "--config", str(self.config), "--out", str(self.candidate))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(self.candidate.read_text(encoding="utf-8"))

    def write_candidate(self, payload: dict) -> None:
        self.candidate.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def filled(self, *, status: str = "draft") -> dict:
        payload = self.draft()
        payload["status"] = status
        for field in payload["home"]:
            if payload["home"][field]["text"] is None:
                payload["home"][field] = {"text": f"虛構首頁 {field}", "source": "ai_suggestion"}
        payload["home"]["offerings_heading"] = {"text": "三件我能幫上的事", "source": "ai_suggestion"}
        payload["about"]["title"] = {"text": "關於虛構工作室", "source": "ai_suggestion"}
        payload["about"]["intro"] = {"text": "幫虛構的小店把流程交給 AI", "source": "user_fact"}
        payload["about"]["sections"][1]["body"] = {"text": "先釐清目標，再決定做法；每一步都交付你可以自己維護的成果。", "source": "ai_suggestion"}
        payload["about"]["cta_heading"] = {"text": "寫信給我", "source": "user_fact"}
        for page in ("services", "contact", "blog", "not_found"):
            for field in payload[page]:
                payload[page][field] = {"text": f"虛構{page}{field}", "source": "ai_suggestion"}
        return payload

    def test_draft_marks_facts_and_refuses_unconfigured(self) -> None:
        payload = self.draft()
        self.assertEqual(payload["status"], "draft")
        self.assertEqual(payload["home"]["title"], {"text": "幫虛構的小店把流程交給 AI", "source": "user_fact"})
        self.assertEqual(payload["home"]["primary_cta"]["source"], "user_fact")
        self.assertEqual(payload["home"]["offerings_heading"], {"text": None, "source": "placeholder"})
        self.assertIn("虛構的三年顧問經驗", payload["facts_snapshot"])
        again = run(str(WRITER), "draft", "--config", str(self.config), "--out", str(self.candidate))
        self.assertEqual(again.returncode, 2)
        unconfigured = self.root / "unconfigured.json"
        unconfigured.write_text(DEFAULT.read_text(encoding="utf-8"), encoding="utf-8")
        blocked = run(str(WRITER), "draft", "--config", str(unconfigured), "--out", str(self.root / "x.json"))
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("website-setup", blocked.stderr)

    def test_fact_boundary_blocks_unverified_numbers(self) -> None:
        payload = self.filled()
        payload["home"]["lead"] = {"text": "已經幫超過 200 家店省下時間", "source": "ai_suggestion"}
        payload["about"]["sections"][1]["body"] = {"text": "有十年以上的經驗，服務過三百位客戶。", "source": "ai_suggestion"}
        self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate), "--config", str(self.config)).stdout)
        kinds = {(f["path"], f["kind"]) for f in preview["blocking"]}
        self.assertIn(("home.lead", "unverified_number"), kinds)
        self.assertIn(("about.sections[1].body", "unverified_number"), kinds)
        apply = run(str(WRITER), "apply", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate), "--expected-preview-sha256", preview["preview_sha256"], "--confirm-write")
        self.assertEqual(apply.returncode, 2)
        self.assertFalse((self.workspace / "website/copy.json").exists())

        payload["home"]["lead"] = {"text": "三年顧問經驗，只做能自己維護的流程。", "source": "ai_suggestion"}
        payload["about"]["sections"][1]["body"] = {"text": "先釐清目標，再決定做法。", "source": "ai_suggestion"}
        self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate), "--config", str(self.config)).stdout)
        self.assertEqual(preview["blocking"], [])

    def test_final_status_blocks_placeholders_and_apply_requires_confirmation(self) -> None:
        payload = self.filled(status="final")
        payload["services"]["closing_note"] = {"text": "這句是佔位，請依實際情況改寫。", "source": "ai_suggestion"}
        self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        self.assertIn("placeholder_text", {f["kind"] for f in preview["blocking"]})

        payload["services"]["closing_note"] = {"text": None, "source": "placeholder"}
        self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        self.assertIn("placeholder_source", {f["kind"] for f in preview["blocking"]})

        payload["services"]["closing_note"] = {"text": "先聊三十分鐘再決定。", "source": "ai_suggestion"}
        self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        self.assertEqual(preview["blocking"], [])
        self.assertEqual(preview["source_counts"]["placeholder"], 0)
        self.assertFalse((self.workspace / "website/copy.json").exists())

        without = run(str(WRITER), "apply", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate), "--expected-preview-sha256", preview["preview_sha256"])
        self.assertEqual(without.returncode, 2)
        wrong = run(str(WRITER), "apply", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate), "--expected-preview-sha256", "0" * 64, "--confirm-write")
        self.assertEqual(wrong.returncode, 2)
        applied = run(str(WRITER), "apply", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate), "--expected-preview-sha256", preview["preview_sha256"], "--confirm-write")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(json.loads((self.workspace / "website/copy.json").read_text(encoding="utf-8"))["status"], "final")

    def test_posts_are_validated_and_synced_and_scaffold_applies_copy(self) -> None:
        payload = self.filled()
        posts_dir = self.workspace / "website/posts"; posts_dir.mkdir()
        (posts_dir / "first-post.md").write_text(POST.format(body="我原本在虛構的小店工作，看到重複的事一直吃掉時間。" * 2), encoding="utf-8")
        payload["posts"] = [{"slug": "first-post", "file": "first-post.md", "source": "user_fact"}]
        self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        self.assertEqual(preview["posts"], ["first-post.md"])
        self.assertEqual(preview["blocking"], [])

        payload["posts"][0]["source"] = "ai_suggestion"; self.write_candidate(payload)
        (posts_dir / "first-post.md").write_text(POST.format(body="我們服務過 500 家店。"), encoding="utf-8")
        flagged = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        self.assertIn("unverified_number", {f["kind"] for f in flagged["blocking"]})
        (posts_dir / "first-post.md").write_text(POST.format(body="我原本在虛構的小店工作，看到重複的事一直吃掉時間。" * 2), encoding="utf-8")
        payload["posts"][0]["source"] = "user_fact"

        short = posts_dir / "short.md"; short.write_text("---\ntitle: \"短\"\ndate: \"2026-01-03\"\ndescription: \"x\"\n---\n太短", encoding="utf-8")
        payload["posts"].append({"slug": "short", "file": "short.md", "source": "ai_suggestion"})
        self.write_candidate(payload)
        bad = run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate))
        self.assertEqual(bad.returncode, 2)
        self.assertIn("100", bad.stderr)
        payload["posts"].pop(); self.write_candidate(payload)

        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        run(str(WRITER), "apply", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate), "--expected-preview-sha256", preview["preview_sha256"], "--confirm-write")

        # scaffold 自動套用工作區文案與文章，並移除範例文章
        target = self.root / "site"
        plan = json.loads(run(str(SCAFFOLD), "plan", "--config", str(self.config), "--target", str(target)).stdout)
        self.assertIn("copy.json", plan["copy_layer"])
        scaffold = run(str(SCAFFOLD), "scaffold", "--config", str(self.config), "--target", str(target), "--confirm-write")
        self.assertEqual(scaffold.returncode, 0, scaffold.stderr)
        payload_out = json.loads(scaffold.stdout)
        self.assertTrue(payload_out["copy_layer"]["applied"])
        self.assertEqual(payload_out["copy_layer"]["posts_copied"], ["first-post.md"])
        site_copy = (target / "site.copy.mjs").read_text(encoding="utf-8")
        self.assertIn("title: '關於虛構工作室'", site_copy)
        self.assertIn("offerings_heading: '三件我能幫上的事'", site_copy)
        self.assertTrue((target / "src/content/posts/first-post.md").is_file())
        self.assertFalse((target / "src/content/posts/hello-world.md").exists())

        # 已建好的專案改用 sync
        payload["home"]["title"] = {"text": "新的虛構標題", "source": "ai_suggestion"}
        self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        run(str(WRITER), "apply", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate), "--expected-preview-sha256", preview["preview_sha256"], "--confirm-write")
        without = run(str(WRITER), "sync", "--workspace-root", str(self.workspace), "--project", str(target))
        self.assertEqual(without.returncode, 2)
        synced = run(str(WRITER), "sync", "--workspace-root", str(self.workspace), "--project", str(target), "--confirm-write")
        self.assertEqual(synced.returncode, 0, synced.stderr)
        self.assertIn("title: '新的虛構標題'", (target / "site.copy.mjs").read_text(encoding="utf-8"))

    def test_guide_lists_required_fields_and_final_blocks_required_missing(self) -> None:
        """guide 列出必填欄位與狀態；定稿時必填空白被阻擋。"""

        bare = json.loads(run(str(WRITER), "guide").stdout)
        self.assertEqual(bare["required_missing"], ["home.title", "home.lead", "about.intro", "about.sections", "contact.intro"])
        self.assertTrue(all(f["example"] and f["purpose"] for f in bare["fields"]))

        skeleton = self.workspace / "skeleton.json"
        run(str(WRITER), "draft", "--config", str(self.workspace / "website/config.json"), "--out", str(skeleton))
        guide = json.loads(run(str(WRITER), "guide", "--candidate", str(skeleton)).stdout)
        status = {f["path"]: f["status"] for f in guide["fields"]}
        self.assertEqual(status["home.title"], "written_by_user")
        self.assertEqual(status["about.sections"], "written_by_user")
        self.assertEqual(guide["required_missing"], ["about.intro", "contact.intro"])

        payload = self.filled(status="final")
        payload["contact"]["intro"] = {"text": None, "source": "user_fact"}
        payload["about"]["sections"] = [{"heading": {"text": "工作方式", "source": "ai_suggestion"}, "body": {"text": None, "source": "user_fact"}}]
        self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        kinds = {(f["kind"], f["path"]) for f in preview["blocking"]}
        self.assertIn(("required_missing", "contact.intro"), kinds)
        self.assertIn(("required_missing", "about.sections"), kinds)
        self.assertEqual(sorted(preview["required_missing"]), ["about.sections", "contact.intro"])
        payload["status"] = "draft"; self.write_candidate(payload)
        preview = json.loads(run(str(WRITER), "preview", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate)).stdout)
        self.assertNotIn("required_missing", {f["kind"] for f in preview["blocking"]})
        guide = json.loads(run(str(WRITER), "guide", "--candidate", str(self.candidate)).stdout)
        self.assertIn("about.sections", guide["required_missing"])

    def test_secret_fields_rejected(self) -> None:
        payload = self.filled()
        payload["api_token"] = "x"
        self.write_candidate(payload)
        result = run(str(WRITER), "validate", "--workspace-root", str(self.workspace), "--candidate", str(self.candidate))
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
