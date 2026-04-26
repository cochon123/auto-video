# Auto-Video Setup

Interactive setup skill that configures all auto-video skills and helpers for the user's system.

## When to use

When the user says "setup auto-video", "install auto-video", "configure auto-video", or when auto-video helpers are missing/broken.

## Overview

You are an interactive setup agent. You will guide the user through configuring auto-video step by step. At the end, the user's system will have:

- All 5 auto-video skills installed in `~/.agents/skills/`
- Helpers configured in `~/.config/auto-video/helpers/`
- A valid `~/.config/auto-video/config.yaml`
- Remotion installed (optional)

## Setup flow

Execute these steps IN ORDER. At each step, ask the user for input before proceeding.

---

### Phase 0: Install skills

1. Copy all auto-video skill folders to `~/.agents/skills/`:
   ```bash
   mkdir -p ~/.agents/skills
   cp -r <repo>/skills/auto-video-* ~/.agents/skills/
   ```
2. If the user uses opencode specifically, ALSO copy to `~/.config/opencode/skill/`:
   ```bash
   mkdir -p ~/.config/opencode/skill
   cp -r <repo>/skills/auto-video-* ~/.config/opencode/skill/
   ```
3. Tell the user: "Skills installed. Now let's configure each module."

---

### Phase 1: Media sources

Ask the user:

> **How should the agent fetch media (images/videos) for video scenes?**
>
> 1. **API** — fetch from stock photo/video APIs (default: Pexels for artistic, DuckDuckGo for factual)
> 2. **Local folder** — use media already present on disk
> 3. **AI generation** — generate images with a local or API model
> 4. **Combination** — mix of the above

Based on their answer:

#### If API selected:
- Ask which services. Default options: **Pexels** (artistic/stock), **DuckDuckGo** (factual/photo-only), **Pixabay**.
- For Pexels/Pixabay: ask for API key. Test with:
  ```bash
  python3 ~/.config/auto-video/helpers/fetch_media.py --test pexels --api-key <KEY>
  ```
- For DuckDuckGo: no key needed, just test:
  ```bash
  python3 ~/.config/auto-video/helpers/fetch_media.py --test duckduckgo
  ```

#### If local folder selected:
- Ask for the path to their media folder.
- Verify it exists and has files: `ls <path> | head -5`

#### If AI generation selected:
- Ask: **Local model** or **API**?
  - **Local**: Search the web for how to run image generation with their hardware. Ask where their model is stored. Common tools: `diffusers` (Python), ComfyUI, Automatic1111. Test generation.
  - **API**: Default to OpenAI DALL-E / Stability AI. Ask for API key. Test with a simple prompt.

#### If combination:
- Go through each sub-option above as needed.

---

### Phase 2: Text-to-Speech

Ask the user:

> **How should the agent generate voice narration?**
>
> 1. **Local TTS (OmniVoice)** — GPU-accelerated, 600+ languages, voice design via instruct attributes (e.g. "female, young adult, british accent"). No API key needed. Needs ~1.9GB VRAM.
> 2. **Edge TTS** — free, uses Microsoft Edge API. No API key, no GPU needed. Good fallback for low-VRAM systems.
> 3. **API TTS** — cloud service (ElevenLabs, OpenAI TTS)
> 4. **I already have audio files** — skip TTS, provide audio manually

Based on their answer:

#### If Local TTS (OmniVoice) — default:
- Ask: **What voice instruct do you want?** Valid attributes: male, female, child, teenager, young adult, middle-aged, elderly, low pitch, moderate pitch, high pitch, very low pitch, very high pitch, whisper, american accent, british accent, australian accent, canadian accent, indian accent, japanese accent, korean accent, portuguese accent, russian accent. Comma-separated, e.g. "female, young adult, british accent"
- Check GPU VRAM: `nvidia-smi --query-gpu=memory.total --format=csv,noheader`. If < 2GB, recommend Edge TTS instead.
- Test: generate sample audio (24kHz WAV) and save to `~/Downloads/tts_test.wav`:
  ```bash
  python3 ~/.config/auto-video/helpers/tts_generate.py \
    --text "Hello world, let's vibe edit a video" \
    --output ~/Downloads/tts_test.wav \
    --provider omnivoice \
    --instruct "<user's voice instruct, e.g. female, young adult, moderate pitch>" \
    --config ~/.config/auto-video/config.yaml
  ```
- Ask the user to listen and confirm.

