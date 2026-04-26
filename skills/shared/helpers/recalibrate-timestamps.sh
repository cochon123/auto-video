#!/usr/bin/env python3
"""Recalibrate phrase_group timestamps using Whisper word-level timestamps.

After TTS generation and Whisper transcription, this script:
1. Reads scenario.json (AI-estimated phrase_groups)
2. Reads timestamps.json (Whisper word-level timestamps from actual audio)
3. Matches each phrase_group text to Whisper words
4. Replaces AI-estimated timestamps with actual timestamps (scene-relative)
5. Updates scenario.json with correct scene timing from actual audio durations
"""

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


def norm(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower().strip())


def norm_words(text: str) -> list[str]:
    return norm(text).split()


def find_phrase_in_whisper(
    phrase_text: str,
    whisper_words: list[dict],
    search_start: int = 0,
) -> tuple[float, float] | None:
    """Find a phrase's start/end time in whisper word list.

    Strategy: take first and last content word from phrase,
    find them sequentially in whisper words from search_start.
    """
    p_words = norm_words(phrase_text)
    if not p_words:
        return None

    first_word = p_words[0]
    last_word = p_words[-1]
    w_norms = [norm(w["word"]) for w in whisper_words]

    # Find first word match
    first_idx = None
    for i in range(search_start, len(w_norms)):
        if w_norms[i] == first_word:
            first_idx = i
            break
        if SequenceMatcher(None, w_norms[i], first_word).ratio() > 0.7:
            first_idx = i
            break

    if first_idx is None:
        return None

    # Find last word match, searching forward from first_idx
    search_end = min(first_idx + len(p_words) + 5, len(w_norms))
    last_idx = None
    for i in range(search_end - 1, first_idx - 1, -1):
        if w_norms[i] == last_word:
            last_idx = i
            break
        if SequenceMatcher(None, w_norms[i], last_word).ratio() > 0.7:
            last_idx = i
            break

    if last_idx is None:
        last_idx = min(first_idx + len(p_words) - 1, len(whisper_words) - 1)

    start_time = whisper_words[first_idx]["start"]
    end_time = whisper_words[last_idx]["end"]

    return start_time, end_time


def recalibrate_scene(
    scene: dict,
    whisper_data: dict,
    audio_duration: float | None = None,
) -> tuple[dict, int, int]:
    """Recalibrate one scene's phrase_groups using whisper timestamps."""
    phrase_groups = scene.get("phrase_groups", [])
    if not phrase_groups:
        return scene, 0, 0

    whisper_words = whisper_data.get("words", [])
    scene_start_s = scene.get("start_s", 0.0)
    matched_count = 0
    unmatched_count = 0

    if not whisper_words:
        if audio_duration is not None and audio_duration > 0:
            new_groups = proportional_rescale(phrase_groups, audio_duration, scene_start_s)
            scene["phrase_groups"] = new_groups
            return scene, 0, len(phrase_groups)
        return scene, 0, len(phrase_groups)

    new_groups = []
    search_start = 0

    for pg in phrase_groups:
        result = find_phrase_in_whisper(pg["text"], whisper_words, search_start)

        if result:
            start_t, end_t = result
            new_groups.append({
                "text": pg["text"],
                "start": round(start_t, 3),
                "end": round(end_t, 3),
                "_matched": True,
            })
            first_word = norm_words(pg["text"])[0] if norm_words(pg["text"]) else ""
            w_norms = [norm(w["word"]) for w in whisper_words]
            for i in range(search_start, len(w_norms)):
                if w_norms[i] == first_word or SequenceMatcher(None, w_norms[i], first_word).ratio() > 0.7:
                    search_start = min(i + max(len(norm_words(pg["text"])), 1), len(whisper_words))
                    break
            matched_count += 1
        else:
            new_groups.append({
                "text": pg["text"],
                "start": pg["start"],
                "end": pg["end"],
                "_matched": False,
            })
            unmatched_count += 1

    # Fix unmatched groups: rescale their timestamps to be scene-relative
    if unmatched_count > 0 and audio_duration is not None:
        for pg in new_groups:
            if not pg.get("_matched", False):
                old_start = pg["start"] - scene_start_s if pg["start"] >= scene_start_s else pg["start"]
                old_end = pg["end"] - scene_start_s if pg["end"] >= scene_start_s else pg["end"]
                pg["start"] = round(max(0.0, old_start), 3)
                pg["end"] = round(min(audio_duration, old_end), 3)

    # Remove internal markers
    for pg in new_groups:
        pg.pop("_matched", None)

    scene["phrase_groups"] = new_groups
    return scene, matched_count, unmatched_count


