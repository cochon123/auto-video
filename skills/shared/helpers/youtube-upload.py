#!/usr/bin/env python3
"""Upload videos to YouTube via the YouTube Data API v3."""

import argparse
import json
import os
import sys
import re
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("Missing dependencies. Run: pip install google-api-python-client google-auth-oauthlib", file=sys.stderr)
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_CLIENT_SECRET = os.path.expanduser("~/.config/auto-video/youtube_client_secret.json")
DEFAULT_CREDENTIALS = os.path.expanduser("~/.config/auto-video/youtube_credentials.json")
DEFAULT_PORT = 7777


def _load_config(config_path: str | None) -> dict:
    if not config_path:
        return {}
    try:
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        pass
    except FileNotFoundError:
        pass
    return {}


def _get_youtube_config(config: dict) -> dict:
    return config.get("youtube", {})


def _get_credentials(client_secret: str, credentials_file: str, host: str, port: int) -> Credentials:
    creds = None
    if os.path.exists(credentials_file):
        try:
            creds = Credentials.from_authorized_user_file(credentials_file, SCOPES)
        except Exception:
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        with open(credentials_file, "w") as f:
            f.write(creds.to_json())
        return creds

    flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
    redirect_uri = f"http://{host}:{port}/"
    flow.redirect_uri = redirect_uri
    creds = flow.run_local_server(host=host, port=port)

    with open(credentials_file, "w") as f:
        f.write(creds.to_json())
    os.chmod(credentials_file, 0o600)

    return creds


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "private",
    client_secret: str | None = None,
    credentials_file: str | None = None,
    config_path: str | None = None,
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    made_for_kids: bool = False,
    embeddable: bool = True,
    license: str = "creativeCommon",
    notify_subscribers: bool = True,
    publish_at: str | None = None,
) -> dict:
    config = _load_config(config_path)
    yt_config = _get_youtube_config(config)

    client_secret = client_secret or yt_config.get("client_secret", DEFAULT_CLIENT_SECRET)
    credentials_file = credentials_file or yt_config.get("credentials_file", DEFAULT_CREDENTIALS)
    host = yt_config.get("redirect_host", host)
    port = yt_config.get("redirect_port", port)

    if not os.path.exists(client_secret):
        print(f"Client secret not found: {client_secret}", file=sys.stderr)
        print("Place your OAuth client secret JSON at that path or pass --client-secret.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    tags = tags or yt_config.get("default_tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    creds = _get_credentials(client_secret, credentials_file, host, port)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "embeddable": embeddable,
            "license": license,
            "selfDeclaredMadeForKids": made_for_kids,
            "notifySubscribers": notify_subscribers,
        },
    }

    if publish_at:
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(video_path, mimetype="video/*", resumable=True)

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    print(f"Uploading: {video_path}")
    print(f"  Title: {title}")
    print(f"  Privacy: {privacy_status}")

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Progress: {int(status.progress() * 100)}%")

    video_id = response.get("id", "unknown")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  Uploaded: {video_url}")

    return {
        "id": video_id,
        "url": video_url,
        "title": response.get("snippet", {}).get("title", title),
        "privacy": response.get("status", {}).get("privacyStatus", privacy_status),
    }


def get_channel_info(
    client_secret: str | None = None,
    credentials_file: str | None = None,
    config_path: str | None = None,
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
) -> dict:
    config = _load_config(config_path)
    yt_config = _get_youtube_config(config)

    client_secret = client_secret or yt_config.get("client_secret", DEFAULT_CLIENT_SECRET)
    credentials_file = credentials_file or yt_config.get("credentials_file", DEFAULT_CREDENTIALS)
    host = yt_config.get("redirect_host", host)
    port = yt_config.get("redirect_port", port)

    creds = _get_credentials(client_secret, credentials_file, host, port)
    youtube = build("youtube", "v3", credentials=creds)

    channels = youtube.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()

    if not channels.get("items"):
        return {}

    ch = channels["items"][0]
    stats = ch.get("statistics", {})
    snippet = ch.get("snippet", {})

    result = {
        "id": ch["id"],
        "name": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "subscribers": stats.get("subscriberCount", "0"),
        "total_views": stats.get("viewCount", "0"),
        "video_count": stats.get("videoCount", "0"),
    }

    uploads_playlist = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if uploads_playlist:
        total_seconds = 0
        video_count = 0
        page_token = None

        while True:
            playlist = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist,
                maxResults=50,
                pageToken=page_token,
            ).execute()

            video_ids = [item["contentDetails"]["videoId"] for item in playlist.get("items", [])]

            if video_ids:
                videos = youtube.videos().list(
                    part="contentDetails",
                    id=",".join(video_ids),
                ).execute()

                for v in videos.get("items", []):
                    dur = v["contentDetails"]["duration"]
                    total_seconds += _parse_duration(dur)
                    video_count += 1

            page_token = playlist.get("nextPageToken")
            if not page_token:
                break

        result["total_duration_seconds"] = total_seconds
        result["total_duration_human"] = _format_duration(total_seconds)
        result["videos_processed"] = video_count

    return result


