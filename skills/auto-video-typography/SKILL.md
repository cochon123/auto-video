---
name: auto-video-typography
description: Typography and text overlay design for auto-video - creates cinematic text, subtitles, and visual emphasis
---

# Auto-Video Typography

Handles cinematic text overlays, typography, and animated text for video production.

## When to use

Always loaded by the montage skill for ALL subtitle modes. Handles dramatic (cinematic), simple (subtitles), and educational (key terms) differently based on the scenario's `subtitle_mode` field.

## Role

You are a motion typography designer. You take phrase_groups from the scenario and produce beautiful, timed text overlays that sync with narration.

## Step 0: Determine typography approach

Based on the scenario's `subtitle_mode` field, choose the appropriate typography strategy:

### dramatic mode
- **Purpose**: Cinematic, artistic, emotional storytelling
- **Text IS the visual**: full-screen text, large, bold
- **Positions**: varies per scene (left, center, right, bottom)
- **Sizes**: epic (96-120px), large (64-80px), medium (40-56px), small (28-36px)
- **Fonts**: Bebas Neue (epic), Playfair Display (cinematic), Oswald (bold display)
- **Animations**: scale, fade, slide, typewriter
- **Adaptive sizing**: highly adaptive based on phrase length

### simple mode
- **Purpose**: Informational subtitles, news, factual content
- **Text SUPPORTS visual**: bottom-aligned, readable, non-intrusive
- **Position**: always "bottom" (subtitles)
- **Size**: always "medium" (40-48px) for readability
- **Font**: Inter (clean, modern, sans-serif)
- **Animation**: fade only (no scale/slide/typewriter)
- **Background**: subtle dark overlay behind text for readability
- **Line spacing**: generous (1.4-1.6) for easy reading

### educational mode
- **Purpose**: Teaching, explaining, highlighting key terms
- **Text REINFORCES learning**: terms appear in center with emphasis
- **Position**: always "center" (terms in middle of screen)
- **Size**: "large" (64-80px) for emphasis
- **Font**: Inter with bold weight (600-700) for key terms
- **Animation**: scale (0.9→1.0) with brief hold
- **Emphasis**: bold, underline, or highlight color for difficult terms
- **Duration**: terms stay on screen slightly longer (20-30% extra)

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

### Presets by mode

| Mode | Preset | Font | Weight | Size (1080p) | Animation | Use case |
|------|--------|------|--------|--------------|-----------|----------|
| **dramatic** | epic | Bebas Neue | 400 | 96-120px | scale | Powerful openings |
| **dramatic** | cinematic | Playfair Display | 400 | 64-80px | typewriter | Emotional scenes |
| **dramatic** | bold | Oswald | 700 | 72px | slide | Statements |
| **simple** | subtitle | Inter | 400 | 44px | fade | Bottom subtitles |
| **educational** | highlight | Inter | 700 | 72px | scale | Key terms |

### Scene-level text_position (dramatic mode only)

| Position | CSS (Remotion) | FFmpeg drawtext x-position | Effect |
|----------|----------------|---------------------------|--------|
| `left` | `textAlign: "left"` | `x=80` | Dramatic, asymmetric |
| `center` | `textAlign: "center"` | `x=(w-text_w)/2` | Balanced, powerful |
| `right` | `textAlign: "right"` | `x=w-text_w-80` | Modern, editorial |
| `bottom` | `position: "absolute", bottom: 80` | `y=h-120` | Cinematic subtitle |

### Scene-level text_size (dramatic mode only)

| Size | Remotion fontSize (1080p) | FFmpeg fontsize | Lines on screen |
|------|--------------------------|-----------------|-----------------|
| `epic` | 96-120px | 72 | 1-2 |
| `large` | 64-80px | 48 | 2-3 |
| `medium` | 40-56px | 32 | 3-4 |
| `small` | 28-36px | 24 | 4-5 |

