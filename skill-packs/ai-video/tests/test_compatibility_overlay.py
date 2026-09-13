"""補丁必須拒絕內容漂移、未知檔案與路徑跳脫。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_source import apply_overlay, safe_path, sha
from install_windows import unpack_tool


class OverlayTests(unittest.TestCase):
    def overlay(self):
        return {'files': [{'path': 'helper.py', 'before_sha256': sha(b'old\n'),
            'after_sha256': sha(b'new\n'), 'operations': [{'start': 0, 'end': 1, 'before': 'old\n', 'after': 'new\n'}]}]}

    def test_exact_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'helper.py').write_bytes(b'old\n')
            apply_overlay(root, self.overlay())
            self.assertEqual((root / 'helper.py').read_bytes(), b'new\n')

    def test_modified_source_stays_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'helper.py').write_bytes(b'user changes\n')
            with self.assertRaisesRegex(ValueError, '來源雜湊'):
                apply_overlay(root, self.overlay())
            self.assertEqual((root / 'helper.py').read_bytes(), b'user changes\n')

    def test_bad_output_hash_never_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'helper.py').write_bytes(b'old\n')
            overlay = self.overlay()
            overlay['files'][0]['after_sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, '輸出雜湊'):
                apply_overlay(root, overlay)
            self.assertEqual((root / 'helper.py').read_bytes(), b'old\n')

    def test_new_file_conflict_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'helper.py').write_bytes(b'old\n')
            overlay = self.overlay()
            overlay['files'][0]['before_sha256'] = None
            with self.assertRaises(ValueError):
                apply_overlay(root, overlay)

    def test_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ['../outside', '/outside', 'C:/outside', 'a\\outside']:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    safe_path(Path(temp), name)

    def test_tool_tampering_is_refused(self):
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'tool.zip'
            with zipfile.ZipFile(archive, 'w') as source:
                source.writestr('tool.exe', b'fixed binary')
            destination = root / 'unpacked'
            unpack_tool(archive, destination)
            unpack_tool(archive, destination)
            (destination / 'tool.exe').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, '工具被修改'):
                unpack_tool(archive, destination)
