import os
import sys
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from utils import parse_channel_input
from youtube_api import get_channel_id, get_channel_stats, get_recent_video_ids, get_video_stats
from analysis import calculate_averages, calculate_engagement_rate, get_engagement_rating, get_ai_insight

load_dotenv()

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyse", methods=["POST"])
@limiter.limit("5 per minute; 30 per hour")
def analyse():
    data = request.get_json()
    channel_input = (data.get("channel") or "").strip()
    num_videos = int(data.get("videos", 10))
    use_ai = bool(data.get("ai", False))

    if not channel_input:
        return jsonify({"error": "Channel name or URL is required."}), 400

    num_videos = max(1, min(num_videos, 50))

    try:
        query = parse_channel_input(channel_input)

        channel_info = get_channel_id(query)
        channel_id = channel_info["id"]

        channel_stats = get_channel_stats(channel_id)

        video_ids = get_recent_video_ids(channel_stats["uploads_playlist_id"], max_results=num_videos)
        if not video_ids:
            return jsonify({"error": "No videos found for this channel."}), 404

        video_stats = get_video_stats(video_ids)

        averages = calculate_averages(video_stats)
        engagement_rate = calculate_engagement_rate(
            averages["avg_likes"], averages["avg_comments"], averages["avg_views"]
        )
        rating = get_engagement_rating(engagement_rate)

        ai_insight = ""
        if use_ai:
            metrics = {
                **channel_stats,
                **averages,
                "engagement_rate": engagement_rate,
                "engagement_rating": rating,
            }
            ai_insight = get_ai_insight(metrics)

        return jsonify({
            "channel": channel_stats["title"],
            "subscribers": channel_stats["subscriber_count"],
            "total_videos": channel_stats["video_count"],
            "videos_analysed": len(video_ids),
            "avg_views": round(averages["avg_views"]),
            "avg_likes": round(averages["avg_likes"]),
            "avg_comments": round(averages["avg_comments"]),
            "engagement_rate": round(engagement_rate, 2),
            "rating": rating,
            "ai_insight": ai_insight,
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({"error": "Too many requests — max 5 per minute, 30 per hour. Please wait and try again."}), 429


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"\n  Open http://localhost:{port} in your browser\n")
    app.run(debug=True, port=port)
