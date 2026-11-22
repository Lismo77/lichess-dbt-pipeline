"""Extract: download my Lichess games to a timestamped JSONL batch file in data/raw/.

Incremental: only asks for games created since (newest game already in raw.games
minus LOOKBACK). The lookback re-fetches recent games because Lichess filters
`since` on *creation* time — a correspondence game created before the watermark
but finished after it would otherwise never be picked up. Overlap is harmless:
load_games.py upserts on game id.

Usage: venv/bin/python scripts/fetch_games.py [--full]
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

from common import RAW_DIR, USERNAME, connect

LOOKBACK = timedelta(days=14)


def get_since_ms():
	"""Epoch ms to fetch from, or None for a full history pull."""
	if "--full" in sys.argv:
		return None
	with connect() as conn:
		row = conn.execute("select max((data->>'createdAt')::bigint) from raw.games").fetchone()
	newest_ms = row[0]
	if newest_ms is None:  # empty table — first run
		return None
	return newest_ms - int(LOOKBACK.total_seconds() * 1000)


def main():
	since_ms = get_since_ms()
	params = {"opening": "true"}
	if since_ms is not None:
		params["since"] = since_ms
		since_str = datetime.fromtimestamp(since_ms / 1000, timezone.utc).date()
		print(f"Incremental fetch: games created since {since_str}")
	else:
		print("Full fetch: entire game history")

	response = requests.get(
		f"https://lichess.org/api/games/user/{USERNAME}",
		headers={
			"Accept": "application/x-ndjson",
			"Authorization": f"Bearer {os.getenv('LICHESS_TOKEN')}",
		},
		params=params,
		stream=True,
		timeout=60,
	)
	# Fail loudly on 401/429/etc. instead of silently writing an empty file.
	response.raise_for_status()

	# One immutable file per run: a re-run never overwrites earlier extracts.
	stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
	RAW_DIR.mkdir(parents=True, exist_ok=True)
	output_path = RAW_DIR / f"{USERNAME}_games_{stamp}.jsonl"

	game_count = 0
	with open(output_path, "w") as f:
		for line in response.iter_lines():
			if line:
				f.write(line.decode("utf-8") + "\n")
				game_count += 1

	print(f"Saved {game_count} games to {output_path.relative_to(RAW_DIR.parent.parent)}")


if __name__ == "__main__":
	main()
