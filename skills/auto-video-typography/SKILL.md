# Auto-Video Typography

Handles cinematic text overlays, typography, and animated text for video production.

## When to use

Loaded by the montage skill when the scenario has `style_mode: "cinematic"`. Also when the user explicitly requests text overlays, quote-style presentation, or cinematic typography.

## Role

You are a motion typography designer. You take phrase_groups from the scenario and produce beautiful, timed text overlays that sync with narration.

## Step 1: Load fonts

### Google Fonts integration (Remotion)

When using Remotion, load fonts via `@remotion/google-fonts`:

```tsx
import { loadFont } from "@remotion/google-fonts/LoadFont";
import { getFontMetadata } from "@remotion/google-fonts";

// Epic/cinematic
const bebasNeue = getFontMetadata("BebasNeue");
loadFont(bebasNeue, { weights: ["400"] });

// Elegant/serif
const playfair = getFontMetadata("PlayfairDisplay");
loadFont(playfair, { weights: ["400", "700"] });

// Clean/modern
const inter = getFontMetadata("Inter");
loadFont(inter, { weights: ["300", "400", "600", "700"] });

// Bold display
const oswald = getFontMetadata("Oswald");
loadFont(oswald, { weights: ["300", "400", "700"] });
```

### FFmpeg fallback

When using FFmpeg, specify fonts by system name:
```bash
drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='Hello':fontsize=48:fontcolor=white
```

Common system fonts: DejaVuSans, LiberationSans, NotoSans.

## Step 2: Apply typography presets

### Presets

| Preset | Font | Weight | Tracking | Case | Use case |
|--------|------|--------|----------|------|----------|
| `epic` | Bebas Neue | 400 | +0.15em | UPPERCASE | Dramatic openings, titles, powerful statements |
| `minimal` | Inter | 300 | +0.05em | normal | Clean narration, documentary |
| `corporate` | Inter | 600 | +0.02em | Capitalize | Business, data, news |
| `cinematic` | Playfair Display | 400 | +0.03em | normal | Emotional, philosophical, storytelling |

### Scene-level text_position

| Position | CSS (Remotion) | FFmpeg drawtext x-position | Effect |
|----------|----------------|---------------------------|--------|
| `left` | `textAlign: "left"` | `x=80` | Dramatic, asymmetric |
| `center` | `textAlign: "center"` | `x=(w-text_w)/2` | Balanced, powerful |
| `right` | `textAlign: "right"` | `x=w-text_w-80` | Modern, editorial |
| `bottom` | `position: "absolute", bottom: 80` | `y=h-120` | Cinematic subtitle |

### Scene-level text_size

| Size | Remotion fontSize (1080p) | FFmpeg fontsize | Lines on screen |
|------|--------------------------|-----------------|-----------------|
| `epic` | 96-120px | 72 | 1-2 |
| `large` | 64-80px | 48 | 2-3 |
| `medium` | 40-56px | 32 | 3-4 |
| `small` | 28-36px | 24 | 4-5 |

### Adaptive sizing

Adjust text_size based on phrase length:
- <= 20 chars: use scene's text_size as-is
- 20-40 chars: reduce fontSize by 15%
- 40-60 chars: reduce fontSize by 25%
- > 60 chars: reduce fontSize by 35% or split into multiple lines

## Step 3: Apply animations

Each phrase_group gets an animation synced to its `start`/`end` timestamps.

### Animation types

| Animation | Description | Duration | Best for |
|-----------|-------------|----------|----------|
| `fade` | Opacity 0->1->0 | 0.3s in, 0.3s out | All styles, default |
| `slide` | TranslateX -60px->0 | 0.4s ease-out | Minimal, corporate |
| `scale` | Scale 0.8->1.0 | 0.4s ease-out | Epic, cinematic |
| `typewriter` | Characters appear one by one | 0.05s per char | Cinematic, storytelling |

### Remotion animation code patterns

```tsx
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

// Fade animation
const opacity = interpolate(frame, [0, fadeInFrames], [0, 1], { extrapolateRight: "clamp" });

// Slide animation (from left)
const translateX = spring({ frame, fps, config: { damping: 200 } });
const x = interpolate(translateX, [0, 1], [-60, 0]);

// Scale animation
const scaleVal = spring({ frame, fps, config: { damping: 15, stiffness: 80 } });
const scale = interpolate(scaleVal, [0, 1], [0.8, 1.0]);

// Typewriter effect
const charsVisible = Math.floor(frame / charsPerFrame);
const displayedText = text.slice(0, charsVisible);
```

### Animation selection by preset

| Preset | Default animation | Alternative |
|--------|------------------|-------------|
| `epic` | scale | fade for long text |
| `minimal` | slide | fade |
| `corporate` | slide | fade |
| `cinematic` | typewriter | fade for short phrases |

### FFmpeg text animation

FFmpeg doesn't natively support per-character animation. Use these approximations:

```bash
# Static text overlay with timing
drawtext=enable='between(t,start,end)':fontcolor='white':text='phrase text':fontsize=48:x=80:y=h/2
```

For complex text animations, prefer Remotion. FFmpeg is limited to static overlays with enable timing.

## Step 4: Compose the typography component

### Remotion component example

```tsx
import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from "remotion";

interface TypographySceneProps {
  phraseGroups: Array<{ text: string; start: number; end: number }>;
  preset: "epic" | "minimal" | "corporate" | "cinematic";
  position: "left" | "center" | "right" | "bottom";
  size: "epic" | "large" | "medium" | "small";
  accentColor: string;
  backgroundMedia?: string;
}

export const TypographyScene: React.FC<TypographySceneProps> = ({
  phraseGroups,
  preset,
  position,
  size,
  accentColor,
  backgroundMedia,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  const activeGroup = phraseGroups.find(
    (g) => currentTime >= g.start && currentTime < g.end
  );

  if (!activeGroup) return null;

  const durationFrames = (activeGroup.end - activeGroup.start) * fps;
  const groupStartFrame = Math.round(activeGroup.start * fps);
  const localFrame = frame - groupStartFrame;

  const fadeFrames = Math.round(0.3 * fps);
  const opacity = interpolate(
    localFrame,
    [0, fadeFrames, durationFrames - fadeFrames, durationFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {backgroundMedia && <img src={backgroundMedia} style={{ opacity: 0.3 }} />}
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: position === "center" ? "center" : "flex-start", paddingLeft: position === "left" ? 80 : 0, opacity }}>
        <span style={{ fontSize: size === "epic" ? 96 : size === "large" ? 64 : size === "medium" ? 48 : 32, color: "white", fontFamily: preset === "epic" ? "Bebas Neue" : preset === "cinematic" ? "Playfair Display" : "Inter" }}>
          {activeGroup.text}
        </span>
      </div>
    </AbsoluteFill>
  );
};
```

## Step 5: Output

Return to the montage skill:
- Typography configuration for each scene (font, size, position, animation)
- Any font files that need to be loaded
- Timing data synchronized with phrase_groups

## Integration with montage

The montage skill calls this skill for each scene that has `text_position` and `text_size` fields. The typography skill:
1. Selects font and preset based on scene type and scenario style
2. Calculates adaptive sizing based on phrase length
3. Chooses animation type
4. Returns rendering instructions (Remotion component or FFmpeg filter)

## Important

- Only active when `style_mode: "cinematic"` in the scenario
- Phrase groups must NEVER be split mid-word or mid-expression
- Text must be readable: minimum 24px equivalent on 1080p
- Animations should feel smooth, not jarring: use spring physics in Remotion
- Dark backgrounds with white text is the default; accent color for highlights only
- Always test with longest phrase first to ensure it fits the screen
