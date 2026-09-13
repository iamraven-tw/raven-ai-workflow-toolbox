"""驗證固定 Release 並套用最小相容性補丁；可在 Windows/macOS 執行。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import tomllib

PACK = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(root: Path, name: str) -> Path:
    """拒絕絕對、跨磁碟、反斜線與父目錄路徑。"""
    relative = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or relative.is_absolute() or '..' in relative.parts:
        raise ValueError(f'不安全的封裝路徑：{name}')
    target = root.joinpath(*relative.parts)
    if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink():
        raise ValueError(f'路徑超出目標：{name}')
    return target


def apply_overlay(root: Path, overlay: dict) -> None:
    """先驗證全部輸入與輸出，再寫入，絕不 fuzzy apply。"""
    outputs = {}
    for entry in overlay['files']:
        target = safe_path(root, entry['path'])
        if target in outputs:
            raise ValueError('補丁包含重複檔案')
        original = target.read_bytes() if target.exists() else b''
        expected = entry['before_sha256']
        if (expected is None and target.exists()) or (expected is not None and (not target.exists() or sha(original) != expected)):
            raise ValueError(f'補丁來源雜湊不符：{entry["path"]}')
        lines = original.decode('utf-8').splitlines(keepends=True)
        for op in reversed(entry['operations']):
            if ''.join(lines[op['start']:op['end']]) != op['before']:
                raise ValueError(f'補丁文字不符：{entry["path"]}')
            lines[op['start']:op['end']] = op['after'].splitlines(keepends=True)
        output = ''.join(lines).encode('utf-8')
        if sha(output) != entry['after_sha256']:
            raise ValueError(f'補丁輸出雜湊不符：{entry["path"]}')
        outputs[target] = output
    for target, output in outputs.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output)


def prepare(archive: Path, destination: Path) -> None:
    manifest = tomllib.loads((PACK / 'install.manifest.toml').read_text(encoding='utf-8'))
    if sha(archive.read_bytes()) != manifest['release']['release_asset_sha256']:
        raise ValueError('Release SHA-256 不符')
    patch = PACK / manifest['compatibility_overlay']['path']
    if sha(patch.read_bytes()) != manifest['compatibility_overlay']['sha256']:
        raise ValueError('補丁 SHA-256 不符')
    if destination.exists() or destination.is_symlink():
        raise ValueError('來源準備目錄必須不存在')
    with tempfile.TemporaryDirectory(prefix='video-use-prepare-') as temp:
        staging = Path(temp) / 'source'
        staging.mkdir()
        with tarfile.open(archive) as source:
            for member in source:
                parts = PurePosixPath(member.name).parts
                if not parts or parts[0] != 'raven-video-use-v0.1.1':
                    raise ValueError('Release 根目錄不符')
                if len(parts) == 1 and member.isdir():
                    continue
                target = safe_path(staging, '/'.join(parts[1:]))
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.extractfile(member) as incoming, target.open('xb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
                else:
                    raise ValueError('Release 不得包含 symlink 或特殊檔案')
        apply_overlay(staging, json.loads(patch.read_text(encoding='utf-8')))
        shutil.copytree(staging, destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.archive, args.destination)
    print('固定 Release 與相容性補丁驗證完成。')
