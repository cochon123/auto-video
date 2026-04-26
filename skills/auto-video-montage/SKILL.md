# Auto-Video Montage

Assembles the final video from scenario, media assets, audio, and timestamps.

## When to use

Loaded by the director after all media and audio have been generated. Takes the scenario + assets and produces the final video file.

## Prerequisites

- Scenario JSON from the scenarist
- Media assets downloaded (images/videos in cache)
- TTS audio files generated (one per scene)
- Timestamps JSON (word-level timing from audio)

## Role

You are a video editor. You take all the production assets and assemble them into a polished final video.

## GPU Resource Management

OmniVoice (local TTS) uses ~1.9GB VRAM. These rules prevent OOM crashes:

1. **NEVER run GPU tasks in parallel** — OmniVoice TTS, Whisper timestamps, and any AI media generation must run sequentially
2. **Run TTS first**, then timestamps, then media generation — this order ensures VRAM is freed between tasks
3. **Call `torch.cuda.empty_cache()`** between GPU tasks
4. **If OmniVoice fails** (OOM, CUDA error), fall back to edge-tts:
   ```bash
   python3 ~/.config/auto-video/helpers/tts-generate.sh --provider edge --text "..." --output audio.wav
   ```
5. **edge-tts** uses NO GPU — it's an HTTP API. Always safe to run in parallel with non-GPU tasks.

### Pipeline order (respecting GPU):
```
1. [GPU] OmniVoice TTS for all scenes (sequential)
2. [GPU] Whisper timestamps (sequential, after TTS is done and unloaded)
3. [CPU] fetch_media (can run while GPU is free)
4. [GPU] AI image generation if needed (after fetch)
5. [CPU] Pre-render validation
6. [CPU] FFmpeg assembly (or [GPU] Remotion render)
```

## Step 1: Verify inputs

Check that all required files exist:
```bash
# Check scenario
cat <cache_dir>/scenario.json | python3 -m json.tool > /dev/null

# Check media assets
ls <cache_dir>/media/

# Check audio
ls <cache_dir>/audio/

# Check timestamps
cat <cache_dir>/timestamps.json | python3 -m json.tool > /dev/null
```

If anything is missing, report back to the director.

## Step 2: Pre-render validation

Before any rendering, validate ALL assets. This prevents wasting 5 minutes on a render that will fail.

### Validation checklist output format:

```
Pre-render validation:
✓ Video writer_new.mp4: 30fps ✓ | 12.4s ✓ | 1920x1080 ✓
✓ Video mountain_new.mp4: 30fps ✓ | 24.2s ✓ | 1920x1080 ✓
✗ Video old_forge.mp4: 25fps ✗ → converting to 30fps...
✓ Audio: 62.6s | fr-FR-HenriNeural
✓ Total frames: 1886 = 62.9s ≈ 62.6s audio ✓
```

### Validation rules:

For each video asset:
- **FPS**: must match target (default 30fps). If mismatch, convert with FFmpeg: `ffmpeg -i input.mp4 -r 30 -c:v libx264 output_30fps.mp4`
- **Resolution**: must match target (default 1920x1080). If mismatch, scale: `ffmpeg -i input.mp4 -vf scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2 output.mp4`
- **Duration**: must be >= scene duration. If shorter, loop or use slow zoom
- **Codec**: must be H.264. If not, re-encode

For audio:
- **Total audio duration** must approximately match **sum of scene durations** (tolerance: 2s)
- **Sample rate**: doesn't matter (FFmpeg handles resampling)

For frame count:
- **Total frames** = sum of (scene_duration_s * fps) for all scenes
- Must match total audio duration within tolerance

If any validation fails:
1. Attempt auto-fix (convert fps, scale resolution, re-encode)
2. If auto-fix fails, report to director and ask for guidance

### Validation helper command:
```bash
python3 -c "
import subprocess, json, sys
from pathlib import Path

media_dir = Path(sys.argv[1])
fps_target = int(sys.argv[2]) if len(sys.argv) > 2 else 30
width_target = int(sys.argv[3]) if len(sys.argv) > 3 else 1920
height_target = int(sys.argv[4]) if len(sys.argv) > 4 else 1080

for f in sorted(media_dir.iterdir()):
    if f.suffix not in ['.mp4', '.mov', '.avi', '.webm']:
        continue
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=r_frame_rate,width,height,codec_name,duration',
         '-of', 'json', str(f)],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout)['streams'][0]
    w, h = info.get('width',0), info.get('height',0)
    codec = info.get('codec_name','?')
    fps_str = info.get('r_frame_rate','0/1')
    fps = eval(fps_str) if '/' in fps_str else float(fps_str)
    dur = float(info.get('duration', 0))
    
    issues = []
    if abs(fps - fps_target) > 1: issues.append(f'{fps:.0f}fps X')
    else: issues.append(f'{fps:.0f}fps OK')
    if w != width_target or h != height_target: issues.append(f'{w}x{h} X')
    else: issues.append(f'{w}x{h} OK')
    
    status = 'X' if 'X' in ' '.join(issues) else 'OK'
    print(f'{status} {f.name}: {" | ".join(issues)} | {dur:.1f}s')
" <cache_dir>/media/ 30 1920 1080
```

