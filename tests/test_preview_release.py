#!/usr/bin/env python3
"""驗證公開來源版本的 PREVIEW 發行紀錄維持一致。"""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PreviewReleaseTest(unittest.TestCase):
    """避免歷史發行紀錄、版本與發行通道在更新時彼此漂移。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.release = tomllib.loads((ROOT / "release.toml").read_text(encoding="utf-8"))
        cls.notes = (ROOT / "docs" / "preview-release.md").read_text(encoding="utf-8")

    def test_release_metadata_is_preview_prerelease(self) -> None:
        version = self.release["version"]
        self.assertEqual(self.release["channel"], "preview")
        self.assertEqual(self.release["release_status"], "preview_release")
        self.assertRegex(version, r"^0\.\d+\.\d+-preview\.\d+$")
        self.assertEqual(self.release["publication_status_source"], "github_prerelease")
        self.assertEqual(self.release["tag"], "v" + version)
        self.assertEqual(self.release["display_name"], "Raven AI 一人公司工具包")
        self.assertEqual(self.release["repository"], "https://github.com/iamraven-tw/raven-ai-workflow-toolbox")
        self.assertFalse(self.release["scope"]["production_ready"])

    def test_source_release_notes_show_the_same_version(self) -> None:
        """來源版本資訊留在發行紀錄，不要求使用者入口展示舊版號。"""
        self.assertIn("PREVIEW", self.notes)
        self.assertIn(self.release["version"], self.notes)

    def test_source_preview_does_not_claim_stable_support(self) -> None:
        """歷史 Preview 說明仍須保留當時的支援邊界。"""
        self.assertIn("不代表所有技能包已完成實機驗證", self.notes)
        self.assertIn("可能有破壞性變更", self.notes)
        self.assertIsNone(re.search(r"(?:正式|穩定)版已(?:完成|發布)", self.notes))


if __name__ == "__main__":
    unittest.main()
