"""YouTube upload module."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
from googleapiclient.http import MediaFileUpload  # type: ignore
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from auto_video.utils.security import secure_credential_file

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


@dataclass
class UploadResult:
    video_id: str
    url: str
    status: str


@dataclass
class QuotaInfo:
    uploaded: int
    remaining: int
    limit: int


class YouTubeUploadError(Exception):
    pass


class YouTubeUploader:
    def __init__(self, credentials_path: Path) -> None:
        self.credentials_path = credentials_path
        self._service: Any = None
        self._credentials: Any = None

    def authenticate(self) -> None:
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")

        credentials = None
        token_path = self.credentials_path.parent / "token.json"

        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)  # type: ignore

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                credentials = flow.run_local_server(port=0)

            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(credentials.to_json(), encoding="utf-8")
            token_path.chmod(0o600)

            old_umask = os.umask(0o077)
            try:
                secure_credential_file(token_path)
            finally:
                os.umask(old_umask)

        self._credentials = credentials
        self._service = build("youtube", "v3", credentials=credentials)
        logger.info("YouTube authentication successful")

    def _ensure_authenticated(self) -> None:
        if self._service is None:
            self.authenticate()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(HttpError),
        reraise=True,
    )
    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: Path | None = None,
        privacy: str = "unlisted",
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> UploadResult:
        self._ensure_authenticated()

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/*")

        request = self._service.videos().insert(part="snippet,status", body=body, media_body=media)

        try:
            logger.info("Starting YouTube upload: %s", video_path.name)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    if progress_callback:
                        progress_callback(status.resumable_progress, status.total_size)
                    logger.debug(
                        "Upload progress: %d / %d bytes",
                        status.resumable_progress,
                        status.total_size,
                    )

            video_id = response.get("id", "")
            url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info("YouTube upload successful: %s", url)

            if thumbnail_path:
                self.set_thumbnail(video_id, thumbnail_path)

            return UploadResult(video_id=video_id, url=url, status="uploaded")

        except HttpError as e:
            if e.resp.status == 429:
                logger.warning("YouTube quota exceeded: %s", str(e))
                raise YouTubeUploadError("YouTube quota exceeded") from e
            logger.error("YouTube upload failed: %s", str(e))
            raise YouTubeUploadError(f"YouTube upload failed: {e}") from e
        except Exception as e:
            logger.error("YouTube upload failed: %s", str(e))
            raise YouTubeUploadError(f"YouTube upload failed: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(HttpError),
        reraise=True,
    )
    def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> None:
        self._ensure_authenticated()

        if not thumbnail_path.exists():
            raise FileNotFoundError(f"Thumbnail file not found: {thumbnail_path}")

        media = MediaFileUpload(str(thumbnail_path))

        try:
            self._service.thumbnails().set(videoId=video_id, media_body=media).execute()
            logger.info("Thumbnail set successfully for video %s", video_id)
        except HttpError as e:
            logger.error("Failed to set thumbnail: %s", str(e))
            raise YouTubeUploadError(f"Failed to set thumbnail: {e}") from e

    def get_quota_usage(self) -> QuotaInfo:
        self._ensure_authenticated()

        try:
            request = self._service.videos().list(part="snippet", mine=True, maxResults=50)
            response = request.execute()

            items = response.get("items", [])
            uploaded_count = len(items)
            page_token = response.get("nextPageToken")

            while page_token and uploaded_count < 10000:
                request = self._service.videos().list(
                    part="snippet", mine=True, maxResults=50, pageToken=page_token
                )
                response = request.execute()
                items = response.get("items", [])
                uploaded_count += len(items)
                page_token = response.get("nextPageToken")

            daily_limit = 10000
            remaining = max(0, daily_limit - uploaded_count)

            return QuotaInfo(uploaded=uploaded_count, remaining=remaining, limit=daily_limit)

        except HttpError as e:
            logger.error("Failed to get quota usage: %s", str(e))
            raise YouTubeUploadError(f"Failed to get quota usage: {e}") from e
