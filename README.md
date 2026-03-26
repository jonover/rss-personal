# RSS Curator

A self-hosted RSS aggregation and curation pipeline that filters, scores, and summarizes feeds into a high-signal, low-noise reading experience.

# Overview

This project combines multiple RSS sources into a single curated feed by:

Fetching articles from multiple RSS feeds
Cleaning and normalizing content
Scoring entries based on relevance
Generating concise summaries
Publishing a custom RSS feed for consumption in any reader

It is designed for users who want full control over their information flow without relying on algorithmic feeds or third-party services.

# Architecture
RSS Sources → Python Pipeline → Curated Feed → FreshRSS → Mobile Client
Python script: ingestion, scoring, summarization
Nginx: serves generated RSS feed
FreshRSS: backend aggregation + API
iOS client (e.g., Unread): consumption layer
## Features
## Multi-source RSS aggregation
## HTML stripping and text normalization
## Keyword-based scoring system
## Automatic summarization + truncation
## Custom RSS feed generation
## Cron-based automation
## Compatible with standard RSS readers and APIs
## Project Structure

├── curate_rss.py        # Main pipeline script
├── run_curator.sh       # Wrapper script (cron-friendly)
├── .env                 # Environment config (not committed)
├── requirements.txt
└── README.md

# Setup
1. Clone the repo
git clone https://github.com/yourusername/rss-curator.git
cd rss-curator
2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
3. Configure environment

Create a .env file:

RSS_BASE_URL=http://YOUR_SERVER_IP:8081/rss/curated_feed.xml
4. Run the script
python curate_rss.py
5. (Optional) Automate with cron
crontab -e

Example:

*/30 * * * * /home/user/rss-curator/run_curator.sh
🌐 Serving the Feed

The generated RSS file is served via nginx:

/var/www/rss/curated_feed.xml

Accessible at:

http://YOUR_SERVER_IP:8081/rss/curated_feed.xml

# Client Usage

The curated feed can be used in any RSS reader.

For full aggregation via FreshRSS:

http://YOUR_SERVER_IP:8080/i/?a=rss&user=USERNAME&token=TOKEN

Or connect via API (Fever / Google Reader compatible clients).

# Security Notes
.env is excluded from version control
Avoid exposing public IPs or tokens in the repository
Use HTTPS if exposing outside your LAN

# Future Improvements
Category-based feeds (security, systems, research, etc.)
Advanced ranking (source weighting, recency decay)
Deduplication across sources
ML-based summarization
Web dashboard for tuning filters

# Acknowledgements
FreshRSS
feedparser
feedgen

# Why?

Modern content feeds are noisy and algorithm-driven. This project aims to:

Put control of information back in the hands of the user.
