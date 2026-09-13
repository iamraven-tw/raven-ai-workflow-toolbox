"""唯讀檢查發行檔案及可選的 Git 歷史；不輸出可疑秘密內容。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.local', 'node_modules', 'dist', '.astro', '__pycache__',
            '.pytest_cache', '.venv', '.cache', '.tmp', 'tmp'}
SENSITIVE_NAMES = {'storage_state.json', '.clasprc.json', '.clasp.json',
                   'sync-manifest.toml', 'oauth-state.json', 'credentials.json'}
PATTERNS = {
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github_token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    'google_api_key': re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b'),
    'aws_access_key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'slack_token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    'private_windows_path': re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+(?!<|Public\b|Default\b)[A-Za-z0-9_.-]+[\\/]'),
    'private_macos_path': re.compile(r'/Users/(?!<)[A-Za-z0-9_.-]+/'),
}


def forbidden(name: str) -> bool:
    path = Path(name)
    return (any(part in EXCLUDED for part in path.parts) or path.name in SENSITIVE_NAMES
            or (path.name.startswith('.env') and path.name != '.env.example')
            or path.suffix.lower() in {'.pyc', '.pyo', '.pem', '.key', '.mp4', '.mov', '.mp3', '.wav'})


def findings(data: bytes) -> list[dict]:
    text = data.decode('utf-8', errors='replace')
    return [{'kind': kind, 'line': text.count('\n', 0, match.start()) + 1}
            for kind, pattern in PATTERNS.items() for match in pattern.finditer(text)]


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def public_files() -> list[Path]:
    if (ROOT / '.git').exists():
        names = git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')
        return sorted({ROOT / name for name in names if name and (ROOT / name).exists()})
    # 發行 ZIP 不含 .git；不走訪本機快取，也不讀取私人同步狀態。
    import os
    result = []
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = [name for name in dirs if name not in EXCLUDED]
        result.extend(Path(directory) / name for name in files)
    return sorted(result)


def audit(history: bool = False) -> dict:
    errors = []
    files = public_files()
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if forbidden(relative):
            errors.append({'path': relative, 'kind': 'excluded_or_sensitive_file'})
            continue
        if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
               for p in [path, *path.parents] if p == ROOT or ROOT in p.parents):
            errors.append({'path': relative, 'kind': 'link'})
            continue
        errors.extend(dict(path=relative, **item) for item in findings(path.read_bytes()))
    for pack in sorted((ROOT / 'skill-packs').iterdir()):
        if not pack.is_dir():
            continue
        for name in ('README.md', 'INSTALL.md', 'install.manifest.toml', 'THIRD_PARTY_NOTICES.md'):
            if not (pack / name).is_file():
                errors.append({'path': pack.name, 'kind': 'missing_' + name})
        manifest = tomllib.loads((pack / 'install.manifest.toml').read_text(encoding='utf-8'))
        if not manifest.get('installable'):
            errors.append({'path': pack.name, 'kind': 'noninstallable_candidate'})
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'release.toml'):
        if not (ROOT / name).is_file():
            errors.append({'path': name, 'kind': 'missing'})
    blob_count = 0
    if history:
        # 只讀 Git 物件，不讀取磁碟上的私人同步 manifest。
        objects = git('rev-list', '--objects', '--all').decode().splitlines()
        process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            for row in objects:
                oid, _, name = row.partition(' ')
                process.stdin.write((oid + '\n').encode())
                process.stdin.flush()
                header = process.stdout.readline().decode().split()
                data = process.stdout.read(int(header[2]))
                process.stdout.read(1)
                if header[1] != 'blob':
                    continue
                blob_count += 1
                if forbidden(name):
                    errors.append({'object': oid, 'path': name, 'kind': 'historical_excluded_file'})
                errors.extend(dict(object=oid, path=name, **item) for item in findings(data))
        finally:
            process.stdin.close()
            process.wait()
    return {'files': len(files), 'history_blobs': blob_count, 'findings': errors,
            'status': 'review_required' if errors else 'passed',
            'limits': 'Pattern and package checks are not a full security or legal audit.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    result = audit(parser.parse_args().history)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['findings']))
