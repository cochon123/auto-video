#!/usr/bin/env python3
"""Extract word-level timestamps from audio using Whisper (transformers, faster-whisper, or openai-whisper)."""

import argparse
import json
import sys
from pathlib import Path


def _normalize_language(lang: str) -> str:
    code_to_name = {
        "en": "english", "en-us": "english", "en-gb": "english",
        "fr": "french", "fr-fr": "french",
        "de": "german", "es": "spanish", "it": "italian",
        "pt": "portuguese", "pt-br": "portuguese",
        "ja": "japanese", "zh": "chinese", "ko": "korean",
        "ru": "russian", "ar": "arabic", "hi": "hindi",
        "nl": "dutch", "pl": "polish", "tr": "turkish",
        "sv": "swedish", "da": "danish", "fi": "finnish",
        "th": "thai", "uk": "ukrainian", "vi": "vietnamese",
        "el": "greek", "cs": "czech", "ro": "romanian",
        "hu": "hungarian", "ta": "tamil", "no": "norwegian",
    }
    lower = lang.lower().strip()
    if lower in code_to_name:
        return code_to_name[lower]
    return lower


def get_timestamps_transformers(audio_path: str, language: str = "fr", model_size: str = "base") -> dict:
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    model_name = f"openai/whisper-{model_size}"
    language = _normalize_language(language)
    print(f"  Loading {model_name}...", flush=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name).to(device)
    model.eval()

    import soundfile as sf
    import numpy as np
    waveform_np, sample_rate = sf.read(audio_path)
    if waveform_np.ndim > 1:
        waveform_np = waveform_np.mean(axis=1)
    if sample_rate != 16000:
        import torchaudio
        waveform = torch.from_numpy(waveform_np).unsqueeze(0).float()
        waveform = torchaudio.functional.resample(waveform, sample_rate, 16000)
        waveform_np = waveform.squeeze().numpy()
        sample_rate = 16000

    chunk_duration_s = 30
    chunk_samples = 16000 * chunk_duration_s
    total_samples = len(waveform_np)
    all_words = []
    all_segments = []

    for start in range(0, total_samples, chunk_samples):
        end = min(start + chunk_samples, total_samples)
        chunk = waveform_np[start:end]
        input_features = processor(chunk, sampling_rate=16000, return_tensors="pt").input_features.to(device)

        with torch.no_grad():
            predicted_ids = model.generate(
                input_features,
                language=language,
                task="transcribe",
                return_timestamps="word",
            )

        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        offset_s = start / 16000

        chunk_words = []
        for token_id in predicted_ids[0]:
            token = processor.decode([token_id.item()])
            ts = processor.decode([token_id.item()], output_offsets=True)
            if "offsets" in ts and ts["offsets"]:
                for off in ts["offsets"]:
                    w = off.get("text", "").strip()
                    if w:
                        s = round(off["start"] + offset_s, 3)
                        e = round(off["end"] + offset_s, 3)
                        chunk_words.append({"word": w, "start": s, "end": e})

        if not chunk_words and transcription.strip():
            chunk_words = [{"word": transcription.strip(), "start": round(offset_s, 3), "end": round(end / 16000, 3)}]

        all_words.extend(chunk_words)
        if chunk_words:
            all_segments.append({
                "start": chunk_words[0]["start"],
                "end": chunk_words[-1]["end"],
                "text": transcription.strip(),
            })

    return {"audio": audio_path, "language": language, "words": all_words, "segments": all_segments}


