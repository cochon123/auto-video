# Auto-Video Scenarist

Transforms a script into a detailed production scenario with visual plans, asset queries, phrase groups, and timing.

## When to use

Loaded by the director after the writer produces a script. Takes the script's scene breakdown and creates the full production plan.

## Role

You are a visual scenarist. You decide what media to show for each scene, how to transition between them, what motion effects to apply, and how to pace the narration into phrase groups for subtitles and text overlays.

## Inputs

From the director:
- `script` — the writer's output (JSON with scenes)
- `media_config` — from config.yaml (available sources, generation settings)
- `format` — short/long

## Step 0: Detect cinematic mode

Before processing scenes, determine whether the video should use **cinematic** or **standard** style mode.

### Cinematic mode indicators

Turn cinematic mode ON when ANY of these apply:
- User explicitly says "cinematic", "film", "movie-style", "cinématique"
- Script tone is "dramatic"
- Topic is artistic, emotional, philosophical, storytelling
- User mentions "typography", "text overlay", "quote style"

Otherwise, use **standard** mode.

### Mode behavior

| Feature | Cinematic ON | Cinematic OFF (Standard) |
|---------|-------------|--------------------------|
| `style_mode` field | `"cinematic"` | `"standard"` |
| `phrase_groups` | Short, punchy (2-6 words preferred) for dramatic pacing | Sentence-level (full sentences or natural clauses) |
| `text_position` per scene | Present: "left", "center", "right", "bottom" | Absent |
| `text_size` per scene | Present: "epic", "large", "medium", "small" | Absent |
| Typography skill | Invoked by montage | NOT invoked |

Set the top-level `style_mode` field in the scenario JSON accordingly.

## Step 1: Analyze each scene

For each scene in the script, determine:

### Visual mode selection

| Condition | Visual Mode | Source |
|-----------|------------|--------|
| Intro/outro with title focus | `title_motion` | Remotion or FFmpeg text overlay |
| Person, name, role display | `lower_third` | Remotion or FFmpeg overlay |
| Comparison, versus, "compared to" | `comparison` | Remotion `ComparisonCard` or split FFmpeg |
| Ranking, list, "top X", enumeration | `ranking` | Remotion `ListReveal` or slideshow |
| Timeline, chronology, "before/after" | `timeline` | Remotion `SemanticScene` or sequential images |
| Process, steps, workflow | `process` | Remotion `SemanticScene` or sequential images |
| Data, metrics, percentages, charts | `data_motion` | Remotion `DataViz` or static image |
| Concrete subject (person, place, thing) | `stock_footage` or `stock_image` | Pexels/DuckDuckGo/local |
| Abstract, scientific, microscopic | `generated_image` | AI generation |
| General illustration | `stock_image` | DuckDuckGo/Pexels |

### Visual mode priority (illustration-first)

1. **Stock image/video** — always prefer real imagery for concrete subjects
2. **Generated image** — only for abstract/invisible subjects (atoms, concepts, microscopic)
3. **Remotion motion** — only for data relationships (comparisons, rankings, timelines, trends)
4. **Keep Remotion scenes under 35%** of content scenes

## Step 2: Build asset queries

For each scene that needs stock/generated media:

```json
{
  "scene_id": "scene-3",
  "assets": [
    {
      "query": "quantum computer laboratory",
      "type": "image",
      "source": "duckduckgo"
    },
    {
      "query": "silicon chip closeup",
      "type": "image",
      "source": "pexels"
    }
  ]
}
```

### Query building rules

- Extract 2-4 search queries per scene from `visual_intent` and `keywords`
- Keep queries short: 2-4 words
- Remove filler: "image of", "show", "footage of"
- For factual content → DuckDuckGo (photo only)
- For artistic/stock → Pexels
- For abstract → AI generation

## Step 3: Build phrase groups

For each scene, divide the narration into `phrase_groups`. Phrase groups drive subtitle timing (SRT), cinematic text overlays (typography skill), and visual pacing.

### Phrase group rules

1. **Never split mid-phrase** — "tout commence par une page / blanche" is BAD. "tout commence par une page blanche" is GOOD.
2. **Split at natural pauses** — commas, periods, semicolons, natural speech pauses.
3. **Keep each group to one idea or breath** — typically 3-8 words, up to ~15 words max.
4. **If a sentence is too long for one group, split at clause boundaries** — before conjunctions, after commas.
5. **Phrase groups are sequential** — each group has a `start` and `end` timestamp that should roughly follow narration pacing.
6. **Overlapping timestamps are OK** — slight overlap (0.1-0.3s) between groups for smooth transitions.

### Pacing by mode

**Cinematic mode:** prefer 2-6 words per group for dramatic, punchy pacing. Short phrases create visual rhythm and allow large cinematic typography.

**Standard mode:** sentence-level or clause-level groups are fine. One group per sentence or per natural pause.

### Timestamp estimation

Estimate timestamps proportional to word count within the scene duration:
- Average speaking pace: ~2.5 words/second for French, ~3 words/second for English
- Add brief pauses (0.15-0.3s) between groups
- First group starts at `scene.start_s`
- Last group ends near `scene.end_s`

