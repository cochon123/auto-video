#!/usr/bin/env python3
"""Validate video assets against target specs (fps, resolution, codec)."""

import subprocess
import json
import sys
from pathlib import Path


def probe_video(path: Path) -> dict | None:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=r_frame_rate,width,height,codec_name,duration",
                "-of", "json", str(path),
            ],
            capture_output=True, text=True,
        )
        streams = json.loads(result.stdout).get("streams", [])
        return streams[0] if streams else None
    except Exception:
        return None


def parse_fps(fps_str: str) -> float:
    if "/" in fps_str:
        num, den = fps_str.split("/")
        return float(num) / float(den)
    return float(fps_str)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <media_dir> [fps] [width] [height]")
        sys.exit(1)

    media_dir = Path(sys.argv[1])
    fps_target = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    width_target = int(sys.argv[3]) if len(sys.argv) > 3 else 1920
    height_target = int(sys.argv[4]) if len(sys.argv) > 4 else 1080
    video_exts = {".mp4", ".mov", ".avi", ".webm"}

    if not media_dir.is_dir():
        print(f"Error: {media_dir} is not a directory")
        sys.exit(1)

    issues_found = False

    for f in sorted(media_dir.iterdir()):
        if f.suffix.lower() not in video_exts:
            continue

        info = probe_video(f)
        if not info:
            print(f"  X {f.name}: cannot probe")
            issues_found = True
            continue

        w = info.get("width", 0)
        h = info.get("height", 0)
        codec = info.get("codec_name", "?")
        fps = parse_fps(info.get("r_frame_rate", "0/1"))
        dur = float(info.get("duration", 0))

        tags = []
        ok = True

        if abs(fps - fps_target) > 1:
            tags.append(f"{fps:.0f}fps X")
            ok = False
        else:
            tags.append(f"{fps:.0f}fps OK")

        if w != width_target or h != height_target:
            tags.append(f"{w}x{h} X")
            ok = False
        else:
            tags.append(f"{w}x{h} OK")

        if codec != "h264":
            tags.append(f"{codec} X")
            ok = False
        else:
            tags.append(f"{codec} OK")

        if not ok:
            issues_found = True

        status = "OK" if ok else " X"
        print(f"{status} {f.name}: {' | '.join(tags)} | {dur:.1f}s")

    sys.exit(1 if issues_found else 0)


if __name__ == "__main__":
    main()
