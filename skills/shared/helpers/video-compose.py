#!/usr/bin/env python3
"""Video composition helper: assemble final video from scenario + assets + audio."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def get_audio_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def build_scene_clip_ffmpeg(
    media_path: str,
    audio_path: str,
    output_path: str,
    duration: float,
    ken_burns: str = "zoom_in",
    resolution: str = "1920x1080",
    fps: int = 30,
) -> str:
    ext = Path(media_path).suffix.lower()
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    w, h = resolution.split("x")
    total_frames = max(int(duration * fps), 1)

    if ext in video_exts:
        cmd = [
            "ffmpeg", "-y",
            "-i", media_path, "-i", audio_path,
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(fps),
            "-shortest",
            output_path,
        ]
    else:
        if ken_burns == "zoom_in":
            z_expr = "min(zoom+0.001,1.5)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif ken_burns == "zoom_out":
            z_expr = "if(eq(on\\,0)\\,1.5\\,max(zoom-0.001\\,1))"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif ken_burns == "pan_left":
            z_expr = "1"
            x_expr = f"iw*({total_frames}-on)/{total_frames}"
            y_expr = "ih/2"
        elif ken_burns == "pan_right":
            z_expr = "1"
            x_expr = f"iw*on/{total_frames}"
            y_expr = "ih/2"
        else:
            z_expr = "min(zoom+0.001,1.3)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"

        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
            f"setsar=1,"
            f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}'"
            f":d={total_frames}:s={w}x{h}:fps={fps}"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", media_path, "-i", audio_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"[ffmpeg] Error building clip:\n{result.stderr[-800:]}", file=sys.stderr)
        raise RuntimeError(result.stderr)
    return output_path


def build_remotion_scene(
    composition: str,
    props: dict,
    output_path: str,
    project_path: str,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
) -> str:
    props_file = Path(output_path).parent / f"{composition}_props.json"
    with open(props_file, "w") as f:
        json.dump(props, f)
    duration_frames = props.get("durationInFrames", 90)
    cmd = [
        "npx", "remotion", "render",
        str(Path(project_path) / "index.ts"),
        composition,
        "--props", str(props_file),
        "--output", output_path,
        "--fps", str(fps),
        "--width", str(width),
        "--height", str(height),
        "--duration", str(duration_frames),
        "--codec", "h264", "--crf", "18",
        "--overwrite",
    ]
    result = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=600)
    if props_file.exists():
        props_file.unlink()
    if result.returncode != 0:
        raise RuntimeError(f"Remotion render failed: {result.stderr}")
    return output_path


def concat_with_transitions(clips: list[str], output_path: str, transition: str = "fade", transition_duration: float = 0.5) -> str:
    if len(clips) == 1:
        import shutil
        shutil.copy2(clips[0], output_path)
        return output_path

    if len(clips) == 2:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clips[0]],
            capture_output=True, text=True
        )
        offset = float(probe.stdout.strip()) - transition_duration
        cmd = [
            "ffmpeg", "-y", "-i", clips[0], "-i", clips[1],
            "-filter_complex",
            f"[0:v][1:v]xfade=transition={transition}:duration={transition_duration}:offset={offset},"
            f"[0:a][1:a]acrossfade=d={transition_duration}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return output_path

    concat_file = Path(output_path).parent / "concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    concat_file.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"Concat failed: {result.stderr}")
    return output_path


def compose_ffmpeg(scenario: dict, media_dir: str, audio_dir: str, output_path: str) -> str:
    media_dir = Path(media_dir)
    audio_dir = Path(audio_dir)
    temp_dir = Path(output_path).parent / "temp_clips"
    temp_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    for scene in scenario.get("scenes", []):
        scene_id = scene.get("scene_id", "unknown")
        audio_file = audio_dir / f"{scene_id}.mp3"
        if not audio_file.exists():
            for ext in [".wav", ".m4a", ".ogg"]:
                alt = audio_dir / f"{scene_id}{ext}"
                if alt.exists():
                    audio_file = alt
                    break

        if not audio_file.exists():
            print(f"[compose] No audio for {scene_id}, skipping", file=sys.stderr)
            continue

        duration = get_audio_duration(str(audio_file))
        visual = scene.get("visual", {})
        render_method = visual.get("render_method", "ffmpeg")

        if render_method == "remotion":
            print(f"[compose] Remotion scene {scene_id} — use remotion method instead", file=sys.stderr)
            continue

        media_files = list(media_dir.glob(f"{scene_id}_*")) + list(media_dir.glob(f"*{scene_id}*"))
        media_files = [f for f in media_files if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"}]
        if not media_files:
            all_media = list(media_dir.iterdir())
            media_files = [f for f in all_media if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"}]
            if not media_files:
                print(f"[compose] No media for {scene_id}", file=sys.stderr)
                continue

        media_path = str(media_files[0])
        clip_path = str(temp_dir / f"{scene_id}.mp4")
        ken_burns = visual.get("ken_burns", "zoom_in")

        try:
            build_scene_clip_ffmpeg(media_path, str(audio_file), clip_path, duration, ken_burns)
            clips.append(clip_path)
        except RuntimeError as exc:
            print(f"[compose] Failed clip for {scene_id}: {exc}", file=sys.stderr)

    if not clips:
        raise RuntimeError("No clips generated")

    transition = scenario.get("default_transition", "fade")
    concat_with_transitions(clips, output_path, transition)
    for clip in clips:
        Path(clip).unlink(missing_ok=True)
    temp_dir.rmdir()
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Compose video from scenario + assets")
    parser.add_argument("--method", choices=["ffmpeg", "remotion"], default="ffmpeg")
    parser.add_argument("--scenario", required=True, help="Path to scenario JSON")
    parser.add_argument("--audio-dir", required=True, help="Directory with per-scene audio")
    parser.add_argument("--timestamps", help="Path to timestamps JSON")
    parser.add_argument("--media-dir", required=True, help="Directory with media assets")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument("--config", default=None)
    parser.add_argument("--resolution", default="1920x1080")
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    with open(args.scenario) as f:
        scenario = json.load(f)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if args.config:
        try:
            import yaml
            with open(args.config) as f:
                config = yaml.safe_load(f) or {}
        except (ImportError, FileNotFoundError):
            pass

    remotion_cfg = config.get("remotion", {})
    project_path = remotion_cfg.get("project_path", str(Path.home() / ".config" / "auto-video" / "remotion"))

    if args.method == "remotion":
        for scene in scenario.get("scenes", []):
            visual = scene.get("visual", {})
            if visual.get("render_method") != "remotion":
                continue
            scene_id = scene.get("scene_id", "unknown")
            composition = visual.get("composition", "Intro")
            props = visual.get("props", {})
            scene_output = str(output_path.parent / f"{scene_id}.mp4")
            try:
                build_remotion_scene(composition, props, scene_output, project_path, args.fps)
                print(f"Rendered: {scene_output}")
            except RuntimeError as exc:
                print(f"[remotion] Failed {scene_id}: {exc}", file=sys.stderr)
        print("Remotion scenes rendered. Use ffmpeg method to combine with non-remotion scenes.")
    else:
        try:
            compose_ffmpeg(scenario, args.media_dir, args.audio_dir, str(output_path))
            print(f"Video saved to: {output_path}")
        except RuntimeError as exc:
            print(f"[compose] Failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
