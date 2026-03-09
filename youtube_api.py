import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.googleapis.com/youtube/v3"


def _api_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise ValueError("YOUTUBE_API_KEY not set in environment / .env file")
    return key


def get_channel_id(query: str) -> dict:
    """
    Resolve a channel name, handle, or search query to a channel ID and title.
    First tries forHandle lookup (for @handle style), then falls back to search.
    Returns {"id": str, "title": str}
    """
    key = _api_key()

    # Try forHandle first (efficient, 1 quota unit)
    handle = query.lstrip("@")
    resp = requests.get(
        f"{BASE_URL}/channels",
        params={
            "part": "snippet",
            "forHandle": handle,
            "key": key,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("items"):
        item = data["items"][0]
        return {"id": item["id"], "title": item["snippet"]["title"]}

    # Fall back to search (100 quota units)
    resp = requests.get(
        f"{BASE_URL}/search",
        params={
            "part": "snippet",
            "type": "channel",
            "q": query,
            "maxResults": 1,
            "key": key,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("items"):
        raise ValueError(f"No channel found for query: {query!r}")
    item = data["items"][0]
    return {
        "id": item["snippet"]["channelId"],
        "title": item["snippet"]["channelTitle"],
    }


def get_channel_stats(channel_id: str) -> dict:
    """
    Fetch subscriber count, total video count, and uploads playlist ID for a channel.
    Returns {"title": str, "subscriber_count": int, "video_count": int, "uploads_playlist_id": str}
    """
    resp = requests.get(
        f"{BASE_URL}/channels",
        params={
            "part": "snippet,statistics,contentDetails",
            "id": channel_id,
            "key": _api_key(),
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("items"):
        raise ValueError(f"Channel not found: {channel_id}")
    item = data["items"][0]
    stats = item["statistics"]
    uploads_playlist_id = (
        item.get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads", "")
    )
    return {
        "title": item["snippet"]["title"],
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "uploads_playlist_id": uploads_playlist_id,
    }


def get_recent_video_ids(uploads_playlist_id: str, max_results: int = 10) -> list:
    """
    Return a list of video IDs for the most recently uploaded videos using the
    channel's uploads playlist (1 quota unit vs 100 for search).
    """
    resp = requests.get(
        f"{BASE_URL}/playlistItems",
        params={
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": min(max_results, 50),
            "key": _api_key(),
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        item["contentDetails"]["videoId"]
        for item in data.get("items", [])
    ]


def get_video_stats(video_ids: list) -> list:
    """
    Fetch statistics for a list of video IDs in a single batch API call.
    Returns a list of dicts with view_count, like_count, comment_count (all int).
    Missing fields (e.g. disabled likes/comments) default to 0.
    """
    if not video_ids:
        return []
    resp = requests.get(
        f"{BASE_URL}/videos",
        params={
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": _api_key(),
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    results = []
    for item in data.get("items", []):
        s = item.get("statistics", {})
        results.append({
            "view_count": int(s.get("viewCount", 0)),
            "like_count": int(s.get("likeCount", 0)),
            "comment_count": int(s.get("commentCount", 0)),
        })
    return results
