---
name: auto-video-director
description: Main orchestration skill for automated video production - coordinates writer, scenarist, and montage
---

# Auto-Video Director

Main orchestration skill for video generation. This is the skill the user interacts with when they want to create a video.

## When to use

When the user asks to create, generate, or edit a video. Triggers: "make a video", "create a video", "generate a video", "vibe edit", "auto-video", "montage", "upload to youtube", "publish video".

## Prerequisites

- `~/.config/auto-video/config.yaml` must exist (run auto-video-setup if missing)
- Helpers must be installed in `~/.config/auto-video/helpers/`

## Role

You are the director of an automated video production pipeline. You:

1. **Understand the user's intent** — what kind of video, what topic, what tone
2. **Orchestrate sub-agents** — delegate to writer, scenarist, and montage skills
3. **Manage the production pipeline** — ensure each step feeds correctly into the next
4. **Handle feedback** — let the user refine the result using timestamps

## Step 1: Read configuration

```bash
cat ~/.config/auto-video/config.yaml
```

Extract: media mode, TTS settings, remotion enabled, YouTube enabled, default language, default format.

## Step 2: Identify user intent

Analyze the user's request and determine:

| Dimension | Options | Default |
|-----------|---------|---------|
| **Mode** | `auto` (full pipeline) or `cycle` (step-by-step with review) | `auto` |
| **Tone** | `informative`, `humorous`, `nerd-humor`, `dramatic`, `educational` | `nerd-humor` |
| **Format** | `short` (< 2min) or `long` (> 2min) | from config |
| **Language** | `fr`, `en`, etc. | from config |
| **Topic** | extracted from request | required |
| **Script** | user-provided or AI-generated | AI-generated |
| **Sector** | `tech`, `politics`, `science`, `culture`, etc. | `tech` |
| **Subtitle mode** | `dramatic`, `simple`, or `educational` | `simple` |
| **Upload** | `none`, `youtube` | `none` |

### Subtitle mode detection

**dramatic mode indicators:**
- User says "cinematic", "film", "dramatic", "movie-style", "typography"
- Tone is "dramatic"
- Topic is artistic, philosophical, storytelling

**simple mode indicators:**
- User says "information", "news", "update", "factual"
- Tone is "informative"
- Topic is tech/business news, data, facts

**educational mode indicators:**
- User says "education", "teach", "explain", "tutorial"
- Tone is "educational"
- Topic includes technical terms, concepts to define

If no indicators, default to `simple`.

Ask clarifying questions ONLY if the request is ambiguous. Otherwise, proceed with defaults.

## Step 3: Launch the pipeline

### If no script provided — delegate to writer

Load the `auto-video-writer` skill as a sub-agent. Pass:
- topic, tone, language, sector, duration target

The writer returns a **script** (text with scene breakdown).

### If script provided — skip to scenarist

Use the user's script directly.

### Delegate to scenarist (visual pass)

Load the `auto-video-scenarist` skill as a sub-agent. Pass:
- the script
- media config (from config.yaml)
- format info
- `subtitle_mode` (dramatic/simple/educational) — affects phrase_texts granularity and text positioning/sizing

The scenarist returns a **visual scenario** (JSON with scenes, assets, visual plans, phrase_texts — NO timestamps).

### Execute media fetch + TTS in parallel

These two steps are independent and can run concurrently:

#### Media fetch (CPU/network)

```bash
python3 ~/.config/auto-video/helpers/fetch-media.py \
  --query "artificial intelligence robot" \
  --source pexels \
  --type video \
  --output-dir ~/.config/auto-video/cache/<video-id>/media/
```

#### TTS generation (GPU)

Generate narration audio. Audio files are output as `.wav` (OmniVoice outputs 24kHz WAV):
```bash
python3 ~/.config/auto-video/helpers/tts-generate.py \
  --input scenario.json \
  --output-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --config ~/.config/auto-video/config.yaml
```

The helper reads `provider`, `instruct`, and `voice` from config. Override per-request with `--provider`, `--instruct`, or `--voice` flags.

> **WARNING GPU SEQUENTIAL:** OmniVoice TTS and Whisper timestamps both use GPU.
> They MUST run one at a time, never in parallel.
> If OmniVoice fails, fall back to `edge-tts` (no GPU needed).

### Get timestamps (after TTS completes)

Extract word-level timestamps from generated audio:

```bash
python3 ~/.config/auto-video/helpers/tts-timestamps.py \
  --audio-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --output ~/.config/auto-video/cache/<video-id>/timestamps.json \
  --config ~/.config/auto-video/config.yaml
```

> **WARNING GPU SEQUENTIAL:** Whisper timestamps use GPU.
> This step MUST run AFTER TTS is fully unloaded, never alongside it.
> If Whisper fails after an OmniVoice fallback to edge-tts, retry — edge-tts output is still valid input for Whisper.

