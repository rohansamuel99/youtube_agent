# YouTube Channel Analyzer

A lightweight tool that analyses a YouTube channel's audience engagement and produces a clean report — useful for evaluating creators for brand partnerships, sponsorships, or marketing campaigns.

Runs as either a **local web app** (Flask) or a **CLI tool** from the terminal.

---

## Features

- Look up any channel by name, `@handle`, or full YouTube URL
- Fetches subscriber count and total video count
- Analyses the most recent N videos (default: 10, max: 50)
- Calculates average views, likes, and comments per video
- Computes an engagement rate and rates it (Low / Good / Excellent)
- Optional AI-powered business insight via Claude (Anthropic API)
- Web UI with a dark theme, animated engagement bar, and formula tooltip
- CLI mode saves a full Markdown report to disk

---

## Project Structure

```
youtube_agent/
├── app.py           # Flask web server
├── main.py          # CLI entry point
├── youtube_api.py   # YouTube Data API v3 calls
├── analysis.py      # Metric calculations + AI insight
├── utils.py         # Input parsing, number formatting
├── templates/
│   └── index.html   # Web UI
├── requirements.txt
└── .env             # API keys (not committed)
```

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd youtube_agent
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Get a YouTube Data API v3 key

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Navigate to **APIs & Services → Library**, search for **YouTube Data API v3**, and enable it
4. Go to **APIs & Services → Credentials**, click **+ Create Credentials → API key**
5. Copy the key

> **Quota:** The free tier gives 10,000 units/day. Each run of this tool costs ~3 units.

### 4. (Optional) Get an Anthropic API key

Required only if you want AI-generated business insights via Claude.

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key under **API Keys**

### 5. Add keys to `.env`

```
YOUTUBE_API_KEY=your_youtube_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

---

## Usage

### Web App

```bash
source venv/bin/activate
python app.py
```

Open [http://localhost:5001](http://localhost:5001) in your browser.

- Enter a channel name, `@handle`, or URL
- Adjust the number of videos to analyse (1–50)
- Toggle **AI business insight** to get a Claude-generated summary
- Hover over **Engagement Rate** to see the formula and rating guide

### CLI

```bash
source venv/bin/activate
python main.py <channel>
```

**Examples:**

```bash
# By handle
python main.py @mkbhd

# By channel name
python main.py "Marques Brownlee"

# By URL
python main.py "https://www.youtube.com/@veritasium"

# Analyse last 20 videos
python main.py @mkbhd --videos 20

# Include AI business insight
python main.py @mkbhd --ai

# Save report to a specific file
python main.py @mkbhd --output report.md
```

The CLI prints a summary to the terminal and saves a full Markdown report to disk (default filename: `report_<ChannelName>.md`).

**Example terminal output:**

```
==================================================
Channel: Marques Brownlee
Subscribers: 18.9M
Total Videos: 1,612

Recent Video Averages (last 10 videos)
Average Views: 3,240,000
Average Likes: 98,500
Average Comments: 4,200

Engagement Rate: 3.16% — Good
==================================================

Report saved to: /path/to/report_Marques_Brownlee.md
```

---

## How Engagement Rate is Calculated

```
Engagement Rate = (Average Likes + Average Comments) / Average Views × 100
```

| Rate | Rating |
|------|--------|
| Below 2% | Low |
| 2% – 5% | Good |
| Above 5% | Excellent |

These thresholds reflect real-world YouTube benchmarks. Most large channels sit between 1–4%, so above 5% indicates a highly engaged audience relative to reach — a strong signal for brand partnerships.

---

## API Quota Usage

This tool is designed to stay well within the YouTube Data API free tier (10,000 units/day).

| Operation | Endpoint | Quota Cost |
|-----------|----------|-----------|
| Channel lookup (by handle) | `channels.list` | 1 unit |
| Channel lookup (fallback search) | `search.list` | 100 units |
| Channel stats + uploads playlist | `channels.list` | 1 unit |
| Fetch recent video IDs | `playlistItems.list` | 1 unit |
| Fetch video statistics (batch) | `videos.list` | 1 unit |
| **Total (typical run)** | | **~3–4 units** |

Video IDs are fetched via the channel's **uploads playlist** rather than the Search API, which reduces quota cost from ~200 units to ~3 units per run.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | YouTube API HTTP calls |
| `python-dotenv` | Load API keys from `.env` |
| `flask` | Web server for the UI |
| `anthropic` | Claude API for AI insights (optional) |
