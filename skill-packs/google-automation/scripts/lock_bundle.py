#!/usr/bin/env python3
"""由維護者在修改內建技能後重建版本雜湊；安裝時只驗證，不自動重建。"""
import json
from pathlib import Path
import tomllib
from manage_install import hash_entry


def main() -> None:
    """以相對路徑保存六個受管理入口的內容摘要。"""
    root = Path(__file__).resolve().parents[1]
    manifest = tomllib.loads((root / 'install.manifest.toml').read_text(encoding='utf-8'))
    entries = {}
    for name in manifest['installation']['managed_entries']:
        kind, digest = hash_entry(root / 'skills' / name)
        entries[name] = {'kind': kind, 'sha256': digest}
    payload = {'version': manifest['installation']['candidate_version'], 'entries': entries}
    (root / 'bundle.lock.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
