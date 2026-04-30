---
name: auto-video-setup
description: Interactive setup for configuring auto-video — media sources, TTS, Remotion, YouTube
---

# Auto-Video Setup

Interactive setup that configures auto-video for the user's system.

## When to use

When the user says "setup auto-video", "install auto-video", "configure auto-video", or when helpers/config are missing.

## What gets configured

- Helpers installed in `~/.config/auto-video/helpers/`
- Valid `~/.config/auto-video/config.yaml`
- Remotion installed (optional)
- YouTube upload configured (optional)

Execute these phases IN ORDER. Ask the user for input at each step.

---

## Phase 1: Install skills + helpers

```bash
# Skills
mkdir -p ~/.agents/skills
cp -r <repo>/skills/auto-video* ~/.agents/skills/

# If using opencode
mkdir -p ~/.config/opencode/skill
cp -r <repo>/skills/auto-video* ~/.config/opencode/skill/

# Helpers
mkdir -p ~/.config/auto-video/{helpers,cache}
mkdir -p ~/Videos/auto-video
cp <repo>/skills/shared/helpers/* ~/.config/auto-video/helpers/
chmod +x ~/.config/auto-video/helpers/*
```

If config doesn't exist yet:
```bash
cp <repo>/skills/shared/templates/config.yaml.example ~/.config/auto-video/config.yaml
chmod 600 ~/.config/auto-video/config.yaml
```

---

## Phase 2: Media sources

Ask: **How should the agent fetch media?**

1. **API** — Pexels (artistic), DuckDuckGo (factual, no key needed), Pixabay
2. **Local folder** — use existing media on disk
3. **AI generation** — local (diffusers, ComfyUI) or API (DALL-E, Stability)
4. **Combination** — mix of the above

For API: test with `python3 ~/.config/auto-video/helpers/fetch-media.py --test <source> [--api-key <KEY>]`
For local: verify path exists and has files
For AI generation: search for setup instructions matching their hardware, test generation

---

## Phase 3: Text-to-Speech

Ask: **How should the agent generate voice narration?**

1. **Local TTS (OmniVoice)** — GPU-accelerated, ~1.9GB VRAM, voice design via instruct attributes
2. **Edge TTS** — free Microsoft Edge API, no GPU needed, good fallback
3. **API TTS** — cloud service (ElevenLabs, OpenAI TTS)
4. **Manual** — skip TTS, provide audio files

For OmniVoice: check GPU VRAM (`nvidia-smi`), test with `--provider omnivoice --instruct "female, young adult, moderate pitch"`
For Edge TTS: test with `--provider edge --voice "en-US-AvaNeural"`
For API: test with `--provider <provider> --api-key <KEY> --voice <voice>`

Save test audio to `~/Downloads/tts_test.wav`, ask user to confirm.

---

## Phase 4: Remotion (optional)

Ask: **Install Remotion for advanced motion graphics?** (y/n)

If yes:
1. Check Node.js >= 18: `node --version`
2. Install: `cp -r <repo>/skills/shared/templates/remotion-templates/* ~/.config/auto-video/remotion/ && cd ~/.config/auto-video/remotion && npm install`
3. Verify: `npx remotion versions`

---

## Phase 5: YouTube upload (optional)

Ask: **Enable YouTube uploads?** (y/n)

If yes:
1. Need OAuth 2.0 client secret from Google Cloud Console (YouTube Data API v3, redirect URI `http://127.0.0.1:7777/`)
2. Copy to `~/.config/auto-video/youtube_client_secret.json`, chmod 600
3. Install: `pip install google-api-python-client google-auth-oauthlib`
4. Authenticate: `python3 ~/.config/auto-video/helpers/youtube-upload.py auth --client-secret ~/.config/auto-video/youtube_client_secret.json --host 127.0.0.1 --port 7777`
5. Verify: `python3 ~/.config/auto-video/helpers/youtube-upload.py info --config ~/.config/auto-video/config.yaml`
6. Ask defaults: privacy (private/unlisted/public), license (creativeCommon/youtube), notify subscribers

---

## Phase 6: Save config + verify

Write final `~/.config/auto-video/config.yaml` with all chosen settings. Schema:

```yaml
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

tts:
  mode: <api|local|manual>
  provider: <openai|omnivoice|edge|elevenlabs>
  voice: <voice or null>
  api_key: <KEY or null>
  language: <lang>

remotion:
  enabled: <true|false>
  project_path: ~/.config/auto-video/remotion

youtube:
  enabled: <true|false>
  client_secret: ~/.config/auto-video/youtube_client_secret.json
  credentials_file: ~/.config/auto-video/youtube_credentials.json
  redirect_host: "127.0.0.1"
  redirect_port: 7777
  default_privacy: <private|unlisted|public>
  default_license: <creativeCommon|youtube>

paths:
  helpers: ~/.config/auto-video/helpers
  cache: ~/.config/auto-video/cache
  output: ~/Videos/auto-video

video:
  default_format: <short|long>
  default_language: <fr|en>
  gpu_acceleration: auto
```

Run verification:
```bash
python3 ~/.config/auto-video/helpers/fetch-media.py --test-all
python3 ~/.config/auto-video/helpers/tts-generate.py --test --config ~/.config/auto-video/config.yaml
```

Tell the user: **Setup complete! Try: "Make a 60-second video about the latest AI news"**

## Notes

- Ask before running destructive commands or installing packages
- Store API keys ONLY in config.yaml with chmod 600
- If a step fails, troubleshoot before moving on
