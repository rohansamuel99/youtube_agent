import os


def calculate_averages(video_stats: list) -> dict:
    """
    Compute average views, likes, and comments across a list of video stat dicts.
    Returns {"avg_views": float, "avg_likes": float, "avg_comments": float}
    """
    if not video_stats:
        return {"avg_views": 0.0, "avg_likes": 0.0, "avg_comments": 0.0}
    n = len(video_stats)
    return {
        "avg_views": sum(v["view_count"] for v in video_stats) / n,
        "avg_likes": sum(v["like_count"] for v in video_stats) / n,
        "avg_comments": sum(v["comment_count"] for v in video_stats) / n,
    }


def calculate_engagement_rate(avg_likes: float, avg_comments: float, avg_views: float) -> float:
    """
    Engagement rate = (avg_likes + avg_comments) / avg_views * 100
    Returns 0.0 if avg_views is zero.
    """
    if avg_views == 0:
        return 0.0
    return (avg_likes + avg_comments) / avg_views * 100


def get_engagement_rating(rate: float) -> str:
    """Return a qualitative label for an engagement rate percentage."""
    if rate >= 5:
        return "Excellent"
    elif rate >= 2:
        return "Good"
    else:
        return "Low"


def get_ai_insight(metrics: dict) -> str:
    """
    Send channel metrics to Claude and return a short business insight.
    Returns an empty string if ANTHROPIC_API_KEY is not set or anthropic is not installed.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    try:
        import anthropic
    except ImportError:
        return ""

    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        f"You are a marketing analyst. Given the following YouTube channel metrics, "
        f"write 1-2 sentences of business insight about whether this channel would be "
        f"a good candidate for brand partnerships or sponsorships. Be concise and direct.\n\n"
        f"Channel: {metrics['title']}\n"
        f"Subscribers: {metrics['subscriber_count']:,}\n"
        f"Total Videos: {metrics['video_count']:,}\n"
        f"Average Views: {metrics['avg_views']:,.0f}\n"
        f"Average Likes: {metrics['avg_likes']:,.0f}\n"
        f"Average Comments: {metrics['avg_comments']:,.0f}\n"
        f"Engagement Rate: {metrics['engagement_rate']:.2f}% ({metrics['engagement_rating']})\n"
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
