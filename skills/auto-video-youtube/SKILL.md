---
name: auto-video-youtube
description: YouTube upload and management — handles OAuth, uploads, metadata, and channel info
---

# Auto-Video YouTube

Upload videos to YouTube directly from the pipeline. Handles OAuth 2.0 authentication, metadata, and publishing.

## When to use

When the user asks to upload/publish a video to YouTube. Triggers: "upload to youtube", "publish to youtube", "youtube upload". Also: "youtube channel stats", "youtube channel info".

## Prerequisites

- Google Cloud project with YouTube Data API v3 enabled
- OAuth 2.0 client secret JSON (type: "Web application", redirect URI `http://127.0.0.1:7777/`)
- Python packages: `google-api-python-client`, `google-auth-oauthlib`
- Helper: `~/.config/auto-video/helpers/youtube-upload.py`
- YouTube enabled in `~/.config/auto-video/config.yaml`

## Configuration

```yaml
youtube:
  enabled: true
  client_secret: ~/.config/auto-video/youtube_client_secret.json
  credentials_file: ~/.config/auto-video/youtube_credentials.json
  redirect_host: "127.0.0.1"
  redirect_port: 7777
  default_privacy: private
  default_category_id: "22"
  default_license: creativeCommon
  notify_subscribers: true
  made_for_kids: false
```

## Authentication

First time requires browser-based OAuth consent:

```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py auth \
  --client-secret ~/.config/auto-video/youtube_client_secret.json \
  --host 127.0.0.1 --port 7777
```

Credentials saved to `~/.config/auto-video/youtube_credentials.json` (chmod 600). Subsequent uploads reuse them automatically.

## Upload

```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py upload \
  --config ~/.config/auto-video/config.yaml \
  --title "Video Title" \
  --description "Description..." \
  --tags "tag1,tag2,tag3" \
  --privacy private \
  --json \
  /path/to/video.mp4
```

Returns JSON: `{"id": "...", "url": "https://youtube.com/watch?v=...", "title": "...", "privacy": "..."}`

### Scheduled publish

```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py upload \
  --config ~/.config/auto-video/config.yaml \
  --title "Title" --privacy private \
  --publish-at "2026-05-01T18:00:00Z" \
  /path/to/video.mp4
```

Note: `--publish-at` requires `--privacy public`. For scheduled, upload as private then set publish time in YouTube Studio.

### Metadata from pipeline

When uploading after video generation, use:
- `--title`: video topic or user-specified title
- `--description`: auto-generated from script summary
- `--tags`: from topic and sector keywords
- `--privacy`: from config `default_privacy` or user override

### Category auto-detection from sector

| Sector | Category ID | Category |
|--------|------------|----------|
| tech | 28 | Science & Technology |
| politics | 25 | News & Politics |
| science | 28 | Science & Technology |
| culture | 24 | Entertainment |
| education | 27 | Education |
| default | 22 | People & Blogs |

## Channel info

```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py info \
  --config ~/.config/auto-video/config.yaml
```

Returns channel name, subscribers, video count, total views, total duration. Add `--json` for machine-readable output.

## Error handling

- **Client secret not found** → place OAuth JSON at configured path
- **redirect_uri_mismatch** → ensure `http://127.0.0.1:7777/` is registered in Google Cloud Console
- **insufficientPermissions** → re-auth with `youtube-upload.py auth`
- **quotaExceeded** → YouTube daily quota reached, wait or request increase
- **Upload fails mid-way** → API supports resumable uploads, retry same command

## Security

- Credentials files saved with chmod 600
- Never commit client secret or credentials to version control
- OAuth tokens revocable at https://myaccount.google.com/permissions