def proportional_rescale(
    phrase_groups: list[dict],
    audio_duration: float,
    scene_start_s: float,
) -> list[dict]:
    """Fallback: proportionally rescale timestamps to match actual audio duration."""
    if not phrase_groups:
        return phrase_groups

    first_start = phrase_groups[0].get("start", 0.0)
    if first_start >= scene_start_s and scene_start_s > 0:
        old_span = phrase_groups[-1]["end"] - scene_start_s
    else:
        old_span = phrase_groups[-1]["end"] - phrase_groups[0]["start"]

    if old_span <= 0:
        old_span = audio_duration

    ratio = audio_duration / old_span
    offset = scene_start_s if first_start >= scene_start_s and scene_start_s > 0 else first_start

    result = []
    for pg in phrase_groups:
        new_start = (pg["start"] - offset) * ratio
        new_end = (pg["end"] - offset) * ratio
        result.append({
            "text": pg["text"],
            "start": round(max(0.0, new_start), 3),
            "end": round(min(audio_duration, new_end), 3),
        })
    return result


def recalculate_scene_timing(scenario: dict, actual_durations: dict[str, float]) -> dict:
    """Recalculate all scene start_s/end_s based on actual audio durations."""
    cumulative = 0.0
    for scene in scenario.get("scenes", []):
        sid = scene.get("scene_id", "")
        ai_dur = scene.get("end_s", 0) - scene.get("start_s", 0)
        actual_dur = actual_durations.get(sid, ai_dur)

        scene["start_s"] = round(cumulative, 3)
        scene["end_s"] = round(cumulative + actual_dur, 3)
        cumulative += actual_dur

    scenario["total_duration_s"] = round(cumulative, 2)
    return scenario


def main():
    parser = argparse.ArgumentParser(
        description="Recalibrate phrase_groups with Whisper timestamps"
    )
    parser.add_argument("--scenario", required=True, help="Path to scenario.json")
    parser.add_argument("--timestamps", required=True, help="Path to timestamps.json")
    parser.add_argument("--audio-dir", help="Audio directory (to measure actual durations)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    with open(args.scenario) as f:
        scenario = json.load(f)

    with open(args.timestamps) as f:
        timestamps = json.load(f)

    # Measure actual audio durations
    actual_durations = {}
    if args.audio_dir:
        import subprocess

        audio_dir = Path(args.audio_dir)
        for scene in scenario.get("scenes", []):
            sid = scene.get("scene_id", "")
            for ext in [".wav", ".mp3", ".m4a"]:
                audio_file = audio_dir / f"{sid}{ext}"
                if audio_file.exists():
                    probe = subprocess.run(
                        [
                            "ffprobe", "-v", "error",
                            "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(audio_file),
                        ],
                        capture_output=True, text=True, timeout=5,
                    )
                    try:
                        actual_durations[sid] = float(probe.stdout.strip())
                    except ValueError:
                        pass
                    break

    # Recalibrate each scene
    total_matched = 0
    total_unmatched = 0

    for scene in scenario.get("scenes", []):
        sid = scene.get("scene_id", "")
        whisper_data = timestamps.get(sid, {})
        audio_dur = actual_durations.get(sid)

        scene, matched, unmatched = recalibrate_scene(scene, whisper_data, audio_dur)
        total_matched += matched
        total_unmatched += unmatched

        if args.verbose:
            print(f"\n{sid} (audio: {audio_dur:.2f}s, matched: {matched}, fallback: {unmatched}):")
            for i, pg in enumerate(scene.get("phrase_groups", [])):
                print(f"  [{i:2d}] {pg['start']:7.2f}-{pg['end']:7.2f}s  \"{pg['text'][:55]}\"")

    # Recalculate absolute scene timing from actual durations
    if actual_durations:
        scenario = recalculate_scene_timing(scenario, actual_durations)
        if args.verbose:
            print(f"\nTotal duration: {scenario['total_duration_s']}s")

    if args.dry_run:
        print(json.dumps(scenario, indent=2, ensure_ascii=False))
    else:
        backup = Path(args.scenario).with_suffix(".json.bak")
        if not backup.exists():
            import shutil
            shutil.copy2(args.scenario, backup)
        with open(args.scenario, "w") as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)
        print(f"Updated {args.scenario}")
        print(f"  {total_matched} matched | {total_unmatched} fallback (proportional)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