def _parse_duration(iso: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


def _format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def main():
    parser = argparse.ArgumentParser(description="YouTube upload helper for auto-video")
    sub = parser.add_subparsers(dest="command")

    upload_parser = sub.add_parser("upload", help="Upload a video to YouTube")
    upload_parser.add_argument("video", help="Path to the video file")
    upload_parser.add_argument("--title", required=True, help="Video title")
    upload_parser.add_argument("--description", default="")
    upload_parser.add_argument("--tags", default="", help="Comma-separated tags")
    upload_parser.add_argument("--category-id", default="22", help="YouTube category ID (default: 22 = People & Blogs)")
    upload_parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    upload_parser.add_argument("--client-secret", default=None)
    upload_parser.add_argument("--credentials-file", default=None)
    upload_parser.add_argument("--config", default=None)
    upload_parser.add_argument("--host", default="127.0.0.1")
    upload_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    upload_parser.add_argument("--no-notify", action="store_true", help="Don't notify subscribers")
    upload_parser.add_argument("--license", default="creativeCommon", choices=["creativeCommon", "youtube"])
    upload_parser.add_argument("--made-for-kids", action="store_true")
    upload_parser.add_argument("--publish-at", default=None, help="ISO 8601 datetime for scheduled publish")
    upload_parser.add_argument("--json", action="store_true", help="Output result as JSON")

    info_parser = sub.add_parser("info", help="Get authenticated channel info and statistics")
    info_parser.add_argument("--client-secret", default=None)
    info_parser.add_argument("--credentials-file", default=None)
    info_parser.add_argument("--config", default=None)
    info_parser.add_argument("--host", default="127.0.0.1")
    info_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    info_parser.add_argument("--json", action="store_true", help="Output result as JSON")

    auth_parser = sub.add_parser("auth", help="Authenticate and save credentials")
    auth_parser.add_argument("--client-secret", default=None)
    auth_parser.add_argument("--credentials-file", default=None)
    auth_parser.add_argument("--config", default=None)
    auth_parser.add_argument("--host", default="127.0.0.1")
    auth_parser.add_argument("--port", type=int, default=DEFAULT_PORT)

    args = parser.parse_args()

    if args.command == "upload":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        result = upload_video(
            video_path=args.video,
            title=args.title,
            description=args.description,
            tags=tags,
            category_id=args.category_id,
            privacy_status=args.privacy,
            client_secret=args.client_secret,
            credentials_file=args.credentials_file,
            config_path=args.config,
            host=args.host,
            port=args.port,
            made_for_kids=args.made_for_kids,
            embeddable=True,
            license=args.license,
            notify_subscribers=not args.no_notify,
            publish_at=args.publish_at,
        )
        if args.json:
            print(json.dumps(result, indent=2))

    elif args.command == "info":
        result = get_channel_info(
            client_secret=args.client_secret,
            credentials_file=args.credentials_file,
            config_path=args.config,
            host=args.host,
            port=args.port,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Channel: {result.get('name', 'N/A')}")
            print(f"Subscribers: {result.get('subscribers', 'N/A')}")
            print(f"Videos: {result.get('video_count', 'N/A')}")
            print(f"Total views: {result.get('total_views', 'N/A')}")
            if "total_duration_human" in result:
                print(f"Total duration: {result['total_duration_human']}")

    elif args.command == "auth":
        config = _load_config(args.config)
        yt_config = _get_youtube_config(config)
        client_secret = args.client_secret or yt_config.get("client_secret", DEFAULT_CLIENT_SECRET)
        credentials_file = args.credentials_file or yt_config.get("credentials_file", DEFAULT_CREDENTIALS)
        host = args.host
        port = args.port
        _get_credentials(client_secret, credentials_file, host, port)
        print("Authentication successful. Credentials saved.")

    else:
        parser.print_help()


if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    main()
