#!/usr/bin/env python3
"""以契約變異驗證來源與授權界線；不下載或呼叫 OpenCLI。"""

import copy
import json
import unittest

from validate_package import ROOT, ValidationError, read_manifest, validate_opencli_dependency, validate_opencli_source


class OpenCLISourceTests(unittest.TestCase):
    """驗證可安裝候選的來源資料，不冒充真實建置或 Browser Bridge 測試。"""

    def setUp(self):
        """只讀目前公開固定來源，所有變異只發生在記憶體。"""
        self.manifest = read_manifest()
        self.source = json.loads((ROOT / self.manifest["dependencies"][0]["source_contract"]).read_text())

    def test_current_contract_is_explicit_runtime_dependency(self):
        """固定來源通過，技能安裝器仍保持離線與不管理外部工具。"""
        validate_opencli_dependency(self.manifest)
        self.assertFalse(self.manifest["installation"]["manager_network_access"])

    def test_floating_fork_or_unverified_asset_is_rejected(self):
        """變異版本、來源與完整性資訊，不能混入另一個下載位置。"""
        changes = [("tag", "main"), ("commit", "latest"), ("tree", "abc"),
                   ("download_url", "https://example.test/opencli.git"),
                   ("license_sha256", ""), ("lockfile_sha256", "")]
        for field, value in changes:
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.source)
                candidate[field] = value
                with self.assertRaises(ValidationError):
                    validate_opencli_source(candidate)
        for field, value in [("url", "https://example.test/extension.zip"), ("sha256", ""), ("host_permissions", [])]:
            with self.subTest(extension=field):
                candidate = copy.deepcopy(self.source)
                candidate["extension"][field] = value
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
