#!/usr/bin/env python3
"""Text-to-speech helper using OmniVoice (local GPU, 600+ languages, voice design)."""

import argparse
import json
import sys
from pathlib import Path

_model = None


def _get_model():
    global _model
    if _model is None:
        import torch
        from omnivoice import OmniVoice
        print("[omnivoice] Loading model...", flush=True)
        _model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16)
        print(f"[omnivoice] Model loaded on GPU ({torch.cuda.memory_allocated()//1024**2} MB)", flush=True)
    return _model


def tts_omnivoice(text: str, output_path: str, instruct: str | None = None) -> str:
    import numpy as np
    import soundfile as sf
    model = _get_model()
    audio = model.generate(text=text, instruct=instruct or "female, young adult, moderate pitch")
    if isinstance(audio, list):
        audio = np.concatenate(audio)
    sf.write(output_path, audio, 24000)
    return output_path


def tts_edge(text: str, output_path: str, voice: str = "fr-FR-DeniseNeural", lang: str = "fr") -> tuple[str, list[dict]]:
    import asyncio
    voice_map = {
        "fr": "fr-FR-DeniseNeural", "en": "en-US-AriaNeural", "en-us": "en-US-AriaNeural",
        "es": "es-ES-ElviraNeural", "de": "de-DE-KatjaNeural", "it": "it-IT-ElsaNeural",
        "pt": "pt-BR-FranciscaNeural", "ja": "ja-JP-NanamiNeural", "zh": "zh-CN-XiaoxiaoNeural",
        "ru": "ru-RU-SvetlanaNeural",
    }
    if voice in voice_map:
        voice = voice_map[voice]
    return asyncio.run(_tts_edge_async(text, output_path, voice))


async def _tts_edge_async(text: str, output_path: str, voice: str) -> tuple[str, list[dict]]:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    words = []
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                offset_s = chunk["offset"] / 10_000_000
                duration_s = chunk["duration"] / 10_000_000
                w = chunk.get("text", "").strip()
                if w:
                    words.append({"word": w, "start": round(offset_s, 3), "end": round(offset_s + duration_s, 3)})
    return output_path, words


def tts_elevenlabs(text: str, output_path: str, api_key: str, voice: str = "Rachel") -> str:
    import httpx
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    resp = httpx.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    Path(output_path).write_bytes(resp.content)
    return output_path


def tts_openai(text: str, output_path: str, api_key: str, voice: str = "alloy") -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.audio.speech.create(model="tts-1-hd", voice=voice, input=text)
    response.stream_to_file(output_path)
    return output_path


def _tts_generate(text: str, output_path: str, provider: str, config: dict) -> tuple[str, list[dict]]:
    tts_cfg = config.get("tts", {})
    api_key = tts_cfg.get("api_key") or ""
    instruct = tts_cfg.get("instruct", "female, young adult, moderate pitch")

    if provider == "omnivoice":
        tts_omnivoice(text, output_path, instruct=instruct)
        return output_path, []
    elif provider == "edge":
        voice = tts_cfg.get("voice", "en-US-AriaNeural")
        lang = tts_cfg.get("language", "en")
        path, words = tts_edge(text, output_path, voice=voice, lang=lang)
        return path, words
    elif provider == "elevenlabs":
        voice = tts_cfg.get("voice", "Rachel")
        tts_elevenlabs(text, output_path, api_key, voice)
        return output_path, []
    elif provider == "openai":
        voice = tts_cfg.get("voice", "alloy")
        tts_openai(text, output_path, api_key, voice)
        return output_path, []
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def generate_from_scenario(scenario_path: str, output_dir: str, config: dict) -> tuple[list[dict], dict[str, list[dict]]]:
    with open(scenario_path) as f:
        scenario = json.load(f)
    tts_cfg = config.get("tts", {})
    provider = tts_cfg.get("provider", "omnivoice")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    results = []
    native_timestamps = {}
    for scene in scenario.get("scenes", []):
        narration = scene.get("narration", "")
        if not narration.strip():
            continue
        scene_id = scene.get("scene_id", "unknown")
        output_file = str(out / f"{scene_id}.wav")
        try:
            _, words = _tts_generate(narration, output_file, provider, config)
            import subprocess
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", output_file],
                capture_output=True, text=True, timeout=5
            )
            dur = 0.0
            try:
                dur = float(probe.stdout.strip())
            except ValueError:
                pass
            results.append({"scene_id": scene_id, "path": output_file, "duration_s": dur})
            if words:
                native_timestamps[scene_id] = {"words": words, "audio": output_file}
            print(f"  {scene_id}: {dur:.1f}s" + (f" ({len(words)} native timestamps)" if words else ""))
        except Exception as exc:
            print(f"[tts] Failed for {scene_id}: {exc}", file=sys.stderr)

    if native_timestamps:
        ts_path = str(out.parent / "timestamps-native.json")
        with open(ts_path, "w") as f:
            json.dump(native_timestamps, f, indent=2, ensure_ascii=False)
        print(f"Native timestamps saved to: {ts_path}")

    return results, native_timestamps


def main():
    parser = argparse.ArgumentParser(description="Text-to-speech generation (OmniVoice / edge-tts / ElevenLabs / OpenAI)")
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--output", help="Output audio file path")
    parser.add_argument("--input", help="Path to scenario JSON (generates audio for all scenes)")
    parser.add_argument("--output-dir", help="Directory for per-scene audio files")
    parser.add_argument("--provider", choices=["omnivoice", "edge", "elevenlabs", "openai"], default=None)
    parser.add_argument("--instruct", default=None, help="Voice design prompt, e.g. 'female, young adult, british accent'")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--voice", default=None)
    parser.add_argument("--language", default=None)
    parser.add_argument("--config", default="~/.config/auto-video/config.yaml")
    parser.add_argument("--test", action="store_true", help="Run a quick test")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    config_path = args.config.replace("~", str(Path.home())) if args.config else None
    config = {}
    if config_path:
        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
        except (ImportError, FileNotFoundError):
            pass

    tts_cfg = config.get("tts", {})
    provider = args.provider or tts_cfg.get("provider", "omnivoice")
    instruct = args.instruct or tts_cfg.get("instruct")

    if args.test:
        text = "Hello world, let's vibe edit a video."
        output = str(Path.home() / "Downloads" / "tts_test.wav")
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        print(f"Testing {provider}...")
        if instruct:
            print(f"  Voice: {instruct}")
        _, words = _tts_generate(text, output, provider, {**config, "tts": {**tts_cfg, "instruct": instruct}})
        print(f"Test audio saved to: {output}")
        if words:
            print(f"  {len(words)} native timestamps available")
        return

    if args.input:
        output_dir = args.output_dir or str(Path(args.input).parent / "audio")
        merged_cfg = {**config, "tts": {**tts_cfg, "instruct": instruct}}
        results, _ = generate_from_scenario(args.input, output_dir, merged_cfg)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"{r['scene_id']}: {r['path']} ({r['duration_s']:.1f}s)")
        return

    if args.text and args.output:
        _, words = _tts_generate(args.text, args.output, provider, {**config, "tts": {**tts_cfg, "instruct": instruct}})
        print(f"Audio saved to: {args.output}")
        if words:
            print(f"  {len(words)} native timestamps available (use --input mode for auto-save)")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