#### If Edge TTS:
- Ask for the voice name (default: `en-US-AvaNeural` for English, `fr-FR-DeniseNeural` for French).
- Test:
  ```bash
  python3 ~/.config/auto-video/helpers/tts_generate.py \
    --text "Hello world, let's vibe edit a video" \
    --output ~/Downloads/tts_test.wav \
    --provider edge --voice "<voice>"
  ```
- Ask the user to listen and confirm.

#### If API TTS:
- Ask which provider (ElevenLabs, OpenAI TTS, etc.)
- Ask for API key and preferred voice.
- Test: generate "Hello world, let's vibe edit a video" and save to `~/Downloads/tts_test.wav`:
  ```bash
  python3 ~/.config/auto-video/helpers/tts_generate.py \
    --text "Hello world, let's vibe edit a video" \
    --output ~/Downloads/tts_test.wav \
    --provider <provider> --api-key <KEY> --voice <voice>
  ```
- Ask the user to listen and confirm.

---

### Phase 3: Remotion (optional)

Ask the user:

> **Do you want to install Remotion for advanced motion graphics?**
> This enables animated intros, data visualizations, semantic motion scenes, etc.
> Without it, videos will use simple FFmpeg transitions (fade/dissolve).
>
> y/n?

If yes:
1. Check Node.js: `node --version` (need >=18)
2. Install Remotion project to `~/.config/auto-video/remotion/`:
   ```bash
   mkdir -p ~/.config/auto-video/remotion
   cp -r <repo>/skills/_shared/remotion/* ~/.config/auto-video/remotion/
   cd ~/.config/auto-video/remotion && npm install
   ```
3. Verify: `npx remotion versions`
4. Load the remotion-render and remotion-best-practices skills:
   ```bash
   # These should already be in ~/.agents/skills/ if installed
   ls ~/.agents/skills/remotion-render/SKILL.md
   ls ~/.agents/skills/remotion-best-practices/SKILL.md
   ```
5. If missing, tell the user to install them.

---

### Phase 4: Save configuration

Write the final config to `~/.config/auto-video/config.yaml`:

```yaml
# Auto-Video Configuration
# Generated by auto-video-setup

media:
  mode: <api|local|generated|hybrid>
  providers:
    - name: pexels
      api_key: <KEY>
    - name: duckduckgo
  local_path: <path or null>
  generation:
    mode: <local|api>
    model: <model_name>
    api_key: <KEY or null>
    model_path: <path or null>

tts:
  mode: <local|api|manual>
  provider: <omnivoice|edge|elevenlabs|openai>
  voice: <voice_name or null>
  instruct: <voice attributes for OmniVoice, e.g. "female, young adult, moderate pitch">
  api_key: <KEY or null>
  language: <lang>

remotion:
  enabled: <true|false>
  project_path: ~/.config/auto-video/remotion

paths:
  helpers: ~/.config/auto-video/helpers
  cache: ~/.config/auto-video/cache
  output: ~/Videos/auto-video

video:
  default_format: <short|long>
  default_language: <fr|en>
  gpu_acceleration: auto
```

Create required directories:
```bash
mkdir -p ~/.config/auto-video/{helpers,cache}
mkdir -p ~/Videos/auto-video
```

Install helpers:
```bash
cp <repo>/skills/_shared/helpers/*.py ~/.config/auto-video/helpers/
chmod +x ~/.config/auto-video/helpers/*.py
```

---

### Phase 5: Final verification

Run a full integration test:
```bash
python3 ~/.config/auto-video/helpers/fetch_media.py --test-all
python3 ~/.config/auto-video/helpers/tts_generate.py --test --config ~/.config/auto-video/config.yaml
```

If Remotion enabled:
```bash
npx remotion render ~/.config/auto-video/remotion/index.ts Intro ~/Downloads/test_intro.mp4 --props '{"title":"Test","subtitle":"Auto-Video Setup","accentColor":"#7ad7ff"}'
```

Tell the user:
> Setup complete! You can now ask your AI agent to generate videos. Try: "Make a 60-second video about the latest AI news"

---

## Important notes

- ALWAYS ask before running destructive commands or installing packages.
- If a step fails, troubleshoot with the user before moving on.
- Store API keys ONLY in `~/.config/auto-video/config.yaml` with `chmod 600`.
- The config file is the single source of truth. All other skills read from it.
- If the user's AI harness is opencode, skills should also be copied to `~/.config/opencode/skill/` for auto-discovery.