def get_timestamps_faster_whisper(audio_path: str, language: str = "fr", model_size: str = "base") -> dict:
    from faster_whisper import WhisperModel
    device = "cuda"
    try:
        import torch
        if not torch.cuda.is_available():
            device = "cpu"
    except ImportError:
        device = "cpu"
    model = WhisperModel(model_size, device=device, compute_type="int8" if device == "cpu" else "float16")
    segments, info = model.transcribe(audio_path, language=language, word_timestamps=True)
    words = []
    all_segments = []
    for segment in segments:
        all_segments.append({"start": round(segment.start, 3), "end": round(segment.end, 3), "text": segment.text})
        for w in segment.words:
            words.append({"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)})
    return {"audio": audio_path, "language": info.language, "words": words, "segments": all_segments}


def get_timestamps_openai_whisper(audio_path: str, language: str = "fr", model_size: str = "base") -> dict:
    import whisper
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path, language=language, word_timestamps=True)
    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            words.append({"word": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)})
    return {"audio": audio_path, "language": language, "words": words, "segments": result.get("segments", [])}


def get_timestamps(audio_path: str, language: str = "fr", model_size: str = "base") -> dict:
    errors = []

    try:
        from faster_whisper import WhisperModel
        return get_timestamps_faster_whisper(audio_path, language, model_size)
    except ImportError:
        pass
    except Exception as exc:
        errors.append(f"[faster-whisper] {exc}")

    try:
        import whisper
        return get_timestamps_openai_whisper(audio_path, language, model_size)
    except ImportError:
        pass
    except Exception as exc:
        errors.append(f"[openai-whisper] {exc}")

    try:
        return get_timestamps_transformers(audio_path, language, model_size)
    except ImportError:
        pass
    except Exception as exc:
        errors.append(f"[transformers] {exc}")

    print(
        "[timestamps] All whisper backends failed:\n"
        + "\n".join(f"  {e}" for e in errors)
        + "\nInstall one of:\n"
        "  pip install faster-whisper\n"
        "  pip install openai-whisper\n"
        "  pip install torch torchaudio transformers",
        file=sys.stderr,
    )
    sys.exit(1)


def process_directory(audio_dir: str, output_path: str, language: str = "fr", model_size: str = "base") -> dict:
    audio_dir = Path(audio_dir)
    audio_exts = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
    audio_files = sorted([f for f in audio_dir.iterdir() if f.suffix.lower() in audio_exts])
    if not audio_files:
        print(f"[timestamps] No audio files found in {audio_dir}", file=sys.stderr)
        return {}
    all_timestamps = {}
    for audio_file in audio_files:
        scene_id = audio_file.stem
        print(f"Processing {scene_id}...")
        ts = get_timestamps(str(audio_file), language, model_size)
        all_timestamps[scene_id] = ts
        word_count = len(ts.get("words", []))
        duration = ts.get("segments", [{}])[-1].get("end", 0) if ts.get("segments") else 0
        print(f"  {word_count} words, {duration:.1f}s")
    with open(output_path, "w") as f:
        json.dump(all_timestamps, f, indent=2, ensure_ascii=False)
    print(f"Timestamps saved to: {output_path}")
    return all_timestamps


def main():
    parser = argparse.ArgumentParser(description="Extract word-level timestamps from audio")
    parser.add_argument("--audio", help="Single audio file to process")
    parser.add_argument("--audio-dir", help="Directory of audio files (one per scene)")
    parser.add_argument("--output", default="timestamps.json", help="Output JSON path")
    parser.add_argument("--language", default=None, help="Language code (fr, en, etc.)")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny, base, small, medium, large)")
    parser.add_argument("--config", default="~/.config/auto-video/config.yaml")
    args = parser.parse_args()

    language = args.language
    config_path = args.config.replace("~", str(Path.home())) if args.config else None
    if config_path:
        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
            language = language or config.get("tts", {}).get("language", "fr")
        except (ImportError, FileNotFoundError):
            pass
    if not language:
        language = "fr"

    if args.audio_dir:
        process_directory(args.audio_dir, args.output, language, args.model)
    elif args.audio:
        ts = get_timestamps(args.audio, language, args.model)
        with open(args.output, "w") as f:
            json.dump(ts, f, indent=2, ensure_ascii=False)
        print(f"Timestamps saved to: {args.output}")
        print(f"  {len(ts.get('words', []))} words detected")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