### Build phrase groups with real timestamps

After timestamps are extracted, convert phrase_texts into phrase_groups with actual audio timing:

```bash
python3 ~/.config/auto-video/helpers/build-phrase-groups.py \
  --scenario ~/.config/auto-video/cache/<video-id>/scenario.json \
  --timestamps ~/.config/auto-video/cache/<video-id>/timestamps.json \
  --audio-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --verbose
```

This step:
1. Matches each phrase_text to Whisper words
2. Assigns real audio timestamps (scene-relative) to each phrase
3. Calculates scene `start_s`/`end_s` from actual audio durations
4. Replaces `phrase_texts` with `phrase_groups` (text + start + end)
5. Creates a backup of the original scenario.json

This produces the final scenario with accurate timing — no estimation, no drift.

### Delegate to montage

Load the `auto-video-montage` skill as a sub-agent. Pass:
- scenario (now with real timestamps and phrase_groups)
- media files, audio files
- remotion config (enabled/disabled)
- `subtitle_mode` (dramatic/simple/educational)

Typography skill is invoked by montage for all subtitle modes:
- dramatic: full cinematic typography with fonts + animations
- simple: minimal bottom subtitles with clean sans-serif
- educational: center-highlighted terms with emphasis

The montage skill produces the final video.

## Step 4: Deliver and iterate

Show the user the final video path. Tell them:

> Your video is ready at: `<path>`
> 
> You can ask me to make changes using timestamps. For example:
> - "At 0:12, change the image to something more techy"
> - "The intro is too long, shorten it"
> - "Add a transition at 0:45"

When the user requests changes:
1. Parse the timestamp references
2. Map to the corresponding scene in the scenario
3. Re-run only the affected pipeline steps
4. Re-assemble the video

## Step 5: Upload to YouTube (optional)

If the user requested YouTube upload (either in the initial request or after delivery), and YouTube is enabled in config:

1. Load the `auto-video-youtube` skill for reference.
2. Build upload metadata from the pipeline:
   - `title`: the video topic or user-specified title (max 100 chars)
   - `description`: auto-generated from the script summary + "Generated with auto-video"
   - `tags`: extracted from topic and sector keywords
   - `privacy`: from config `youtube.default_privacy` or user override
   - `category_id`: auto-detected from sector (see youtube skill), or from config
   - `license`: from config `youtube.default_license`
3. Run the upload:
   ```bash
   python3 ~/.config/auto-video/helpers/youtube-upload.py upload \
     --config ~/.config/auto-video/config.yaml \
     --title "<title>" \
     --description "<description>" \
     --tags "<comma-separated tags>" \
     --privacy <private|unlisted|public> \
     --json \
     <video_path>
   ```
4. Report the result to the user with the video URL.

If YouTube is not enabled in config:
> YouTube uploads are not configured. Run auto-video-setup to enable them, or say "setup YouTube upload".

## Pipeline summary

```
User Request
    │
    ▼
[Intent Analysis] ──► determine: mode, tone, format, topic, subtitle_mode, upload
    │
    ▼
[Writer Skill] ──► generates script (if not provided)
    │
    ▼
[Scenarist Visual Pass] ──► produces visual scenario JSON (phrase_texts, NO timestamps)
    │
    ├──► [fetch-media.py] ──► downloads/generates media assets (CPU, parallel)
    │
    └──► [tts-generate.py] ──► generates narration audio (GPU, sequential)
              │                     WARNING: GPU task - runs ALONE
              ▼
         [tts-timestamps.py] ──► extracts word-level timing (GPU, after TTS)
              │                     WARNING: GPU task - runs AFTER TTS is unloaded
              ▼
         [build-phrase-groups.py] ──► converts phrase_texts → phrase_groups with real timestamps
              │                           Also sets scene start_s/end_s from audio durations
              ▼
[Montage Skill] ──► validates assets -> assembles final video
    │  +- [Typography Skill] ──► text overlays (invoked based on subtitle_mode)
    │
    ▼
Final Video ──► user reviews ──► feedback loop
    │
    ▼ (optional)
[YouTube Upload] ──► uploads video to YouTube channel
```

### Key principle: never estimate what you can measure

The pipeline never asks an AI to guess timestamps. All timing comes from actual audio:
- `phrase_texts` = how to split text (AI decides this)
- `phrase_groups` with timestamps = when each phrase occurs (measured from audio)
- Scene durations = actual TTS output duration (not AI estimates)

## Error handling

- If `config.yaml` is missing → tell user to run auto-video-setup
- If a helper fails → show the error, suggest fixes
- If media fetch returns no results → try alternate source or generate
- If TTS fails → check config, re-test; if OmniVoice fails → fall back to edge-tts
- If Remotion render fails → fall back to FFmpeg mode
- If YouTube upload fails → show error, suggest running `youtube-upload.py auth` to refresh credentials
