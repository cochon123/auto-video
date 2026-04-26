# Auto-Video Director

Main orchestration skill for video generation. This is the skill the user interacts with when they want to create a video.

## When to use

When the user asks to create, generate, or edit a video. Triggers: "make a video", "create a video", "generate a video", "vibe edit", "auto-video", "montage".

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

Extract: media mode, TTS settings, remotion enabled, default language, default format.

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

### Delegate to scenarist

Load the `auto-video-scenarist` skill as a sub-agent. Pass:
- the script
- media config (from config.yaml)
- format info
- `subtitle_mode` (dramatic/simple/educational) — affects phrase_group granularity and text positioning/sizing

The scenarist returns a **scenario** (JSON with scene timing, asset queries, visual plans, phrase_groups).

### Execute media fetch

Use the fetch helper for each scene's asset requests:
```bash
python3 ~/.config/auto-video/helpers/fetch-media.py \
  --query "artificial intelligence robot" \
  --source pexels \
  --type video \
  --output-dir ~/.config/auto-video/cache/<video-id>/media/
```

### Execute TTS

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

### Get timestamps

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

### Recalibrate timestamps

After Whisper extracts word-level timestamps, recalibrate the scenario's phrase_groups to match actual audio timing. This fixes the progressive audio/text drift caused by AI timestamp estimation.

```bash
python3 ~/.config/auto-video/helpers/recalibrate-timestamps.py \
  --scenario ~/.config/auto-video/cache/<video-id>/scenario.json \
  --timestamps ~/.config/auto-video/cache/<video-id>/timestamps.json \
  --audio-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --verbose
```

This step:
1. Matches each phrase_group text to Whisper words
2. Replaces AI-estimated timestamps with actual audio timestamps (scene-relative)
3. Falls back to proportional rescaling when matching fails
4. Recalculates scene start/end times from actual audio durations
5. Creates a backup of the original scenario.json

This is CRITICAL for sync quality. Without it, phrase_groups use AI-estimated timing that drifts progressively from actual narration.

### Delegate to montage

Load the `auto-video-montage` skill as a sub-agent. Pass:
- scenario, media files, audio files, timestamps
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

## Pipeline summary

```
User Request
    │
    ▼
[Intent Analysis] ──► determine: mode, tone, format, topic, subtitle_mode
    │
    ▼
[Writer Skill] ──► generates script (if not provided)
    │
    ▼
[Scenarist Skill] ──► produces scenario JSON with phrase_groups + subtitle_mode
    │
    ▼
[fetch-media.py] ──► downloads/generates all media assets
    │
    ▼
[tts-generate.py] ──► generates narration audio (OmniVoice, or edge/API)
    │                     WARNING: GPU task - runs ALONE
    ▼
[tts-timestamps.py] ──► extracts word-level timing
    │                     WARNING: GPU task - runs AFTER TTS is unloaded
    ▼
[recalibrate-timestamps.py] ──► aligns phrase_groups to actual audio timing
    │
    ▼
[Montage Skill] ──► validates assets -> assembles final video
    │  +- [Typography Skill] ──► text overlays (invoked based on subtitle_mode)
    │
    ▼
Final Video ──► user reviews ──► feedback loop
```

## Error handling

- If `config.yaml` is missing → tell user to run auto-video-setup
- If a helper fails → show the error, suggest fixes
- If media fetch returns no results → try alternate source or generate
- If TTS fails → check config, re-test; if OmniVoice fails → fall back to edge-tts
- If Remotion render fails → fall back to FFmpeg mode