### Adaptive sizing (dramatic mode only)

Adjust text_size based on phrase length:
- <= 20 chars: use scene's text_size as-is
- 20-40 chars: reduce fontSize by 15%
- 40-60 chars: reduce fontSize by 25%
- > 60 chars: reduce fontSize by 35% or split into multiple lines

## Simple mode: Subtitle rendering

### FFmpeg subtitle overlay

For simple mode, use FFmpeg's drawtext with a dark background box:

```bash
# Bottom subtitle with dark background
drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='PHRASE TEXT':fontsize=44:x=(w-text_w)/2:y=h-120:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=10
```

### Remotion subtitle component

```tsx
export const SubtitleOverlay: React.FC<{ text: string }> = ({ text }) => {
  return (
    <div style={{
      position: "absolute",
      bottom: 80,
      left: 80,
      right: 80,
      backgroundColor: "rgba(0, 0, 0, 0.7)",
      padding: "20px 30px",
      borderRadius: 8,
    }}>
      <span style={{
        fontFamily: "Inter",
        fontSize: 44,
        fontWeight: 400,
        color: "white",
        textAlign: "center",
        display: "block",
        lineHeight: 1.5
      }}>
        {text}
      </span>
    </div>
  );
};
```

## Educational mode: Term highlighting

### Emphasis techniques

