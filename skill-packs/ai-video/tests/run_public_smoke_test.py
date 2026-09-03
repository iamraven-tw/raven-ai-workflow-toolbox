#!/usr/bin/env python3
"""以公開合成資料驗證正式字幕與影片渲染，不使用真人素材。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "synthetic-project"


def run(command: list[str], *, environment: dict[str, str] | None = None) -> None:
    """執行必要命令，任何一步失敗就保留原始錯誤並停止。"""
    subprocess.run(command, check=True, env=environment)


def require_file(file_path: Path, label: str) -> Path:
    """確認外部工具或必要檔案存在。"""
    resolved = file_path.expanduser().resolve()
    if not resolved.is_file():
        raise SystemExit(f"找不到{label}：{resolved}")
    return resolved


def prepare_workspace(work_root: Path) -> Path:
    """複製可公開散布的文字 fixture，媒體稍後在暫存目錄產生。"""
    edit_dir = work_root / "edit"
    if edit_dir.exists():
        raise SystemExit(f"測試目錄已存在，為避免覆寫而停止：{edit_dir}")
    shutil.copytree(FIXTURE_ROOT, edit_dir)
    return edit_dir


def generate_media(ffmpeg: Path, output: Path) -> None:
    """建立六秒純色畫面與固定音調，不含真人聲音或第三方媒體。"""
    run(
        [
            str(ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x203040:s=1280x720:r=30:d=6",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=6",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(output),
        ]
    )


def validate_output(ffprobe: Path, edit_dir: Path) -> None:
    """確認正式字幕 QA 與最終影片都真的產生。"""
    qa_path = edit_dir / "master.qa.json"
    subtitle_path = edit_dir / "master.srt"
    video_path = edit_dir / "final.mp4"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    if qa.get("hard_failures"):
        raise SystemExit(f"正式字幕 QA 失敗：{qa['hard_failures']}")
    subtitle_text = subtitle_path.read_text(encoding="utf-8")
    if "公開測試流程" not in subtitle_text:
        raise SystemExit("正式字幕沒有保留受保護片語「公開測試流程」。")
    probe = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of",
            "json",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(probe.stdout)
    if float(payload["format"]["duration"]) < 5.0:
        raise SystemExit("最終影片長度不足五秒。")
    video_streams = [
        item for item in payload["streams"] if item.get("codec_type") == "video"
    ]
    if not video_streams:
        raise SystemExit("最終輸出沒有影片串流。")
    if (video_streams[0].get("width"), video_streams[0].get("height")) != (1920, 1080):
        raise SystemExit("預覽輸出不是預期的 1920×1080。")
    if not any(item.get("codec_type") == "audio" for item in payload["streams"]):
        raise SystemExit("最終輸出沒有音訊串流。")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-use-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg-bin", type=Path, required=True)
    parser.add_argument("--ffprobe-bin", type=Path, required=True)
    parser.add_argument("--python-bin", type=Path)
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="指定空的新目錄以保留輸出；省略時使用並清除暫存目錄。",
    )
    args = parser.parse_args()

    video_use_dir = args.video_use_dir.expanduser().resolve()
    ffmpeg = require_file(args.ffmpeg_bin, "FFmpeg")
    ffprobe = require_file(args.ffprobe_bin, "FFprobe")
    python = require_file(
        args.python_bin or video_use_dir / ".venv" / "bin" / "python",
        "Video-Use Python",
    )
    require_file(video_use_dir / "helpers" / "build_subtitles.py", "字幕 helper")
    require_file(video_use_dir / "helpers" / "render.py", "渲染 helper")

    version = subprocess.check_output([str(python), "--version"], text=True).strip()
    if version != "Python 3.12.14":
        raise SystemExit(f"公開候選版需要 Python 3.12.14；目前是 {version}。")
    filter_help = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-h", "filter=subtitles"],
        check=True,
        capture_output=True,
        text=True,
    )
    if "Filter subtitles" not in filter_help.stdout:
        raise SystemExit("FFmpeg 沒有可用的 libass subtitles filter。")

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if args.work_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="ai-video-public-smoke-")
        work_root = Path(temporary.name)
    else:
        work_root = args.work_dir.expanduser().resolve()
        work_root.mkdir(parents=True, exist_ok=False)

    try:
        edit_dir = prepare_workspace(work_root)
        generate_media(ffmpeg, edit_dir / "take.mp4")
        environment = os.environ.copy()
        binary_dirs = [str(ffmpeg.parent), str(ffprobe.parent)]
        environment["PATH"] = os.pathsep.join(
            binary_dirs + [environment.get("PATH", "")]
        )
        run(
            [str(python), str(video_use_dir / "helpers" / "build_subtitles.py"), str(edit_dir)],
            environment=environment,
        )
        run(
            [
                str(python),
                str(video_use_dir / "helpers" / "render.py"),
                str(edit_dir / "edl.json"),
                "--preview",
                "--no-loudnorm",
                "--output",
                str(edit_dir / "final.mp4"),
            ],
            environment=environment,
        )
        validate_output(ffprobe, edit_dir)
        print("通過：公開合成素材完成正式字幕、渲染與輸出檢查。")
        if args.work_dir is not None:
            print(f"保留測試輸出：{work_root}")
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    main()
