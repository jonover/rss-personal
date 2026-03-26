#!/usr/bin/env python3
"""
curate_rss.py

Fetch multiple RSS/Atom feeds, score entries by your interests,
deduplicate them, and generate a curated RSS feed.

Install:
    pip install feedparser feedgen requests

Run:
    python curate_rss.py

Output:
    curated_feed.xml
"""

from __future__ import annotations

import hashlib
import os
import html
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable, List, Optional

import feedparser
import requests
from feedgen.feed import FeedGenerator
from dotenv import load_dotenv

load_dotenv()


# ----------------------------
# Configuration
# ----------------------------

FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/blog/atom.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://www.reddit.com/r/netsec/.rss",
    "https://rss.arxiv.org/rss/cs",
]

# Higher weight = stronger preference
KEYWORD_WEIGHTS = {
    # security
    "cybersecurity": 6,
    "security": 4,
    "vulnerability": 6,
    "cve": 8,
    "exploit": 7,
    "malware": 7,
    "ransomware": 7,
    "phishing": 6,
    "breach": 6,
    "zero-day": 8,
    "encryption": 5,
    "tls": 5,
    "authentication": 5,
    "linux": 4,
    "kernel": 5,
    "network": 4,

    # systems / HPC / CS
    "parallel": 5,
    "distributed": 5,
    "compiler": 5,
    "ocaml": 6,
    "functional programming": 5,
    "hpc": 7,
    "high performance computing": 7,
    "mpi": 6,
    "openmp": 6,
    "cuda": 5,
    "performance": 4,
    "benchmark": 4,
    "systems programming": 6,
    "operating system": 5,
    "wayland": 4,
    "arch linux": 5,
    "rss": 2,
}

NEGATIVE_KEYWORDS = {
    "celebrity": -5,
    "gossip": -6,
    "fashion": -4,
    "shopping": -4,
    "lifestyle": -3,
}

MAX_ITEMS = 30
REQUEST_TIMEOUT = 15
USER_AGENT = "JonathanCurator/1.0 (+personal RSS curation script)"
BASE_URL = os.getenv("RSS_BASE_URL", "http://192.168.1.42:8081/rss/curated_feed.xml")
FEED_VERSION = "v3"


# ----------------------------
# Data model
# ----------------------------

@dataclass
class FeedItem:
    title: str
    link: str
    summary: str
    published: Optional[datetime]
    source_title: str
    score: int
    uid: str


# ----------------------------
# Helpers
# ----------------------------

def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def summarize(text: str) -> str:
    text = clean_text(text)

    # Strip noisy prefixes often found in arXiv / Reddit / security feeds
    patterns = [
        r"^\[.*?\]\s*",
        r"^arXiv:\S+\s+",
        r"^Announce Type:\s*new Abstract:\s*",
        r"^Abstract:\s*",
        r"^Resumo técnico:\s*",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # If there is a colon-heavy metadata blob at the front, cut after it
    text = re.sub(r"^(?:[A-ZÀ-Ž0-9 _/-]+:\s*){2,}", "", text)

    # Keep only the first sentence or two
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:2]).strip()

    return summary[:220]


def parse_date(entry) -> Optional[datetime]:
    candidates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created"),
    ]
    for value in candidates:
        if not value:
            continue
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

    # feedparser may expose parsed tuples
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(attr)
        if parsed:
            try:
                return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
            except Exception:
                pass

    return None


def item_uid(title: str, link: str, summary: str) -> str:
    digest = hashlib.sha256(
        f"{title}|{link}|{summary}".encode("utf-8")
    ).hexdigest()
    return digest


def score_text(title: str, summary: str) -> int:
    haystack = f"{title} {summary}".lower()
    score = 0

    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in haystack:
            score += weight

    for keyword, weight in NEGATIVE_KEYWORDS.items():
        if keyword in haystack:
            score += weight

    # Small bonus for title matches
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in title.lower():
            score += max(1, weight // 2)

    return score


def dedupe_items(items: Iterable[FeedItem]) -> List[FeedItem]:
    seen_links = set()
    seen_titles = set()
    result = []

    for item in items:
        norm_link = item.link.strip().lower()
        norm_title = re.sub(r"\s+", " ", item.title.strip().lower())

        if norm_link in seen_links or norm_title in seen_titles:
            continue

        seen_links.add(norm_link)
        seen_titles.add(norm_title)
        result.append(item)

    return result


def fetch_feed(url: str) -> List[FeedItem]:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    parsed = feedparser.parse(response.content)
    source_title = parsed.feed.get("title", url)

    items: List[FeedItem] = []

    for entry in parsed.entries:
        title = clean_text(entry.get("title", "Untitled"))
        link = entry.get("link", "").strip()
        summary = clean_text(
            entry.get("summary", "") or entry.get("description", "")
        )
        published = parse_date(entry)

        # Remove duplicated title in summary
        if summary.lower().startswith(title.lower()):
            summary = summary[len(title):].strip(" :-–—")

        if not link:
            continue

        score = score_text(title, summary)

        items.append(
            FeedItem(
                title=title,
                link=link,
                summary=summary,
                published=published,
                source_title=source_title,
                score=score,
                uid=None,
            )
        )

    return items


def sort_items(items: List[FeedItem]) -> List[FeedItem]:
    def key(item: FeedItem):
        published_ts = item.published.timestamp() if item.published else 0
        return (item.score, published_ts)

    return sorted(items, key=key, reverse=True)


def build_feed(items: List[FeedItem], output_file: str = "curated_feed.xml") -> None:
    fg = FeedGenerator()
    fg.title("Jonathan's Curated Feed")
    fg.link(href=BASE_URL, rel="self")
    fg.description("A personal curated RSS feed generated from multiple sources.")
    fg.language("en")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        fe = fg.add_entry(order="append")

        summary = summarize(item.summary)
        guid = item_uid(item.title, item.link, summary)

        fe.id(guid)
        fe.guid(guid, permalink=False)
        fe.title(item.title)
        fe.link(href=item.link)
        fe.description(summary)
        fe.pubDate(datetime.now(timezone.utc))

    fg.rss_file(output_file, pretty=True)


def main() -> None:
    all_items: List[FeedItem] = []

    for url in FEEDS:
        try:
            print(f"Fetching: {url}")
            items = fetch_feed(url)
            print(f"  -> got {len(items)} items")
            all_items.extend(items)
        except Exception as exc:
            print(f"  !! failed: {url} ({exc})")

    all_items = dedupe_items(all_items)
    all_items = sort_items(all_items)

    # Keep the best items; optionally discard zero/negative scores
    curated = [item for item in all_items if item.score > 0][:MAX_ITEMS]

    build_feed(curated)
    print(f"\nWrote curated_feed.xml with {len(curated)} items.")


if __name__ == "__main__":
    main()
