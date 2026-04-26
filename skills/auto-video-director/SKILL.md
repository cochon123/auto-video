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
| **Style mode** | `cinematic` or `standard` | `standard` |

### Style mode detection

**Cinematic mode indicators:**
- User says "cinematic", "film", "movie-style", "cinematique"
- Tone is `dramatic`
- Topic is artistic, emotional, philosophical, storytelling
- User mentions "typography", "text overlay", "quote style"

When `style_mode: cinematic`:
- Heavier use of typography and text overlays
- `phrase_groups` drive text overlay placement
- Remotion is preferred over FFmpeg
- Typography skill is loaded by montage as a sub-skill

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
- `style_mode` (`cinematic`/`standard`) — affects `phrase_group` granularity and whether `text_position`/`text_size` are included in the scenario

The scenarist returns a **scenario** (JSON with scene timing, asset queries, visual plans, phrase_groups).

### Execute media fetch

Use the fetch helper for each scene's asset requests:
```bash
python3 ~/.config/auto-video/helpers/fetch-media.sh \
  --query "artificial intelligence robot" \
  --source pexels \
  --type video \
  --output-dir ~/.config/auto-video/cache/<video-id>/media/
```

### Execute TTS

Generate narration audio. Audio files are output as `.wav` (OmniVoice outputs 24kHz WAV):
```bash
python3 ~/.config/auto-video/helpers/tts-generate.sh \
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
python3 ~/.config/auto-video/helpers/tts-timestamps.sh \
  --audio-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --output ~/.config/auto-video/cache/<video-id>/timestamps.json \
  --config ~/.config/auto-video/config.yaml
```

> **WARNING GPU SEQUENTIAL:** Whisper timestamps use GPU.
> This step MUST run AFTER TTS is fully unloaded, never alongside it.
> If Whisper fails after an OmniVoice fallback to edge-tts, retry — edge-tts output is still valid input for Whisper.

### Delegate to montage

Load the `auto-video-montage` skill as a sub-agent. Pass:
- scenario, media files, audio files, timestamps
- remotion config (enabled/disabled)
- `style_mode` (`cinematic`/`standard`)

When `style_mode: cinematic`, the montage skill loads the `auto-video-typography` sub-skill to generate cinematic text overlays driven by `phrase_groups`. This is not a separate pipeline step — typography is handled internally by montage.

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
[Intent Analysis] ──► determine: mode, tone, format, topic, style_mode
    │
    ▼
[Writer Skill] ──► generates script (if not provided)
    │
    ▼
[Scenarist Skill] ──► produces scenario JSON with phrase_groups + visual plans + asset queries
    │
    ▼
[fetch-media.sh] ──► downloads/generates all media assets
    │
    ▼
[tts-generate.sh] ──► generates narration audio per scene (OmniVoice 24kHz, or edge/API)
    │                            WARNING: GPU task - runs ALONE
    ▼
[tts-timestamps.sh] ──► extracts word-level timing
    │                            WARNING: GPU task - runs AFTER TTS is unloaded
    ▼
[Montage Skill] ──► validates assets -> assembles final video
    │  +- [Typography Skill] ──► cinematic text overlays (only if style_mode=cinematic)
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
