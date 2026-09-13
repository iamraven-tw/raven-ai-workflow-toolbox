"""驗證公開快照可獨立驗證、不帶快取、可重現且不覆蓋舊產物。"""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_artifact_test", ROOT / "scripts/prepare_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseArtifactTests(unittest.TestCase):
    def test_reproducible_standalone_zip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix="fictional-release-") as folder:
            output = Path(folder) / "first"
            first = release.prepare(ROOT, output)
            second = release.prepare(ROOT, Path(folder) / "second")
            self.assertEqual(first["archive_sha256"], second["archive_sha256"])
            with zipfile.ZipFile(output / first["archive"]) as archive:
                names = archive.namelist()
            self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
            self.assertIn("website-building/docs/package-decisions.md", names)
            self.assertIn("website-building/skills/website-design-preview/assets/previews/THIRD_PARTY_LICENSES.txt", names)
            with self.assertRaises(ValueError):
                release.prepare(ROOT, output)

    def test_cache_exclusion_does_not_hide_unknown_files(self):
        with tempfile.TemporaryDirectory(prefix="fictional-release-") as folder:
            root = Path(folder)
            (root / "skills/example/__pycache__").mkdir(parents=True)
            (root / "skills/example/__pycache__/module.pyc").write_bytes(b"cache")
            (root / "skills/example/SKILL.md").write_text("fictional", encoding="utf-8")
            self.assertEqual([p.relative_to(root).as_posix() for p in release.source_files(root)], ["skills/example/SKILL.md"])
            (root / "skills/example/.env").write_text("fictional", encoding="utf-8")
            with self.assertRaises(ValueError):
                release.source_files(root)
