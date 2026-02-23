"""Security utilities for auto-video."""

import re
from pathlib import Path

SENSITIVE_PATTERNS = [
    r"sk-[a-zA-Z0-9]{10,}",
    r"sk-ant-[a-zA-Z0-9-]{10,}",
    r"[a-zA-Z0-9]{32,}",
    r"AIza[a-zA-Z0-9_-]{30,}",
    r"ya29\.[a-zA-Z0-9_-]+",
    r"refresh_token",
    r"access_token",
    r"client_secret",
    r"api_key",
    r"password",
]

SENSITIVE_KEYS = {
    "api_key",
    "password",
    "secret",
    "token",
    "credential",
    "client_secret",
    "refresh_token",
    "access_token",
    "private_key",
    "auth",
}


def mask_sensitive_value(key: str, value: str) -> str:
    if not isinstance(value, str) or not value:
        return value

    key_lower = key.lower()
    for sensitive_key in SENSITIVE_KEYS:
        if sensitive_key in key_lower:
            if len(value) <= 4:
                return "***"
            return f"{value[:2]}...{value[-2:]}"

    return value


def mask_secrets_in_string(text: str) -> str:
    if not isinstance(text, str):
        return text

    masked = text
    for pattern in SENSITIVE_PATTERNS:
        masked = re.sub(pattern, "[REDACTED]", masked, flags=re.IGNORECASE)

    return masked


def mask_secrets_in_dict(data: dict[str, object], depth: int = 0) -> dict[str, object]:
    if depth > 10:
        return data

    result: dict[str, object] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = mask_secrets_in_dict(value, depth + 1)
        elif isinstance(value, str):
            result[key] = mask_sensitive_value(key, value)
        else:
            result[key] = value

    return result


def sanitize_filename(filename: str) -> str:
    if not filename:
        return "unnamed"

    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    sanitized = re.sub(r"\.{2,}", ".", sanitized)
    sanitized = sanitized.strip(". ")

    if not sanitized:
        return "unnamed"

    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rsplit("_", 1)[0] or sanitized[:max_length]

    return sanitized


def sanitize_path_component(component: str) -> str:
    if not component:
        return ""

    sanitized = sanitize_filename(component)

    dangerous_names = {
        ".",
        "..",
        "~",
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
    }

    if sanitized.lower() in dangerous_names:
        sanitized = f"_{sanitized}"

    return sanitized


def validate_path(base_path: Path, target_path: Path) -> bool:
    try:
        base_resolved = base_path.resolve()
        target_resolved = target_path.resolve()
        return str(target_resolved).startswith(str(base_resolved))
    except (OSError, ValueError):
        return False


def secure_file_permissions(path: Path, mode: int = 0o644) -> None:
    if not path.exists():
        return

    current_mode = path.stat().st_mode & 0o777
    if current_mode != mode:
        path.chmod(mode)


def secure_credential_file(path: Path) -> None:
    secure_file_permissions(path, 0o600)


def secure_directory_permissions(path: Path, mode: int = 0o755) -> None:
    if not path.exists():
        return

    current_mode = path.stat().st_mode & 0o777
    if current_mode != mode:
        path.chmod(mode)


def create_secure_file(path: Path, content: str | bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)

    path.chmod(mode)


def validate_video_id(video_id: str) -> bool:
    if not video_id:
        return False

    if len(video_id) > 100:
        return False

    if not re.match(r"^[\w\-_.]+$", video_id):
        return False

    return True


def validate_title(title: str | None) -> str:
    if title is None:
        return ""

    title = str(title).strip()

    max_length = 500
    if len(title) > max_length:
        title = title[:max_length]

    return title


def validate_language(lang: str) -> str:
    if not lang:
        return "en"

    lang = lang.strip().lower()

    if not re.match(r"^[a-z]{2,3}(-[a-z]{2,4})?$", lang):
        return "en"

    return lang


def validate_format(format_str: str) -> str:
    valid_formats = {"short", "long"}

    if format_str not in valid_formats:
        return "long"

    return format_str


def validate_duration(duration: int | None) -> int | None:
    if duration is None:
        return None

    if duration < 5:
        return 5

    if duration > 3600:
        return 3600

    return duration


def validate_step(step: int) -> int:
    valid_steps = {1, 2, 3, 4, 5, 6, 7}

    if step not in valid_steps:
        return 1

    return step
