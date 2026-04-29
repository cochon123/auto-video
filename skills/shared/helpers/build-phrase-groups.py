#!/usr/bin/env python3
"""Build phrase_groups with real timestamps from phrase_texts + word-level timestamps.

Pipeline step: runs AFTER TTS + timestamp extraction, BEFORE montage.

1. Reads scenario.json (visual pass output — has phrase_texts, NO timestamps)
2. Reads timestamps.json (word-level from Whisper or native TTS)
3. For each scene, matches phrase_texts to word timestamps
4. Outputs updated scenario.json with full phrase_groups (text + start + end)
5. Calculates scene start_s/end_s from actual audio durations
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


def find_phrase_in_words(
    phrase_text: str,
    words: list[dict],
    search_start: int = 0,
) -> tuple[float, float] | None:
    p_words = norm_words(phrase_text)
    if not p_words:
        return None

    first_word = p_words[0]
    last_word = p_words[-1] if len(p_words) > 1 else first_word
    w_norms = [norm(w["word"]) for w in words]

    first_idx = None
    for i in range(search_start, len(w_norms)):
        if w_norms[i] == first_word or SequenceMatcher(None, w_norms[i], first_word).ratio() > 0.7:
            first_idx = i
            break

    if first_idx is None:
        return None

    if first_word == last_word:
        last_idx = first_idx
    else:
        search_end = min(first_idx + len(p_words) + 5, len(w_norms))
        last_idx = None
        for i in range(search_end - 1, first_idx, -1):
            if w_norms[i] == last_word or SequenceMatcher(None, w_norms[i], last_word).ratio() > 0.7:
                last_idx = i
                break
        if last_idx is None:
            last_idx = min(first_idx + len(p_words) - 1, len(words) - 1)

    return words[first_idx]["start"], words[last_idx]["end"]


def build_scene_phrase_groups(
    scene: dict,
    word_data: list[dict],
    audio_duration: float | None = None,
) -> tuple[list[dict], int, int]:
    phrase_texts = scene.get("phrase_texts", [])
    if not phrase_texts:
        return [], 0, 0

    if not word_data:
        dur = audio_duration or 10.0
        n = len(phrase_texts)
        chunk = dur / n
        groups = []
        for i, text in enumerate(phrase_texts):
            groups.append({"text": text, "start": round(i * chunk, 3), "end": round((i + 1) * chunk, 3)})
        return groups, 0, n

    phrase_groups = []
    search_start = 0
    matched = 0
    unmatched = 0

    for text in phrase_texts:
        result = find_phrase_in_words(text, word_data, search_start)
        if result:
            start_t, end_t = result
            phrase_groups.append({"text": text, "start": round(start_t, 3), "end": round(end_t, 3)})
            first_w = norm_words(text)[0] if norm_words(text) else ""
            w_norms = [norm(w["word"]) for w in word_data]
            for i in range(search_start, len(w_norms)):
                if w_norms[i] == first_w or SequenceMatcher(None, w_norms[i], first_w).ratio() > 0.7:
                    search_start = min(i + max(len(norm_words(text)), 1), len(word_data))
                    break
            matched += 1
        else:
            unmatched += 1
            if phrase_groups:
                prev_end = phrase_groups[-1]["end"]
            else:
                prev_end = 0.0
            remaining = len(phrase_texts) - len(phrase_groups)
            remaining_time = (audio_duration or prev_end + 5.0) - prev_end
            chunk = remaining_time / max(remaining, 1)
            phrase_groups.append({"text": text, "start": round(prev_end, 3), "end": round(prev_end + chunk, 3)})

    return phrase_groups, matched, unmatched


def main():
    parser = argparse.ArgumentParser(description="Build phrase_groups from phrase_texts + word timestamps")
    parser.add_argument("--scenario", required=True, help="Path to scenario.json (visual pass output)")
    parser.add_argument("--timestamps", required=True, help="Path to timestamps.json (Whisper or native TTS)")
    parser.add_argument("--audio-dir", help="Audio directory (to measure actual durations)")
    parser.add_argument("--dry-run", action="store_true", help="Print result without writing")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    with open(args.scenario) as f:
        scenario = json.load(f)

    with open(args.timestamps) as f:
        timestamps = json.load(f)

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
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio_file)],
                        capture_output=True, text=True, timeout=5,
                    )
                    try:
                        actual_durations[sid] = float(probe.stdout.strip())
                    except ValueError:
                        pass
                    break

    total_matched = 0
    total_unmatched = 0
    cumulative = 0.0

    for scene in scenario.get("scenes", []):
        sid = scene.get("scene_id", "")
        word_data = timestamps.get(sid, {}).get("words", [])
        audio_dur = actual_durations.get(sid)

        phrase_groups, matched, unmatched = build_scene_phrase_groups(scene, word_data, audio_dur)
        total_matched += matched
        total_unmatched += unmatched

        dur = audio_dur or 0.0
        scene["start_s"] = round(cumulative, 3)
        scene["end_s"] = round(cumulative + dur, 3)
        cumulative += dur

        scene.pop("phrase_texts", None)
        if phrase_groups:
            scene["phrase_groups"] = phrase_groups

        if args.verbose:
            print(f"\n{sid} ({dur:.2f}s, matched: {matched}, fallback: {unmatched}):")
            for i, pg in enumerate(phrase_groups):
                print(f"  [{i:2d}] {pg['start']:7.2f}-{pg['end']:7.2f}s  \"{pg['text'][:55]}\"")

    scenario["total_duration_s"] = round(cumulative, 2)

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
        print(f"  {total_matched} matched | {total_unmatched} proportional fallback")
        print(f"  Total duration: {scenario['total_duration_s']}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
