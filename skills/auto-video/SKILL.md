---
name: auto-video
description: Automated video production — research, script, scenario, assembly, and delivery
---

# Auto-Video

End-to-end automated video production pipeline.

## When to use

When the user asks to create, generate, or edit a video. Triggers: "make a video", "create a video", "generate a video", "vibe edit", "auto-video", "montage".

## Prerequisites

- `~/.config/auto-video/config.yaml` must exist (run auto-video-setup if missing)
- Helpers in `~/.config/auto-video/helpers/`

## Pipeline

```
User Request → Intent → [Research + Script] → Scenario JSON
                                        │
                    ┌─── fetch-media.py (CPU/NET, parallel)
                    └─── tts-generate.py (GPU, sequential)
                              │
                    tts-timestamps.py (GPU, after TTS unloaded)
                              │
                    build-phrase-groups.py (CPU)
                              │
                    validate-assets.py → video-compose.py
                              │
                    Final Video → [optional] YouTube upload
```

## GPU rules

- **NEVER run GPU tasks in parallel** — TTS, Whisper timestamps, and AI media generation must run one at a time
- Order: TTS → timestamps → media generation
- If local TTS fails, fall back to edge-tts (no GPU, HTTP API — safe to parallelize)
- Call `torch.cuda.empty_cache()` between GPU tasks

## Step 1: Identify intent

Analyze the request. Determine: topic, tone, language, duration target, subtitle style, YouTube upload?

Ask clarifying questions ONLY if ambiguous.

## Step 2: Research + Script

Skip if the user provided a script.

### Research

Run 3-5 web searches 

Look for: contrarian angles, hidden implications, concrete data, human stories, timeline context. Compile 5-10 key findings.

### Write

Structure: **HOOK** (1-2 attention-grabbing sentences) → **INTRO** → **BODY** (3-5 points) → **TWIST** (counterintuitive insight) → **OUTRO**

Rules:
- Plain text, no markdown
- Short sentences, 8-15 words, spoken rhythm
- Concrete > abstract — "Revenue jumped 340%" not "Revenue grew significantly"
- Subtle nerd humor, never forced
- ~150 words per minute of narration

| Format | Words | Scenes |
|--------|-------|--------|
| Short (60s) | ~150 | 3-4 |
| Medium (120s) | ~300 | 5-7 |
| Long (300s) | ~750 | 8-12 |

Those are just default, the user prompt is the main source of thruth.

### Scene breakdown

```json
{
  "scene_id": "scene-1",
  "type": "intro|content|outro",
  "narration": "spoken text",
  "visual_intent": "what to show visually",
  "keywords": ["..."]
}
```

First scene = intro, last = outro. Scenes 10-40s each.

## Step 3: Build visual scenario

Transform the script into a scenario JSON. For each scene: decide visual mode, media queries, phrase_texts, text style, transition.
don't be boring or lazy because we will use it for editing. it should be complex but clean when we watch it.

### Visual modes

| Condition | Mode | Source |
|-----------|------|--------|
| Intro/outro with title | `title_motion` | Remotion |
| Comparison, "vs" | `comparison` | Remotion |
| Ranking, list, "top X" | `ranking` | Remotion slideshow |
| Timeline, chronology | `timeline` | Remotion |
| Data, metrics, charts | `data_motion` | Statistic with Remotion |
| Concrete subject | `stock_footage`/`stock_image` | Pexels/DuckDuckGo animated with remotion |
| Abstract/invisible | `generated_image` | AI generation |
| General illustration | `stock_image` | DuckDuckGo/Pexels animated with remotion |

These are just recomendation, be smart and adapt to the user prompt. be creative and use the maximum potential of remotion

### Media queries

Per scene, 5-8 queries (use more if needed, this is just a recommendation). Short (2-4 words), no filler. Factual → DuckDuckGo, artistic → Pexels, abstract → AI.

### Phrase texts

Split narration into ordered text strings. These define HOW text splits — timing is added later by `build-phrase-groups.py`.

Rules:
- Split at natural pauses (commas, periods, clauses)
- One idea per phrase (3-8 words, max ~15)
- Never split mid-expression

### Text overlay style

The scenario has a `subtitle_mode` field: `"simple"` (default), `"dramatic"`, or `"educational"`.

**Simple (default):** Bottom subtitles. Dark background box. Clean sans-serif (Inter, DejaVu). Fade in/out. Readable, non-intrusive. Text supports the visual.

**Dramatic:** Text IS the visual. BIG sizing (96-120px on 1080p). Display fonts (Bebas Neue, Playfair Display, Oswald). Heavy animations — scale, typewriter, slide, spring physics. Key words and phrases get accent color highlights. Vary position per scene (left, center, right) for visual rhythm. Use `text_position` and `text_size` per scene for variety. Make it feel cinematic and alive.

**Educational:** Centered key terms. Large bold font (64-80px). Terms appear with scale animation and hold. Accent color borders or highlights. Text reinforces learning.

### Style profiles

| Style | Best for | Palette |
|-------|----------|---------|
| `tech-noir` | AI, software, startups | Deep blue, cyan, purple |
| `editorial-contrast` | Documentary, investigation | Dark navy, light blue, amber |
| `warm-documentary` | Human stories, culture | Warm dark, amber, terracotta |
| `bold-infographic` | Short-form, explainers | Deep indigo, green, gold |

### Scenario JSON schema

