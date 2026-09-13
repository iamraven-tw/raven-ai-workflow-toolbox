"""在已驗證來源的暫存副本驗證上游；只有 Windows 1314 跳過 symlink 測試。"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from manage_install import read_manifest, verify_learn_gas


def prepare_tests(source: Path, destination: Path) -> None:
    """不修改固定來源或 runtime，只修正測試對 Windows 權限的假設。"""
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('.git', '__pycache__'))
    test = destination / 'skills/google-apps-script-teaching/scripts/test_update_course_progress.py'
    old = '            (docs_path / "course-progress.md").symlink_to(outside)'
    new = '''            try:
                (docs_path / "course-progress.md").symlink_to(outside)
            except OSError as error:
                if getattr(error, "winerror", None) == 1314:
                    self.skipTest("Windows 未授予建立 symlink 權限；未驗證 symlink 防護")
                raise'''
    content = test.read_text(encoding='utf-8')
    if content.count(old) != 1:
        raise ValueError('上游測試結構已改變，停止套用相容性調整')
    test.write_text(content.replace(old, new), encoding='utf-8', newline='\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--learn-gas-source', required=True, type=Path)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[1] / 'install.manifest.toml')
    args = parser.parse_args()
    source = args.learn_gas_source.resolve()
    verify_learn_gas(read_manifest(args.manifest), source)
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    with tempfile.TemporaryDirectory(prefix='learn-gas-validation-') as temp:
        candidate = Path(temp) / 'source'
        prepare_tests(source, candidate)
        for command in ([sys.executable, 'scripts/validate_skills.py'],
                        [sys.executable, '-m', 'unittest', 'discover', '-s',
                         'skills/google-apps-script-teaching/scripts', '-p', 'test_*.py', '-v']):
            result = subprocess.run(command, cwd=candidate, env=env)
            if result.returncode:
                return result.returncode
    verify_learn_gas(read_manifest(args.manifest), source)
    print('上游驗證通過；安裝使用原始固定來源，symlink 權限不足時明確列為 skipped。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
