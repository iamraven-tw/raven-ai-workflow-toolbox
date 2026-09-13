#!/usr/bin/env python3
"""驗證產品層級的 PREVIEW 發行標示維持一致。"""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PreviewReleaseTest(unittest.TestCase):
    """避免文件、版本與發行通道在更新時彼此漂移。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.release = tomllib.loads((ROOT / "release.toml").read_text(encoding="utf-8"))
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
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

    def test_user_entrypoints_show_the_same_version(self) -> None:
        version = self.release["version"]
        for document in (self.readme, self.install, self.notes):
            self.assertIn("PREVIEW", document)
            self.assertIn(version, document)

    def test_preview_does_not_claim_stable_support(self) -> None:
        combined = "\n".join((self.readme, self.install, self.notes))
        self.assertIn("尚未正式支援", combined)
        self.assertIn("可能有破壞性變更", combined)
        self.assertIsNone(re.search(r"(?:正式|穩定)版已(?:完成|發布)", combined))


if __name__ == "__main__":
    unittest.main()
