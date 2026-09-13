"""Windows x64 隔離安裝；固定下載、完整副本註冊，不需要 symlink 或管理員。"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
import zipfile

from prepare_source import PACK, prepare, safe_path, sha


def download(url: str, checksum: str, target: Path) -> Path:
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
            temporary = Path(handle.name)
        try:
            urllib.request.urlretrieve(url, temporary)
            if sha(temporary.read_bytes()) != checksum:
                raise ValueError(f'下載雜湊不符：{target.name}')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    if target.is_symlink() or sha(target.read_bytes()) != checksum:
        raise ValueError(f'快取雜湊不符：{target.name}')
    return target


def unpack_tool(archive: Path, destination: Path) -> None:
    """重跑時也逐檔核對解壓內容；不覆寫遭修改的工具。"""
    def write(name: str, data: bytes) -> None:
        # Python 第一次執行會重建 bytecode；只核對來源、套件資料與 binary。
        if '__pycache__' in Path(name).parts or name.endswith('.pyc'):
            return
        target = safe_path(destination, name)
        if target.exists():
            if not target.is_file() or sha(target.read_bytes()) != sha(data):
                raise ValueError(f'既有工具被修改：{target}')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('工具封裝不允許 symlink')
                safe_path(destination, member.filename.rstrip('/'))
                if not member.is_dir():
                    write(member.filename, source.read(member))
    else:
        with tarfile.open(archive) as source:
            for member in source:
                safe_path(destination, member.name)
                if member.isfile():
                    with source.extractfile(member) as stream:
                        write(member.name, stream.read())
                elif not member.isdir():
                    raise ValueError('工具封裝不允許 symlink 或特殊檔案')


def source_hashes(root: Path, *, build_artifacts: bool = False) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if build_artifacts and relative.parts[0] == 'video_use.egg-info':
            continue
        if any(part in {'.venv', '__pycache__'} for part in relative.parts) or relative.as_posix() == 'toolbox-runtime.json':
            continue
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError(f'不接受來源捷徑：{relative}')
        if path.is_file():
            result[relative.as_posix()] = sha(path.read_bytes())
    return result


def run(*args: object, env: dict | None = None) -> None:
    subprocess.run([str(arg) for arg in args], check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--state-root', required=True, type=Path)
    parser.add_argument('--cache-root', type=Path)
    parser.add_argument('--client', choices=['agents', 'claude'], default='agents')
    args = parser.parse_args()
    if sys.platform != 'win32' or platform.machine().lower() not in {'amd64', 'x86_64'}:
        raise SystemExit('此安裝入口只用於 Windows x64；macOS 依 INSTALL.md。')
    manifest = tomllib.loads((PACK / 'install.manifest.toml').read_text(encoding='utf-8'))
    state = args.state_root.expanduser().resolve()
    cache = (args.cache_root or state / 'tools').expanduser().resolve()
    entry = args.workspace.expanduser().resolve() / f'.{args.client}' / 'skills' / 'video-use'
    if state.is_relative_to(entry.parent) or cache.is_relative_to(entry.parent):
        raise ValueError('狀態與工具快取必須位於技能掃描目錄外')
    receipt = state / ('installation-' + sha(str(entry).encode())[:16] + '.json')
    prior = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
    if entry.exists() or entry.is_symlink():
        if not prior or entry.is_symlink() or getattr(entry, 'is_junction', lambda: False)() or source_hashes(entry) != prior['source_hashes']:
            raise ValueError('技能目錄含未知或修改內容，停止安裝')
        if sha((entry / 'toolbox-runtime.json').read_bytes()) != prior['descriptor_sha256']:
            raise ValueError('技能 runtime 設定被修改')
    tools = {}
    for name, asset in manifest['windows']['assets'].items():
        archive = download(asset['url'], asset['sha256'], cache / asset['archive'])
        unpack_tool(archive, cache / name)
        tools[name] = cache / name / asset['executable']
    if subprocess.check_output([str(tools['python']), '--version'], text=True).strip() != 'Python 3.12.14':
        raise ValueError('Python 版本不符')
    if subprocess.check_output([str(tools['uv']), '--version'], text=True).split()[:2] != ['uv', '0.12.7']:
        raise ValueError('uv 版本不符')
    release = manifest['release']
    archive = download(release['release_asset_url'], release['release_asset_sha256'], cache / 'video-use.tar.gz')
    version = manifest['compatibility_overlay']['sha256'][:16]
    component = state / 'components' / ('video-use-v0.1.1-' + version)
    with tempfile.TemporaryDirectory(prefix='video-use-install-') as temp:
        prepared = Path(temp) / 'source'
        prepare(archive, prepared)
        hashes = source_hashes(prepared)
        if component.exists():
            if component.is_symlink() or getattr(component, 'is_junction', lambda: False)() or source_hashes(component, build_artifacts=True) != hashes:
                raise ValueError('已存在的 component 含修改，停止')
        else:
            shutil.copytree(prepared, component)
        if prior and prior['source_hashes'] != hashes:
            raise ValueError('版本不同；請先於新的工作區驗證更新，不覆寫現有入口')
        uv = tools['uv']
        python = component / '.venv/Scripts/python.exe'
        asr = state / 'asr'
        ckip = state / 'ckip'
        environment = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                           HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        environment['PATH'] = os.pathsep.join([str(tools['ffmpeg'].parent), str(uv.parent), environment.get('PATH', '')])
        run(uv, 'sync', '--frozen', '--project', component, '--python', tools['python'], env=environment)
        run(uv, 'pip', 'install', '--require-hashes', '--python', python, '-r', component / 'requirements/opencc-windows.lock', env=environment)
        for root, lock in [(asr, 'asr-runtime-windows.lock'), (ckip, 'ckip-runtime-windows.lock')]:
            runtime_python = root / 'runtime/Scripts/python.exe'
            if not runtime_python.exists():
                run(uv, 'venv', '--python', tools['python'], root / 'runtime', env=environment)
            if subprocess.check_output([str(runtime_python), '--version'], text=True).strip() != 'Python 3.12.14':
                raise ValueError('現有 runtime Python 版本不符')
            run(uv, 'pip', 'sync', '--require-hashes', '--strict', '--python', runtime_python, component / 'requirements' / lock, env=environment)
        run(python, '-c', 'from opencc import OpenCC; assert OpenCC("s2twp").convert("软件") == "軟體"', env=environment)
        run(asr / 'runtime/Scripts/python.exe', '-c', 'import torch; from qwen_asr import Qwen3ASRModel, Qwen3ForcedAligner; assert torch.ones(2).sum().item() == 2', env=environment)
        run(ckip / 'runtime/Scripts/python.exe', '-c', 'from ckip_transformers.nlp import CkipWordSegmenter, CkipPosTagger', env=environment)
        run(python, '-m', 'unittest', 'discover', '-s', component / 'tests', '-p', 'test_*.py', env=environment)
        run(sys.executable, PACK / 'tests/run_public_smoke_test.py', '--video-use-dir', component,
            '--python-bin', python, '--ffmpeg-bin', tools['ffmpeg'], '--ffprobe-bin', tools['ffmpeg'].with_name('ffprobe.exe'), env=environment)
        descriptor = {'python': str(python), 'uv': str(uv), 'ffmpeg_bin': str(tools['ffmpeg'].parent),
                      'asr_root': str(asr), 'ckip_python': str(ckip / 'runtime/Scripts/python.exe'),
                      'ckip_cache': str(ckip / 'huggingface'), 'models_downloaded': False}
        descriptor_bytes = (json.dumps(descriptor, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        if not entry.exists():
            (prepared / 'toolbox-runtime.json').write_bytes(descriptor_bytes)
            entry.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.video-use-', dir=entry.parent) as staging:
                incoming = Path(staging) / 'video-use'
                shutil.copytree(prepared, incoming)
                incoming.rename(entry)
        elif sha(descriptor_bytes) != prior['descriptor_sha256']:
            raise ValueError('安裝位置與原設定不同，停止')
        state.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({'entry': str(entry), 'component': str(component), 'source_hashes': hashes,
            'descriptor_sha256': sha(descriptor_bytes), 'models_downloaded': False}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'result': 'verified_existing' if prior else 'installed', 'entry': str(entry), 'receipt': str(receipt)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
