# Auto-Video YouTube

Upload finished videos to YouTube directly from the pipeline. Handles OAuth 2.0 authentication, metadata, and upload.

## When to use

When the user asks to upload a video to YouTube, publish to YouTube, or when the director pipeline finishes and the user wants to publish. Triggers: "upload to youtube", "publish to youtube", "send to youtube", "youtube upload", "post to youtube".

Also used to check YouTube channel info: "youtube channel stats", "how many videos on my channel", "youtube channel info".

## Prerequisites

- A Google Cloud project with the YouTube Data API v3 enabled
- An OAuth 2.0 client secret JSON file (type: "Web application")
- The redirect URI `http://127.0.0.1:7777/` registered in the Google Cloud Console
- Python packages: `google-api-python-client`, `google-auth-oauthlib` (`pip install google-api-python-client google-auth-oauthlib`)
- The helper script `youtube-upload.py` installed at `~/.config/auto-video/helpers/`

## Configuration

YouTube settings live in `~/.config/auto-video/config.yaml` under the `youtube` key:

```yaml
youtube:
  enabled: true
  client_secret: ~/.config/auto-video/youtube_client_secret.json
  credentials_file: ~/.config/auto-video/youtube_credentials.json
  redirect_host: "127.0.0.1"
  redirect_port: 7777
  default_privacy: private          # private | unlisted | public
  default_tags: []
  default_category_id: "22"         # 22 = People & Blogs
  default_license: creativeCommon   # creativeCommon | youtube
  notify_subscribers: true
  made_for_kids: false
```

## Authentication flow

The first time a YouTube action is performed, the user must authenticate:

1. The helper opens a browser to the Google OAuth consent screen
2. The user signs in and grants "Manage your YouTube videos" permission
3. Credentials are saved to `~/.config/auto-video/youtube_credentials.json` (chmod 600)
4. Subsequent uploads reuse the saved credentials automatically

To pre-authenticate (recommended during setup):
```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py auth \
  --client-secret ~/.config/auto-video/youtube_client_secret.json \
  --host 127.0.0.1 --port 7777
```

## Upload a video

### From the pipeline (post-montage)

After the montage skill produces a final `.mp4`:

```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py upload \
  --config ~/.config/auto-video/config.yaml \
  --title "My Video Title" \
  --description "Video description here..." \
  --tags "tag1,tag2,tag3" \
  --privacy private \
  --json \
  /path/to/final_video.mp4
```

This returns JSON:
```json
{
  "id": "dQw4w9WgXcQ",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "My Video Title",
  "privacy": "private"
}
```

### From the director skill

The director skill calls this after a successful montage, if the user requested YouTube upload. It passes:
- `--title`: the video topic or user-specified title
- `--description`: auto-generated from the script summary
- `--tags`: extracted from the topic and sector
- `--privacy`: from config (`default_privacy`) or user override
- `--category-id`: from config or detected from sector
- `--license`: from config (`default_license`)
- `--publish-at`: if the user wants to schedule the publish

### Scheduling a publish

To upload now but publish later:
```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py upload \
  --config ~/.config/auto-video/config.yaml \
  --title "Scheduled Video" \
  --privacy private \
  --publish-at "2026-05-01T18:00:00Z" \
  /path/to/video.mp4
```

Note: `--publish-at` only works when `--privacy public` is set. For scheduled publishing, upload as `private` first, then the user can set a publish time in YouTube Studio.

## Get channel information

```bash
python3 ~/.config/auto-video/helpers/youtube-upload.py info \
  --config ~/.config/auto-video/config.yaml
```

Returns:
```
Channel: Creatures-b9x
Subscribers: 42
Videos: 12
Total views: 1500
Total duration: 1h 23m 45s
```

With `--json`:
```json
{
  "id": "UC9aa3U1sA8X9gBcLIx8RlJQ",
  "name": "Creatures-b9x",
  "subscribers": "42",
  "total_views": "1500",
  "video_count": "12",
  "total_duration_seconds": 5025,
  "total_duration_human": "1h 23m 45s"
}
```

## Category IDs reference

Common YouTube category IDs for `default_category_id`:

| ID | Category |
|----|----------|
| 1  | Film & Animation |
| 2  | Autos & Vehicles |
| 10 | Music |
| 15 | Pets & Animals |
| 17 | Sports |
| 20 | Gaming |
| 22 | People & Blogs (default) |
| 24 | Entertainment |
| 25 | News & Politics |
| 26 | How-to & Style |
| 27 | Education |
| 28 | Science & Technology |
| 29 | Non-profits & Activism |

Auto-detection from director sector:
- `tech` → 28 (Science & Technology)
- `politics` → 25 (News & Politics)
- `science` → 28 (Science & Technology)
- `culture` → 24 (Entertainment)
- `education` → 27 (Education)
- default → 22 (People & Blogs)

## Error handling

- **"Client secret not found"**: User needs to place their OAuth client secret JSON at the configured path
- **"redirect_uri_mismatch"**: The redirect URI must be `http://127.0.0.1:7777/` in the Google Cloud Console
- **"insufficientPermissions"**: Re-auth with `youtube-upload.py auth` to refresh scopes
- **Upload fails mid-way**: The API supports resumable uploads — retry the same command
- **"quotaExceeded"**: YouTube has daily upload quotas. Wait or request a quota increase in Google Cloud Console

## Security notes

- `youtube_credentials.json` is saved with chmod 600 (owner read/write only)
- Never commit `youtube_client_secret.json` or `youtube_credentials.json` to version control
- The client secret file is the user's own OAuth credential, not an API key — it identifies the app, not the user
- OAuth tokens can be revoked at https://myaccount.google.com/permissions
