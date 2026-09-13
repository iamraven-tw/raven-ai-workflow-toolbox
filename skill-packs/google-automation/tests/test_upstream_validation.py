"""確認 Windows 相容性調整只跳過 1314，不吞掉真正的測試失敗。"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_upstream import prepare_tests

FIXTURE = '''class Probe(unittest.TestCase):
    def runTest(self):
        if True:
            docs_path = Path(".")
            outside = Path("unused")
            (docs_path / "course-progress.md").symlink_to(outside)
            self.completed = True
'''


class UpstreamValidationTests(unittest.TestCase):
    def probe(self, error):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'original'
            relative = Path('skills/google-apps-script-teaching/scripts/test_update_course_progress.py')
            target = source / relative
            target.parent.mkdir(parents=True)
            target.write_text(FIXTURE, encoding='utf-8')
            destination = Path(temp) / 'prepared'
            prepare_tests(source, destination)
            scope = {'Path': Path, 'unittest': unittest}
            exec((destination / relative).read_text(encoding='utf-8'), scope)
            case = scope['Probe']()
            with patch.object(Path, 'symlink_to', side_effect=error):
                result = case.run()
            self.assertEqual(target.read_text(encoding='utf-8'), FIXTURE)
            return case, result

    def test_only_missing_privilege_is_skipped(self):
        error = OSError('missing privilege')
        error.winerror = 1314
        case, result = self.probe(error)
        self.assertEqual(len(result.skipped), 1)
        self.assertFalse(result.errors)
        self.assertFalse(hasattr(case, 'completed'))

    def test_other_errors_fail(self):
        _, result = self.probe(PermissionError('different permission problem'))
        self.assertEqual(len(result.errors), 1)
        self.assertFalse(result.skipped)

    def test_capable_host_runs_test(self):
        case, result = self.probe(None)
        self.assertTrue(case.completed)
        self.assertTrue(result.wasSuccessful())
        self.assertFalse(result.skipped)
