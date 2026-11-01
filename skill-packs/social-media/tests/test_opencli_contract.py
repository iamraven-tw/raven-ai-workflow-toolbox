#!/usr/bin/env python3
"""以契約變異驗證來源與授權界線；不下載或呼叫 OpenCLI。"""

import copy
import json
import unittest

from validate_package import ROOT, ValidationError, read_manifest, validate_opencli_dependency, validate_opencli_source


class OpenCLISourceTests(unittest.TestCase):
    """驗證可安裝候選的來源資料，不冒充真實建置或 Browser Bridge 測試。"""

    def setUp(self):
        """只讀目前的來源契約，所有變異只發生在記憶體。"""
        self.manifest = read_manifest()
        self.source = json.loads((ROOT / self.manifest["dependencies"][0]["source_contract"]).read_text())

    def test_current_contract_is_explicit_runtime_dependency(self):
        """latest 來源契約通過，技能安裝器仍保持離線與不管理外部工具。"""
        validate_opencli_dependency(self.manifest)
        self.assertFalse(self.manifest["installation"]["manager_network_access"])

    def test_fork_prerelease_or_unverified_contract_is_rejected(self):
        """latest 政策下仍不能換來源、吃 prerelease、放寬擴充配對或遺失測試版本紀錄。"""
        changes = [("download_url", "https://example.test/opencli.git"),
                   ("upstream_url", "https://example.test/opencli"),
                   ("version_policy", "main"),
                   ("tier", "A"),
                   ("release_selection", "latest_including_prerelease"),
                   ("schema_version", 1)]
        for field, value in changes:
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.source)
                candidate[field] = value
                with self.assertRaises(ValidationError):
                    validate_opencli_source(candidate)
        for field, value in [("release_asset_pattern", "any.zip"), ("same_release_as_cli", False),
                             ("host_permissions_expected", []), ("on_new_permission", "load_anyway")]:
            with self.subTest(extension=field):
                candidate = copy.deepcopy(self.source)
                candidate["extension"][field] = value
                with self.assertRaises(ValidationError):
                    validate_opencli_source(candidate)
        for field, value in [("tag", "main"), ("commit", "latest"), ("tree", "abc"),
                             ("license_sha256", ""), ("lockfile_sha256", "")]:
            with self.subTest(tested_release=field):
                candidate = copy.deepcopy(self.source)
                candidate["tested_release"][field] = value
                with self.assertRaises(ValidationError):
                    validate_opencli_source(candidate)

    def test_silent_install_and_premature_live_claim_are_rejected(self):
        """安裝階段或驗收狀態不能越過告知與真實驗證關卡。"""
        for field, value in [("managed_by_skill_installer", True), ("installation_stage", "silent"), ("bundled", True)]:
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.manifest)
                candidate["dependencies"][0][field] = value
                with self.assertRaises(ValidationError):
                    validate_opencli_dependency(candidate)
        self.source["live_installation"] = "verified"
        with self.assertRaises(ValidationError):
            validate_opencli_source(self.source)


if __name__ == "__main__":
    unittest.main()
