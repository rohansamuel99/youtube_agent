from urllib.parse import urlparse


def parse_channel_input(input_str: str) -> str:
    """
    Given a YouTube channel URL or name/handle, return the channel query string.
    For URLs, extracts the handle or username from the path.
    For plain text, returns as-is.
    """
    input_str = input_str.strip()
    if "youtube.com" in input_str:
        parsed = urlparse(input_str)
        path = parsed.path.rstrip("/")
        # e.g. /@mkbhd, /c/mkbhd, /user/mkbhd, /mkbhd
        parts = path.split("/")
        # Return the last meaningful path segment (strip leading @)
        for part in reversed(parts):
            if part and part not in ("c", "user", "channel"):
                return part.lstrip("@")
    return input_str


def format_number(n) -> str:
    """Format a number with commas as thousands separators."""
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return "N/A"