## Step 3: Choose assembly method

### Method A: Remotion (if enabled in config)

Use when: `config.yaml → remotion.enabled = true`

For scenes with `render_method: "remotion"`:
1. Load the `remotion-render` skill for rendering guidance
2. Load the `remotion-best-practices` skill for composition patterns
3. For each Remotion scene, render with:
   ```bash
   python3 ~/.config/auto-video/helpers/video-compose.sh \
     --method remotion \
     --scenario <cache_dir>/scenario.json \
     --audio-dir <cache_dir>/audio/ \
     --timestamps <cache_dir>/timestamps.json \
     --media-dir <cache_dir>/media/ \
     --output <output_path> \
     --config ~/.config/auto-video/config.yaml
   ```

### Method B: FFmpeg (default/fallback)

Use when: Remotion is disabled OR as fallback for non-Remotion scenes.

The helper handles:
1. **Per-scene video clips**: For each scene, combine media + audio
   - Images: Apply Ken Burns effect (pan/zoom)
   - Videos: Scale to 1920x1080, trim to scene duration
   - Add audio track
2. **Transitions**: Apply fade/dissolve between scenes
3. **Subtitles**: Optional, burned-in from narration text
4. **Final concat**: Merge all scene clips into one video

```bash
python3 ~/.config/auto-video/helpers/video-compose.sh \
  --method ffmpeg \
  --scenario <cache_dir>/scenario.json \
  --audio-dir <cache_dir>/audio/ \
  --timestamps <cache_dir>/timestamps.json \
  --media-dir <cache_dir>/media/ \
  --output ~/Videos/auto-video/<video_id>.mp4 \
  --config ~/.config/auto-video/config.yaml
```

## Step 4: Typography (for all subtitle modes)

The scenario has a `subtitle_mode` field (dramatic, simple, or educational). Typography is needed for ALL modes:

### Load the typography skill

For ALL scenarios (regardless of subtitle_mode), load the `auto-video-typography` skill:

```bash
# Pass the entire scenario, the typography skill will read subtitle_mode
# No need to pass mode separately
```

### Typography mode behaviors

| Mode | When typography is applied | What it does |
|------|---------------------------|--------------|
| **dramatic** | All scenes | Full-screen text with fonts, animations, epic sizing |
| **simple** | All scenes | Bottom subtitles with dark background, clean sans-serif |
| **educational** | All scenes | Center-highlighted terms with emphasis, bold/underline |

### Apply typography during assembly

- For FFmpeg: typography skill returns drawtext filters appropriate to mode
- For Remotion: typography skill provides the right component (TypographyScene, SubtitleOverlay, or TermHighlight)
- The `text_position` and `text_size` fields from each scene guide the typography skill

### No typography?

If `subtitle_mode` is absent or malformed, default to **simple** (bottom subtitles).

## Step 5: FFmpeg montage details (for manual work or troubleshooting)

If you need to build the video manually instead of using the helper:

### Scene clip from image + audio + Ken Burns
```bash
ffmpeg -loop 1 -i scene_image.jpg -i scene_audio.wav \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,
       pad=1920:1080:(ow-iw)/2:(oh-ih)/2,
       zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=900:s=1920x1080:fps=30" \
  -c:v libx264 -preset slow -crf 18 \
  -c:a aac -b:a 192k \
  -shortest scene_clip.mp4
```

### Concat with crossfade
```bash
# Create concat file with crossfade
ffmpeg -i clip1.mp4 -i clip2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=<time>,
                    [0:a][1:a]acrossfade=d=0.5" \
  -c:v libx264 -preset slow -crf 18 output.mp4
```

### Add subtitles (simple mode)

For simple subtitle mode with FFmpeg:

```bash
ffmpeg -i video.mp4 -vf "subtitles=subs.srt:force_style='FontSize=24,PrimaryColour=&Hffffff&'" -c:v libx264 output_with_subs.mp4
```

For more control, use drawtext directly (typography skill provides the filter):

```bash
# Simple bottom subtitle with dark background
ffmpeg -i video.mp4 -vf "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='PHRASE':fontsize=44:x=(w-text_w)/2:y=h-120:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=10" -c:v libx264 output.mp4
```

## Step 6: Quality check

After rendering:
1. Verify the file exists and has reasonable size: `ls -lh <output>`
2. Get duration: `ffprobe -v error -show_entries format=duration -of csv=p=0 <output>`
3. Verify duration matches scenario total_duration_s (within 2s tolerance)

## Step 7: Output

Return to the director:
- Output video path
- Actual duration
- Any warnings or issues encountered

## Handling edit requests

When the user requests changes via timestamps:

1. **"At 0:XX, change the image"** → identify scene → re-fetch media → re-render that scene clip → re-concat
2. **"Shorten the intro"** → adjust scenario timing → re-render affected scenes → re-concat
3. **"Add transition at 0:XX"** → find the scene boundary → adjust concat filter → re-concat
4. **"Change narration at 0:XX"** → re-run TTS for that scene → update timestamps → typography adjusts based on `subtitle_mode` → re-render → re-concat

For small edits, you only need to re-process affected scenes and re-concat, not the entire video.
