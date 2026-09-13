#!/usr/bin/env python3
"""驗證 Toolbox 第一次安裝後的盤點邀請與授權邊界。"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FirstInstallInventoryOfferTest(unittest.TestCase):
    """避免盤點邀請被誤寫成自動掃描或一般重跑步驟。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        cls.agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        cls.inventory_install = (
            ROOT / "skill-packs" / "agent-inventory" / "INSTALL.md"
        ).read_text(encoding="utf-8")

    def test_offer_follows_first_successful_install_and_discovery(self) -> None:
        for document in (self.install, self.agents):
            self.assertIn("第一個 Toolbox 技能包", document)
            self.assertIn("技能發現驗證", document)
            self.assertIn("主動詢問一次", document)

    def test_offer_does_not_authorize_install_or_scan(self) -> None:
        self.assertIn("不得自動開始掃描", self.install)
        self.assertIn("詢問不是掃描授權", self.agents)
        self.assertIn("不會跳過下方的下載、寫入與掃描範圍授權", self.inventory_install)

    def test_decline_and_non_first_operations_do_not_reprompt(self) -> None:
        for phrase in ("拒絕", "稍後處理", "同一安裝流程中重複詢問"):
            self.assertIn(phrase, self.install)
        for operation in ("status", "相同版本重跑", "修復", "更新", "回復", "移除"):
            self.assertIn(operation, self.install)


if __name__ == "__main__":
    unittest.main()
