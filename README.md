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
[Director] -- analyzes intent, delegates work
    |
    +-- [Writer] -- researches topic, writes script
    |
    +-- [Scenarist] -- plans visuals, phrase groups, timing
    |
    +-- [Helpers] -- fetch media, generate TTS, timestamps
    |
    +-- [Montage] -- validates assets, assembles video
    |   |
    |   +-- [Typography] -- cinematic text overlays (optional)
    |
    v
Finished video (.mp4)
```

### The 6 skills

| Skill | What it does |
|-------|-------------|
| **setup** | Interactive setup: config, API keys, GPU check |
| **director** | Main orchestration — understands your request, runs the pipeline |
| **writer** | Researches a topic and writes a narrated script |
| **scenarist** | Plans visuals, phrase groups, timing, asset queries |
| **montage** | Pre-render validation, FFmpeg/Remotion assembly |
| **typography** | Cinematic text overlays with fonts, presets, animations |

### What's included by default

| Component | Default | Alternatives |
|-----------|---------|-------------|
| **TTS** | OmniVoice (local, GPU, 600+ languages, 1.9GB VRAM) | edge-tts (free, cloud), ElevenLabs, OpenAI TTS |
| **Media** | Pexels (free API) + DuckDuckGo Images | Pixabay, AI-generated |
| **Assembly** | FFmpeg (always available) | Remotion (React-based, more control) |
| **Subtitles** | Phrase groups (auto-generated, synced to narration) | SRT, burned-in |
| **Resolution** | 1920x1080 @ 30fps | Configurable |
| **Languages** | French (default) | Any language OmniVoice/edge-tts supports |

### Typography & cinematic mode

When you request a "cinematic" or "dramatic" video:
- Text overlays with Google Fonts (Bebas Neue, Playfair Display, Inter, Oswald)
- 4 presets: epic, minimal, corporate, cinematic
- 4 animations: fade, slide, scale, typewriter
- Adaptive sizing based on phrase length
- Phrase groups never split mid-expression

### GPU management

If you have an NVIDIA GPU (recommended 2GB+ VRAM):
- OmniVoice TTS runs locally, no API needed
- GPU tasks run sequentially (TTS -> Whisper timestamps -> media generation)
- Automatic fallback to edge-tts if GPU is busy or unavailable

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
~/.agents/skills/auto-video-{setup,director,writer,scenarist,montage,typography}/
~/.config/auto-video/
  config.yaml          # your configuration (API keys, TTS, language)
  helpers/             # Python/Shell helpers
  cache/               # media + audio cache
```

## Configuration

Config lives at `~/.config/auto-video/config.yaml`:

```yaml
tts:
  provider: omnivoice          # omnivoice | edge | elevenlabs | openai
  instruct: "female, young adult, moderate pitch"
  language: fr

media:
  mode: stock                  # stock | generate | hybrid
  sources:
    - pexels
    - duckduckgo
  pexels_api_key: null

video:
  resolution: 1920x1080
  fps: 30
  format: mp4

remotion:
  enabled: false
```

## Modularity

Everything is swappable:
- **TTS provider**: Switch between OmniVoice (local), edge-tts (free cloud), ElevenLabs, or OpenAI by changing one config line
- **Media sources**: Pexels, DuckDuckGo, Pixabay, AI generation — mix and match
- **Assembly engine**: FFmpeg for reliability, Remotion for creative control
- **Skills**: Each skill is a standalone markdown file — edit, extend, or replace any of them
- **Helpers**: Python scripts that can be called independently or swapped for your own

## Requirements

- Python 3.10+
- FFmpeg (`apt install ffmpeg` or `brew install ffmpeg`)
- NVIDIA GPU recommended for local TTS (not required — edge-tts works without one)
- API keys: Pexels (free), optionally ElevenLabs or OpenAI

## Project structure

```
auto-video/
  skills/
    auto-video-setup/SKILL.md
    auto-video-director/SKILL.md
    auto-video-writer/SKILL.md
    auto-video-scenarist/SKILL.md
    auto-video-montage/SKILL.md
    auto-video-typography/SKILL.md
    shared/
      helpers/
        fetch-media.sh
        tts-generate.sh
        tts-timestamps.sh
        video-compose.sh
      templates/
        config.yaml.example
        remotion-templates/
    install.sh
  README.md
  LICENSE
```

## License

MIT
