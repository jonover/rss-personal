#!/bin/bash
set -euo pipefail

LOCKFILE="/tmp/rss-curator.lock"
exec 9>"$LOCKFILE"
flock -n 9 || exit 0

SRC="/home/jon/freshrss/curated_feed.xml"
DST_DIR="/var/www/rss"
TMP="$DST_DIR/curated_feed.xml.tmp"
DST="$DST_DIR/curated_feed.xml"

cd /home/jon/freshrss || exit 1
/home/jon/freshrss/.venv/bin/python /home/jon/freshrss/curator.py

if  [ ! -f "$SRC" ]; then
	echo "Source file not found: $SRC"
	exit 1
fi

if [ ! -d "$DST_DIR" ]; then
	echo "Destination directory not found: $DST_DIR"
	exit 1
fi

cp "$SRC" "$TMP"
mv "$TMP" "$DST"
echo "Feed updated successfully."
