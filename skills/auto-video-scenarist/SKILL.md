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

## Step 0: Detect subtitle mode

Determine which subtitle mode to use based on the video's purpose and content.

### Mode detection rules

| Mode | When to use | Indicators |
|------|-------------|------------|
| **dramatic** | Cinematic, artistic, emotional, storytelling | User says "cinematic", "film", "dramatic", "movie-style"; tone is "dramatic"; topic is artistic/philosophical; user mentions "typography", "text overlay" |
| **simple** | Informational, news, factual updates | User says "information", "news", "update", "factual"; tone is "informative"; topic is tech/business news, data, facts |
| **educational** | Learning, explaining concepts, highlighting terms | User says "education", "teach", "explain", "tutorial"; tone is "educational"; topic includes technical terms, concepts to define |

### Mode behavior table

| Feature | dramatic | simple | educational |
|---------|----------|--------|-------------|
| `subtitle_mode` field | `"dramatic"` | `"simple"` | `"educational"` |
| `phrase_groups` style | Short, punchy (2-6 words) for dramatic pacing | Full sentences, natural pauses | Key terms, difficult words, concepts |
| `text_position` | Varies per scene: "left", "center", "right", "bottom" | Always "bottom" (subtitles) | "center" with highlight |
| `text_size` | "epic", "large", "medium", "small" | "medium" (readable) | "large" (emphasized) |
| Typography skill | Full cinematic fonts + animations | Simple sans-serif, minimal animation | Highlighted terms, bold/underline |
| Visual emphasis | Text IS the visual (full screen text) | Text supports visual (subtitles below) | Text reinforces learning (terms highlighted) |

### Phrase group rules per mode

#### dramatic mode:
- **Ultra-short phrases**: 2-6 words maximum
- **Split at emotional beats**: comma, period, dramatic pause
- **One idea per phrase**: no compound thoughts
- **Visual rhythm**: phrases drive the visual pace
- **Timestamps**: allow slight overlap (0.1-0.3s) for smooth transitions
- **Example**: "Tout commence." → "Une page blanche." → "Et un clavier."

#### simple mode:
- **Full sentences**: one phrase per complete sentence
- **Natural pauses**: split only at periods or major clauses
- **No mid-sentence splits**: "tout commence par une page blanche" is ONE phrase, not two
- **Subtitle style**: position "bottom", size "medium"
- **Example**: "Tout commence par une page blanche, et un jeune se lance." → ONE phrase

#### educational mode:
- **Key terms only**: highlight difficult words, technical terms, concepts
- **Phrase IS the term**: each phrase is a word or phrase that needs explanation
- **Position center**: terms appear in center of screen with emphasis
- **Bold/underline**: use typographic emphasis to draw attention
- **Example**: If narration explains "l'intelligence artificielle", create phrase: "Intelligence Artificielle" with emphasis

### JSON schema update

Update the scenario JSON schema. Replace `style_mode` with `subtitle_mode`:

```json
{
  "video_id": "auto-2026-04-26-topic",
  "title": "...",
  "language": "fr",
  "subtitle_mode": "dramatic" | "simple" | "educational",
  "total_duration_s": 65,
  "scenes": [
    {
      "scene_id": "scene-1",
      "type": "intro",
      "narration": "Spoken text...",
      "phrase_groups": [
        { "text": "...", "start": 0.0, "end": 2.0 }
      ],
      "text_position": "bottom",  // "simple" mode always "bottom"
      "text_size": "medium",       // "simple" mode always "medium"
      "visual": { ... },
      "assets": [ ... ],
      "transition": "fade"
    }
  ]
}
```

### Per-scene subtitle mode

If you detect that a specific scene needs a DIFFERENT subtitle mode (e.g., a definition in an informational video), you can override `text_position` and `text_size` per scene. But the global `subtitle_mode` field should reflect the PRIMARY mode.

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

**Dramatic mode:** prefer 2-6 words per group for dramatic, punchy pacing. Short phrases create visual rhythm and allow large cinematic typography.

