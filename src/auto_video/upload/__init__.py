"""Upload modules (YouTube, etc)."""

__all__ = ["YouTubeUploader", "UploadResult", "QuotaInfo", "YouTubeUploadError"]


def __getattr__(name: str):
    if name in __all__:
        from auto_video.upload.youtube import (
            QuotaInfo,
            UploadResult,
            YouTubeUploader,
            YouTubeUploadError,
        )

        exports = {
            "YouTubeUploader": YouTubeUploader,
            "UploadResult": UploadResult,
            "QuotaInfo": QuotaInfo,
            "YouTubeUploadError": YouTubeUploadError,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
