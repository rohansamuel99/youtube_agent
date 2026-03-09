import logging
import os
import sys
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from utils import parse_channel_input, validate_channel_input, validate_videos_count
from youtube_api import get_channel_id, get_channel_stats, get_recent_video_ids, get_video_stats
from analysis import calculate_averages, calculate_engagement_rate, get_engagement_rating, get_ai_insight

load_dotenv()

# ---------------------------------------------------------------------------
# OWASP A09 — Security Logging & Monitoring
# Log security-relevant events (validation failures, rate limits, errors).
# Avoid logging user-supplied values verbatim; log sanitised summaries only.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("youtube_analyzer")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

# OWASP A05 — Security Misconfiguration: never trust debug flag from code;
# read from environment so production deployments stay safe by default.
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# OWASP A04 — Insecure Design: limit request body size to 16 KB.
# Prevents memory exhaustion from oversized payloads.
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # 16 KB

# ---------------------------------------------------------------------------
# OWASP A04 — Rate limiting (5/min, 30/hr per IP)
# ---------------------------------------------------------------------------
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


# ---------------------------------------------------------------------------
# OWASP A05 — Security headers on every response
# ---------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    # Prevent MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Don't send Referer header to third parties
    response.headers["Referrer-Policy"] = "no-referrer"
    # Disable browser features not needed by this app
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    # CSP: self-only for scripts/styles (inline required by current HTML),
    # no external resources loaded by the page itself.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyse", methods=["POST"])
@limiter.limit("5 per minute; 30 per hour")
def analyse():
    # OWASP A03 — Injection: enforce Content-Type before parsing body
    if not request.is_json:
        logger.warning("Rejected request: Content-Type is not application/json (ip=%s)", _safe_ip())
        return jsonify({"error": "Content-Type must be application/json."}), 415

    # OWASP A03 — Injection: parse JSON strictly, reject malformed bodies
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        logger.warning("Rejected request: invalid JSON body (ip=%s)", _safe_ip())
        return jsonify({"error": "Invalid request body. Expected a JSON object."}), 400

    # OWASP A03 — Injection: validate and sanitise all user inputs
    try:
        channel_input = validate_channel_input(data.get("channel", ""))
        num_videos = validate_videos_count(data.get("videos", 10))
    except ValueError as e:
        logger.info("Validation failure: %s (ip=%s)", e, _safe_ip())
        return jsonify({"error": str(e)}), 400

    use_ai = bool(data.get("ai", False))

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
        # Expected errors (channel not found, etc.) — safe to surface
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        # OWASP A05 — Security Misconfiguration: never leak internal details
        # Log the real error server-side; return a generic message to the client.
        logger.error("Internal error during analysis (ip=%s): %s", _safe_ip(), e, exc_info=True)
        return jsonify({"error": "An internal error occurred. Please try again later."}), 500


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(413)
def request_too_large(_e):
    logger.warning("Rejected oversized request body (ip=%s)", _safe_ip())
    return jsonify({"error": "Request body too large (max 16 KB)."}), 413


@app.errorhandler(429)
def rate_limit_exceeded(_e):
    logger.warning("Rate limit exceeded (ip=%s)", _safe_ip())
    return jsonify({"error": "Too many requests — max 5 per minute, 30 per hour. Please wait and try again."}), 429


@app.errorhandler(405)
def method_not_allowed(_e):
    return jsonify({"error": "Method not allowed."}), 405


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_ip() -> str:
    """Return a truncated IP suitable for logging (avoids storing full PII)."""
    ip = request.remote_addr or "unknown"
    # Keep only the first two octets of IPv4 (e.g. 192.168.x.x) for privacy
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.x.x"
    return ip[:16]  # truncate IPv6 or unexpected formats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"\n  Open http://localhost:{port} in your browser\n")
    if DEBUG:
        print("  WARNING: debug mode is ON — do not use in production\n")
    app.run(debug=DEBUG, port=port)