**Simple mode:** sentence-level or clause-level groups are fine. One group per sentence or per natural pause. Position "bottom", size "medium".

**Educational mode:** highlight key terms only. Each phrase is a term that needs explanation. Position "center", size "large" with emphasis.

### Timestamp estimation

Estimate timestamps proportional to word count within the scene duration:
- Average speaking pace: ~2.5 words/second for French, ~3 words/second for English
- Add brief pauses (0.15-0.3s) between groups
- First group starts at `scene.start_s`
- Last group ends near `scene.end_s`

### Example

Given narration: "Tout commence par une page blanche. Un jeune, une idée, et un clavier."
Scene duration: 0.0s → 4.97s.

**Dramatic mode:**
```json
"phrase_groups": [
  { "text": "Tout commence.", "start": 0.0, "end": 1.0 },
  { "text": "Une page blanche.", "start": 1.0, "end": 2.17 },
  { "text": "Un jeune,", "start": 2.17, "end": 3.0 },
  { "text": "une idée,", "start": 3.0, "end": 3.8 },
  { "text": "et un clavier.", "start": 3.8, "end": 4.97 }
]
```

**Simple mode:**
```json
"phrase_groups": [
  { "text": "Tout commence par une page blanche.", "start": 0.0, "end": 2.17 },
  { "text": "Un jeune, une idée, et un clavier.", "start": 2.17, "end": 4.97 }
]
```

## Step 4: Build the full scenario

### Scenario JSON schema

```json
{
  "video_id": "auto-2026-04-23-topic",
  "title": "...",
  "language": "fr",
  "subtitle_mode": "dramatic",
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
        { "text": "Tout commence.", "start": 0.0, "end": 1.0 },
        { "text": "Une page blanche.", "start": 1.0, "end": 2.17 },
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

### Text overlay fields (behavior varies by `subtitle_mode`)

The `text_position` and `text_size` fields are present for all modes, but their behavior differs:

| Field | Values | Purpose by mode |
|-------|--------|-----------------|
| `text_position` | `"left"`, `"center"`, `"right"`, `"bottom"` | **dramatic**: varies per scene for visual interest; **simple**: always `"bottom"` (subtitles); **educational**: `"center"` for term emphasis |
| `text_size` | `"epic"`, `"large"`, `"medium"`, `"small"` | **dramatic**: varies per scene; **simple**: always `"medium"` (readable subtitles); **educational**: `"large"` for emphasis |

Guidelines for assigning text overlay fields:

**Dramatic mode:**
- **Intro scenes**: `"text_position": "center"`, `"text_size": "epic"`
- **Key reveal/punchline scenes**: `"text_position": "left"` or `"center"`, `"text_size": "large"` or `"epic"`
- **Supporting content**: `"text_position": "left"` or `"right"`, `"text_size": "medium"`
- **Outro scenes**: `"text_position": "center"`, `"text_size": "large"`
- Vary positions across consecutive scenes for visual interest
- When a scene has strong imagery, use `"left"` or `"right"` to avoid obscuring visuals

**Simple mode:**
- All scenes: `"text_position": "bottom"`, `"text_size": "medium"`

**Educational mode:**
- All scenes with terms: `"text_position": "center"`, `"text_size": "large"`
- Use bold/underline emphasis in the typography skill for highlighted terms

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
1. `fetch-media.sh` — to download all assets
2. `tts-generate.sh` — to generate audio per scene
3. The montage skill — to assemble everything (including typography overlays based on subtitle_mode)

## Important

- Every scene MUST have either `visual.mode = title_motion/lower_third` OR at least 1 asset query
- Every scene MUST have `phrase_groups` with at least one entry
- Total duration must match the sum of scene durations
- Scene order must be sequential with no gaps
- Prefer variety: don't use the same visual mode for more than 3 consecutive scenes
- `text_position` and `text_size` behavior depends on `subtitle_mode`
- Phrase group timestamps must fit within the scene's `start_s` and `end_s` bounds