- **Bold**: Use font-weight 600-700
- **Underline**: Add CSS `text-decoration: underline`
- **Highlight color**: Use accent color (e.g., #ffeb3b) for terms
- **Background**: Slight dark background to separate from media

### Remotion term component

```tsx
export const TermHighlight: React.FC<{ term: string; accentColor: string }> = ({ term, accentColor }) => {
  return (
    <div style={{
      position: "absolute",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      padding: "30px 50px",
      borderRadius: 12,
      border: `3px solid ${accentColor}`,
    }}>
      <span style={{
        fontFamily: "Inter",
        fontSize: 72,
        fontWeight: 700,
        color: "white",
        textShadow: `0 0 20px ${accentColor}`,
      }}>
        {term}
      </span>
    </div>
  );
};
```

## Step 3: Apply animations

Each phrase_group gets an animation synced to its `start`/`end` timestamps.

### Animation types

| Animation | Description | Duration | Best for |
|-----------|-------------|----------|----------|
| `fade` | Opacity 0->1->0 | 0.3s in, 0.3s out | All styles, default |
| `slide` | TranslateX -60px->0 | 0.4s ease-out | Minimal, corporate |
| `scale` | Scale 0.8->1.0 | 0.4s ease-out | Epic, cinematic, educational |
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

### Animation selection by mode and preset

| Mode | Preset | Default animation | Alternative |
|------|--------|------------------|-------------|
| **dramatic** | epic | scale | fade for long text |
| **dramatic** | cinematic | typewriter | fade for short phrases |
| **dramatic** | bold | slide | fade |
| **simple** | subtitle | fade | - |
| **educational** | highlight | scale | - |

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

type SubtitleMode = "dramatic" | "simple" | "educational";

interface TypographySceneProps {
  phraseGroups: Array<{ text: string; start: number; end: number }>;
  mode: SubtitleMode;
  preset?: "epic" | "cinematic" | "bold" | "subtitle" | "highlight";
  position?: "left" | "center" | "right" | "bottom";
  size?: "epic" | "large" | "medium" | "small";
  accentColor: string;
  backgroundMedia?: string;
}

export const TypographyScene: React.FC<TypographySceneProps> = ({
  phraseGroups,
  mode,
  preset = "subtitle",
  position = "center",
  size = "medium",
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

  // Simple mode: subtitle at bottom with dark background
  if (mode === "simple") {
    const fadeFrames = Math.round(0.3 * fps);
    const opacity = interpolate(
      localFrame,
      [0, fadeFrames, durationFrames - fadeFrames, durationFrames],
      [0, 1, 1, 0],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );

    return (
      <AbsoluteFill>
        <div style={{
          position: "absolute",
          bottom: 80,
          left: 80,
          right: 80,
          backgroundColor: "rgba(0, 0, 0, 0.7)",
          padding: "20px 30px",
          borderRadius: 8,
          opacity,
        }}>
          <span style={{
            fontFamily: "Inter",
            fontSize: 44,
            fontWeight: 400,
            color: "white",
            textAlign: "center",
            display: "block",
            lineHeight: 1.5
          }}>
            {activeGroup.text}
          </span>
        </div>
      </AbsoluteFill>
    );
  }

  // Educational mode: centered term with emphasis
  if (mode === "educational") {
    const scaleVal = spring({ frame: localFrame, fps, config: { damping: 15, stiffness: 80 } });
    const scale = interpolate(scaleVal, [0, 1], [0.9, 1.0]);

    return (
      <AbsoluteFill>
        <div style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%) scale(${scale})`,
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          padding: "30px 50px",
          borderRadius: 12,
          border: `3px solid ${accentColor}`,
        }}>
          <span style={{
            fontFamily: "Inter",
            fontSize: 72,
            fontWeight: 700,
            color: "white",
            textShadow: `0 0 20px ${accentColor}`,
          }}>
            {activeGroup.text}
          </span>
        </div>
      </AbsoluteFill>
    );
  }

  // Dramatic mode: full cinematic text
  const fadeFrames = Math.round(0.3 * fps);
  const opacity = interpolate(
    localFrame,
    [0, fadeFrames, durationFrames - fadeFrames, durationFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const fontSize = size === "epic" ? 96 : size === "large" ? 64 : size === "medium" ? 48 : 32;
  const fontFamily = preset === "epic" ? "Bebas Neue" : preset === "cinematic" ? "Playfair Display" : preset === "bold" ? "Oswald" : "Inter";

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {backgroundMedia && <img src={backgroundMedia} style={{ opacity: 0.3 }} />}
      <div style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: position === "bottom" ? "flex-end" : "center",
        justifyContent: position === "center" ? "center" : position === "left" ? "flex-start" : "flex-end",
        paddingLeft: position === "left" ? 80 : 0,
        paddingRight: position === "right" ? 80 : 0,
        paddingBottom: position === "bottom" ? 80 : 0,
        opacity
      }}>
        <span style={{
          fontSize,
          color: "white",
          fontFamily,
          fontWeight: preset === "bold" ? 700 : 400,
          textTransform: preset === "epic" ? "uppercase" : "none",
        }}>
          {activeGroup.text}
        </span>
      </div>
    </AbsoluteFill>
  );
};
```

## Step 5: Output

Return to the montage skill:
- Typography configuration for each scene (mode, font, size, position, animation)
- Any font files that need to be loaded
- Timing data synchronized with phrase_groups
- For simple mode: subtitle styling with background
- For educational mode: term highlighting with emphasis effects

## Integration with montage

The montage skill calls this skill for ALL scenes based on the scenario's `subtitle_mode` field. The typography skill:
1. Reads `subtitle_mode` from scenario (dramatic, simple, or educational)
2. Selects font, preset, and styling based on mode
3. For dramatic mode: calculates adaptive sizing based on phrase length
4. Chooses animation type appropriate for the mode
5. Returns rendering instructions (Remotion component or FFmpeg filter) tailored to the mode

## Important

- Always active for all subtitle modes (dramatic, simple, educational)
- Phrase groups must NEVER be split mid-word or mid-expression
- Text must be readable: minimum 24px equivalent on 1080p
- Animations should feel smooth, not jarring: use spring physics in Remotion
- Dark backgrounds with white text is the default; accent color for highlights only
- Simple mode always uses bottom position with dark background overlay
- Educational mode always uses center position with emphasis styling
- Always test with longest phrase first to ensure it fits the screen