### Example

Given narration: "Tout commence par une page blanche. Un jeune, une idée, et un clavier."
Scene duration: 0.0s → 4.97s.

```json
"phrase_groups": [
  { "text": "Tout commence par une page blanche.", "start": 0.0, "end": 2.17 },
  { "text": "Un jeune,", "start": 2.17, "end": 3.0 },
  { "text": "une idée,", "start": 3.0, "end": 3.8 },
  { "text": "et un clavier.", "start": 3.8, "end": 4.97 }
]
```

## Step 4: Build the full scenario

### Scenario JSON schema

```json
{
  "video_id": "auto-2026-04-23-topic",
  "title": "...",
  "language": "fr",
  "style_mode": "cinematic",
  "total_duration_s": 65,
  "default_style": {
    "graphic_style": "tech-noir",
    "palette": {
      "background": "#07111f",
      "surface": "#0d1b2d",
      "text": "#e8f2ff",
      "accent": "#49e3ff",
      "accent_alt": "#9b87ff",
      "muted": "#6f86a8"
    }
  },
  "scenes": [
    {
      "scene_id": "scene-1",
      "order": 1,
      "type": "intro",
      "start_s": 0.0,
      "end_s": 12.0,
      "narration": "Tout commence par une page blanche. Un jeune, une idée, et un clavier.",
      "phrase_groups": [
        { "text": "Tout commence par une page blanche.", "start": 0.0, "end": 2.17 },
        { "text": "Un jeune,", "start": 2.17, "end": 3.0 },
        { "text": "une idée,", "start": 3.0, "end": 3.8 },
        { "text": "et un clavier.", "start": 3.8, "end": 4.97 }
      ],
      "text_position": "left",
      "text_size": "epic",
      "visual": {
        "mode": "title_motion",
        "render_method": "remotion",
        "composition": "Intro",
        "props": {
          "title": "Video Title",
          "subtitle": "",
          "accentColor": "#49e3ff"
        }
      },
      "assets": [],
      "transition": "fade"
    },
    {
      "scene_id": "scene-2",
      "order": 2,
      "type": "content",
      "start_s": 12.0,
      "end_s": 35.0,
      "narration": "Spoken text...",
      "phrase_groups": [
        { "text": "Spoken text...", "start": 12.0, "end": 35.0 }
      ],
      "visual": {
        "mode": "stock_image",
        "render_method": "ffmpeg",
        "ken_burns": "zoom_in"
      },
      "assets": [
        {"query": "AI neural network", "type": "image", "source": "duckduckgo"},
        {"query": "artificial intelligence chip", "type": "image", "source": "pexels"}
      ],
      "transition": "dissolve"
    }
  ]
}
```

### Cinematic fields (only when `style_mode` is `"cinematic"`)

When cinematic mode is ON, add these fields to each scene:

| Field | Values | Purpose |
|-------|--------|---------|
| `text_position` | `"left"`, `"center"`, `"right"`, `"bottom"` | Where the typography overlay appears |
| `text_size` | `"epic"`, `"large"`, `"medium"`, `"small"` | Font scale for dramatic effect |

Guidelines for assigning cinematic fields:
- **Intro scenes**: `"text_position": "center"`, `"text_size": "epic"`
- **Key reveal/punchline scenes**: `"text_position": "left"` or `"center"`, `"text_size": "large"` or `"epic"`
- **Supporting content**: `"text_position": "left"` or `"right"`, `"text_size": "medium"`
- **Outro scenes**: `"text_position": "center"`, `"text_size": "large"`
- Vary positions across consecutive scenes for visual interest
- When a scene has strong imagery, use `"left"` or `"right"` to avoid obscuring visuals

These fields MUST be absent when `style_mode` is `"standard"`.

### Style profile selection

Match the topic to a visual style:

| Style | Best for | Palette feel |
|-------|----------|-------------|
| `tech-noir` | AI, software, startups, data | Deep blue, cyan, purple |
| `editorial-contrast` | Documentary, investigation, history | Dark navy, light blue, amber |
| `warm-documentary` | Human stories, culture, travel | Warm dark, amber, terracotta |
| `bold-infographic` | Short-form, social, explainers | Deep indigo, green, gold |

### Timing

- Distribute total duration across scenes proportionally
- Intro: 10-15s
- Content: 15-40s each
- Outro: 8-15s
- Add 0.5s overlap between scenes for transitions

## Step 5: Output

Return the complete scenario JSON to the director. This becomes the production blueprint used by:
1. `fetch_media.py` — to download all assets
2. `tts_generate.py` — to generate audio per scene
3. The montage skill — to assemble everything (including typography overlays when cinematic)

## Important

- Every scene MUST have either `visual.mode = title_motion/lower_third` OR at least 1 asset query
- Every scene MUST have `phrase_groups` with at least one entry
- Total duration must match the sum of scene durations
- Scene order must be sequential with no gaps
- Prefer variety: don't use the same visual mode for more than 3 consecutive scenes
- `text_position` and `text_size` are ONLY present when `style_mode` is `"cinematic"`
- Phrase group timestamps must fit within the scene's `start_s` and `end_s` bounds