```json
{
  "video_id": "auto-2026-04-26-topic",
  "title": "...",
  "language": "fr",
  "subtitle_mode": "dramatic",
  "default_style": {
    "graphic_style": "tech-noir",
    "palette": { "background": "#07111f", "surface": "#0d1b2d", "text": "#e8f2ff", "accent": "#49e3ff", "accent_alt": "#9b87ff", "muted": "#6f86a8" }
  },
  "scenes": [
    {
      "scene_id": "scene-1",
      "order": 1,
      "type": "intro",
      "narration": "Spoken text for this scene.",
      "phrase_texts": ["phrase one", "phrase two"],
      "text_position": "center",
      "text_size": "epic",
      "visual": { "mode": "title_motion", "render_method": "remotion", "composition": "Intro", "props": { "title": "...", "accentColor": "#49e3ff" } },
      "assets": [],
      "transition": "fade"
    },
    {
      "scene_id": "scene-2",
      "order": 2,
      "type": "content",
      "narration": "...",
      "phrase_texts": ["..."],
      "text_position": "left",
      "text_size": "medium",
      "visual": { "mode": "stock_image", "render_method": "ffmpeg", "ken_burns": "zoom_in" },
      "assets": [
        { "query": "AI neural network", "type": "image", "source": "duckduckgo" },
        { "query": "artificial intelligence chip", "type": "image", "source": "pexels" }
      ],
      "transition": "dissolve"
    }
  ]
}
```

**NO timing in this output.** No `start_s`, `end_s`, `total_duration_s`, `phrase_groups` — those come from real audio measurements.

Every scene MUST have either `visual.mode = title_motion/lower_third` OR at least 1 asset query. Every scene MUST have `phrase_texts` with at least one entry.

## Step 4: Execute pipeline

### Media fetch (CPU/NET — runs in parallel with TTS)

```bash
python3 ~/.config/auto-video/helpers/fetch-media.py \
  --query "..." --source pexels --type video \
  --output-dir ~/.config/auto-video/cache/<video-id>/media/
```

If a helper fails: look at the code. Fix if it's a code problem, pass otherwise.

### TTS generation (GPU — runs alone)

```bash
python3 ~/.config/auto-video/helpers/tts-generate.py \
  --input scenario.json \
  --output-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --config ~/.config/auto-video/config.yaml
```

Reads `provider`, `voice` from config. Override with `--provider`, `--voice`.

### Timestamps (GPU — runs after TTS unloads)

```bash
python3 ~/.config/auto-video/helpers/tts-timestamps.py \
  --audio-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --output ~/.config/auto-video/cache/<video-id>/timestamps.json \
  --config ~/.config/auto-video/config.yaml
```

### Build phrase groups (CPU)

```bash
python3 ~/.config/auto-video/helpers/build-phrase-groups.py \
  --scenario ~/.config/auto-video/cache/<video-id>/scenario.json \
  --timestamps ~/.config/auto-video/cache/<video-id>/timestamps.json \
  --audio-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --verbose
```

This matches phrase_texts → Whisper words, assigns real timestamps, calculates scene durations, replaces `phrase_texts` with `phrase_groups`. Creates backup of original scenario.json.

## Step 5: Assembly

### Validate assets first

```bash
python3 ~/.config/auto-video/helpers/validate-assets.py ~/.config/auto-video/cache/<video-id>/media/ 30 1920 1080
```

Auto-fix fps/resolution/codec mismatches before rendering. Re-encode with FFmpeg if needed:
- FPS mismatch: `ffmpeg -i input.mp4 -r 30 -c:v libx264 output_30fps.mp4`
- Resolution mismatch: `ffmpeg -i input.mp4 -vf scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2 output.mp4`
- Audio duration must match scene durations within 2s tolerance

### Render

```bash
python3 ~/.config/auto-video/helpers/video-compose.py \
  --method ffmpeg \
  --scenario ~/.config/auto-video/cache/<video-id>/scenario.json \
  --audio-dir ~/.config/auto-video/cache/<video-id>/audio/ \
  --timestamps ~/.config/auto-video/cache/<video-id>/timestamps.json \
  --media-dir ~/.config/auto-video/cache/<video-id>/media/ \
  --output ~/Videos/auto-video/<video_id>.mp4 \
  --config ~/.config/auto-video/config.yaml
```

If Remotion enabled in config, use `--method remotion`. If Remotion fails, fall back to `--method ffmpeg`.

For text overlays during assembly:
- **FFmpeg**: use `drawtext` filters with enable timing from phrase_groups
- **Remotion**: build React components with `useCurrentFrame`, `interpolate`, `spring`

### Quality check

```bash
ls -lh <output>
ffprobe -v error -show_entries format=duration -of csv=p=0 <output>
```

Duration must match scenario total within 2s.

## Step 6: Deliver

Show the video path. User can request changes by timestamp:
- "At 0:12, change the image" → re-fetch media → re-render scene → re-concat
- "Shorten the intro" → adjust scenario → re-render affected scenes → re-concat
- "Add transition at 0:45" → adjust concat → re-concat

Small edits only need affected scenes re-processed, not the entire video.

## Step 7: YouTube upload (optional)

If requested and YouTube enabled in config:

```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py upload \
  --config ~/.config/auto-video/config.yaml \
  --title "<title>" --description "<description>" \
  --tags "<tags>" --privacy <private|unlisted|public> \
  --json <video_path>
```

If YouTube not enabled: tell user to run auto-video-setup.

## Error handling

- Missing `config.yaml` → run auto-video-setup
- Helper fails → show error, suggest fix
- Media fetch empty → alternate source or generate
- TTS fails → check config; local TTS fails → edge-tts fallback
- Remotion render fails → FFmpeg fallback
- YouTube upload fails → suggest `youtube-upload.py auth` to refresh credentials
