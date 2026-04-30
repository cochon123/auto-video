# auto-video

AI-native video generation. Give your AI agent a topic, get a finished video back.

Works with **opencode**, **Claude Code**, **Codex**, **Cursor**, **Cline**, or any AI agent that supports skills/instructions.

## Quick start

Tell your AI agent:

> Look at https://github.com/cochon123/auto-video and specifically the auto-video-setup skill. Follow the installation steps.

That's it. The agent will:
1. Install the skills and helpers
2. Check your GPU, TTS, and API key configuration
3. Walk you through any setup needed

Then ask it to make a video:
> Make a 60-second video about the latest AI funding rounds

## How it works

auto-video is a **skill-based architecture** — not a library, not a CLI. Each skill is a markdown file that tells an AI agent exactly what to do, step by step.

```
Your request
    |
    v
[auto-video] -- research, script, scenario, assembly, delivery
    |
    +-- [Helpers] -- fetch media, generate TTS, timestamps
    |
    +-- [YouTube] -- upload to YouTube (optional)
    |
    v
Finished video (.mp4)
```

### The 3 skills

| Skill | What it does |
|-------|-------------|
| **auto-video** | Main pipeline: research, script writing, visual scenario, media assembly, delivery |
| **auto-video-setup** | Interactive setup: config, API keys, GPU check |
| **auto-video-youtube** | Upload finished videos directly to YouTube |

### What's included by default

| Component | Default | Alternatives |
|-----------|---------|-------------|
| **TTS** | OpenAI TTS (cloud) | edge-tts (free), OmniVoice (local, GPU), ElevenLabs |
| **Media** | Pexels (free API) + DuckDuckGo Images | Pixabay, AI-generated |
| **Assembly** | FFmpeg (always available) | Remotion (React-based, more control) |
| **Subtitles** | Simple bottom subtitles (synced to narration) | Dramatic (cinematic text), Educational (term highlights) |
| **Resolution** | 1920x1080 @ 30fps | Configurable |
| **Languages** | French (default) | Any language your TTS supports |

### Text overlay modes

- **Simple (default):** Bottom subtitles, clean sans-serif, fade in/out. Text supports the visual.
- **Dramatic:** BIG cinematic text, display fonts (Bebas Neue, Playfair Display), heavy animations, accent color highlights on key words. Text IS the visual.
- **Educational:** Centered key terms, large bold font, scale animations, accent borders. Text reinforces learning.

### GPU management

If you have an NVIDIA GPU (recommended 2GB+ VRAM):
- OmniVoice TTS runs locally, no API needed
- GPU tasks run sequentially (TTS -> Whisper timestamps -> media generation)
- Automatic fallback to edge-tts if GPU is busy or unavailable

### YouTube uploads

Upload finished videos directly to your YouTube channel:
- OAuth 2.0 authentication (one-time browser consent)
- Auto-filled metadata: title, description, tags from the pipeline
- Privacy control: private (default), unlisted, or public
- Category auto-detection from video sector (tech, education, etc.)
- Creative Commons or standard YouTube license
- Scheduled publishing support

Setup: during auto-video-setup, enable YouTube and provide your Google Cloud OAuth client secret (with YouTube Data API v3 enabled and redirect URI `http://127.0.0.1:7777/`).

## Installation

### Automatic (recommended)

```bash
bash <(curl -s https://raw.githubusercontent.com/cochon123/auto-video/main/skills/install.sh)
```

Or tell your AI agent:
> Look at https://github.com/cochon123/auto-video and load the auto-video-setup skill. Follow the setup steps.

### Manual

```bash
# Clone
git clone https://github.com/cochon123/auto-video.git
cd auto-video

# Install (for Claude Code / generic agents)
bash skills/install.sh

# Install (for opencode too)
bash skills/install.sh --opencode

# Install (for all supported agents)
bash skills/install.sh --all-agents

# Edit config
nano ~/.config/auto-video/config.yaml
```

### What gets installed

```
~/.agents/skills/auto-video/
~/.agents/skills/auto-video-setup/
~/.agents/skills/auto-video-youtube/
~/.config/auto-video/
  config.yaml          # your configuration (API keys, TTS, language)
  helpers/             # Python helpers
  cache/               # media + audio cache
```

## Configuration

Config lives at `~/.config/auto-video/config.yaml`:

```yaml
tts:
  provider: openai             # openai | edge | omnivoice | elevenlabs
  voice: alloy
  language: fr

media:
  mode: api                    # api | local | generated | hybrid
  providers:
    - name: pexels
      api_key: null
    - name: duckduckgo

video:
  default_format: short        # short | long
  default_language: fr
  gpu_acceleration: auto

remotion:
  enabled: false

youtube:
  enabled: false
  default_privacy: private
  default_license: creativeCommon
```

## Modularity

Everything is swappable:
- **TTS provider**: Switch between OpenAI, edge-tts, OmniVoice, or ElevenLabs by changing one config line
- **Media sources**: Pexels, DuckDuckGo, Pixabay, AI generation — mix and match
- **Assembly engine**: FFmpeg for reliability, Remotion for creative control
- **Skills**: Each skill is a standalone markdown file — edit, extend, or replace any of them
- **Helpers**: Python scripts that can be called independently or swapped for your own

## Requirements

- Python 3.10+
- FFmpeg (`apt install ffmpeg` or `brew install ffmpeg`)
- NVIDIA GPU recommended for local TTS (not required — edge-tts and OpenAI work without one)
- API keys: Pexels (free), optionally ElevenLabs or OpenAI
- For YouTube uploads: `google-api-python-client`, `google-auth-oauthlib`, and a Google Cloud OAuth client secret

## Project structure

```
auto-video/
  skills/
    auto-video/SKILL.md          # main pipeline
    auto-video-setup/SKILL.md    # interactive setup
    auto-video-youtube/SKILL.md  # YouTube upload
    shared/
      helpers/
        fetch-media.py
        tts-generate.py
        tts-timestamps.py
        build-phrase-groups.py
        validate-assets.py
        video-compose.py
        recalibrate-timestamps.py
        youtube-upload.py
      templates/
        config.yaml.example
        remotion-templates/
    install.sh
  README.md
  LICENSE
```

## License

MIT
