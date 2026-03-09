import os
import re
import unicodedata
from urllib.parse import urlparse

# Allowed characters in a bare channel name/handle after stripping the URL
_CHANNEL_RE = re.compile(r'^[\w\-. @]{1,100}$')

# Allowed YouTube URL hostnames
_YOUTUBE_HOSTS = {"www.youtube.com", "youtube.com", "youtu.be"}

# Output path: only a filename or single relative path ending in .md, no traversal
_OUTPUT_RE = re.compile(r'^[\w\-. ]{1,100}\.md$')


def _strip_control_chars(s: str) -> str:
    """Remove Unicode control characters (categories Cc, Cf) from a string."""
    return "".join(c for c in s if unicodedata.category(c) not in ("Cc", "Cf"))


def validate_channel_input(raw: str) -> str:
    """
    Validate and sanitise a raw channel input (name, @handle, or URL).
    Returns the cleaned string, or raises ValueError with a user-facing message.
    """
    if not isinstance(raw, str):
        raise ValueError("Channel input must be a string.")

    # Remove control characters and strip whitespace
    cleaned = _strip_control_chars(raw).strip()

    if not cleaned:
        raise ValueError("Channel name or URL cannot be empty.")

    if len(cleaned) > 200:
        raise ValueError("Channel input is too long (max 200 characters).")

    # If it looks like a URL, validate the host before accepting it
    if "://" in cleaned or cleaned.startswith("www."):
        try:
            parsed = urlparse(cleaned if "://" in cleaned else "https://" + cleaned)
        except Exception:
            raise ValueError("Invalid URL format.")
        if parsed.hostname not in _YOUTUBE_HOSTS:
            raise ValueError("URL must be a YouTube channel URL (youtube.com).")
        return cleaned

    # Bare handle or name — allow @handle or plain alphanumeric channel names
    if not _CHANNEL_RE.match(cleaned):
        raise ValueError(
            "Invalid channel name. Use letters, numbers, hyphens, underscores, "
            "dots, or a @handle. Max 100 characters."
        )

    return cleaned


def validate_videos_count(raw) -> int:
    """
    Validate and return the number of videos to analyse.
    Accepts int or string. Raises ValueError for bad input.
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError("Video count must be a whole number.")
    if value < 1 or value > 50:
        raise ValueError("Video count must be between 1 and 50.")
    return value


def validate_output_path(raw: str) -> str:
    """
    Validate a CLI output file path.
    Must be a simple filename ending in .md with no path traversal.
    Raises ValueError for unsafe or invalid paths.
    """
    if not isinstance(raw, str):
        raise ValueError("Output path must be a string.")

    cleaned = _strip_control_chars(raw).strip()

    if not cleaned:
        raise ValueError("Output path cannot be empty.")

    # Reject absolute paths and any path traversal
    if os.path.isabs(cleaned):
        raise ValueError("Output path must be a relative filename, not an absolute path.")

    if ".." in cleaned.split(os.sep):
        raise ValueError("Output path must not contain '..'.")

    if not _OUTPUT_RE.match(os.path.basename(cleaned)):
        raise ValueError(
            "Output filename must end in .md and contain only letters, numbers, "
            "hyphens, underscores, dots, or spaces (max 100 characters)."
        )

    return cleaned


def parse_channel_input(input_str: str) -> str:
    """
    Given a validated YouTube channel URL or name/handle, return the query string
    to pass to the YouTube API. Extracts the handle/username from URLs.
    """
    input_str = input_str.strip()
    if "youtube.com" in input_str:
        if "://" not in input_str:
            input_str = "https://" + input_str
        parsed = urlparse(input_str)
        path = parsed.path.rstrip("/")
        parts = path.split("/")
        for part in reversed(parts):
            if part and part not in ("c", "user", "channel"):
                return part.lstrip("@")
    return input_str.lstrip("@") if input_str.startswith("@") else input_str


def format_number(n) -> str:
    """Format a number with commas as thousands separators."""
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return "N/A"
