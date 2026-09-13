#!/usr/bin/env python3
"""建立不含快取的獨立 Preview 快照、逐檔雜湊與 ZIP；不發布。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL = {"AGENTS.md", "CLAUDE.md", "INSTALL.md", "LICENSE", "README.md",
             "THIRD_PARTY_NOTICES.md", "install.manifest.toml", "docs", "scripts", "skills", "template", "tests"}
EXCLUDES = {"__pycache__", ".pytest_cache", ".git", ".local", "node_modules", "dist", ".astro", ".DS_Store"}


def source_files(root: Path) -> list[Path]:
    files = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in [*dirs, *names]:
            path = base / name
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise ValueError(f"發行來源不得含連結：{path.relative_to(root)}")
        dirs[:] = sorted(name for name in dirs if name not in EXCLUDES and (base != root or name in TOP_LEVEL))
        for name in sorted(names):
            path = base / name
            if name in EXCLUDES or path.suffix in {".pyc", ".pyo"} or (base == root and name not in TOP_LEVEL):
                continue
            if name.startswith(".env") or name in {".dev.vars", "credentials.json", "secrets.json"}:
                raise ValueError(f"發行來源疑似含秘密檔案：{path.relative_to(root)}")
            files.append(path)
    return sorted(files)


def prepare(root: Path, output: Path) -> dict:
    root = root.resolve(strict=True)
    output = output.absolute()
    for parent in (output, *output.parents):
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            raise ValueError("輸出路徑不得包含連結")
    output = output.resolve()
    if output.is_relative_to(root) or root.is_relative_to(output) or output.exists():
        raise ValueError("輸出必須是來源以外、尚不存在的新目錄")
    files = source_files(root)
    with (root / "install.manifest.toml").open("rb") as handle:
        version = tomllib.load(handle)["installation"]["candidate_version"]
    if not isinstance(version, str) or not all(c in "0123456789.-abcdefghijklmnopqrstuvwxyz" for c in version):
        raise ValueError("版本名稱不安全")
    snapshot = output / "website-building"
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for path in files:
        relative = path.relative_to(root)
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        content = destination.read_bytes()
        records.append({"path": relative.as_posix(), "size": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    # 驗證獨立快照，而不是依賴原 repository 外層文件。
    validated = subprocess.run([sys.executable, "-B", str(snapshot / "tests/validate_package.py")],
                               cwd=snapshot, capture_output=True, text=True, encoding="utf-8")
    if validated.returncode:
        raise ValueError("快照驗證失敗；保留輸出供檢查：" + validated.stdout + validated.stderr)
    archive_path = output / f"website-building-{version}-preview.zip"
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for record in records:
            entry = zipfile.ZipInfo("website-building/" + record["path"], date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, (snapshot / record["path"]).read_bytes())
    archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    report = {"version": version, "channel": "preview", "published": False,
              "archive": archive_path.name, "archive_sha256": archive_hash,
              "file_count": len(records), "files": records, "static_validation": "passed"}
    (output / "files.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text(f"{archive_hash}  {archive_path.name}\n", encoding="utf-8")
    return {key: value for key, value in report.items() if key != "files"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-write", action="store_true")
    args = parser.parse_args()
    if not args.confirm_write:
        parser.error("建立本機發布產物需要 --confirm-write；不會 push 或發布")
    print(json.dumps(prepare(ROOT, Path(args.output_dir)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
