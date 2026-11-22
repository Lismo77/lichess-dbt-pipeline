"""Load: upsert a JSONL batch file into raw.games.

Idempotent — loading the same file twice changes nothing. Rows whose payload
is unchanged are skipped, so loaded_at only moves when the data actually did.

Usage: venv/bin/python scripts/load_games.py [path/to/file.jsonl]
       (default: the most recently written .jsonl in data/raw/)
"""
import json
import sys
from pathlib import Path

from psycopg.types.json import Jsonb

from common import RAW_DIR, connect

UPSERT = """
	insert into raw.games (id, data)
	values (%s, %s)
	on conflict (id) do update
		set data = excluded.data,
			loaded_at = now()
		where games.data is distinct from excluded.data
	returning (xmax = 0) as was_insert
"""
# xmax is a Postgres system column: 0 on a freshly inserted row, non-zero on an
# updated one. No row is returned at all when the WHERE skips an unchanged game.


def pick_file():
	if len(sys.argv) > 1:
		return Path(sys.argv[1])
	files = sorted(RAW_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
	if not files:
		sys.exit(f"No .jsonl files in {RAW_DIR}")
	return files[-1]


def main():
	path = pick_file()
	inserted = updated = unchanged = 0

	with connect() as conn, conn.cursor() as cur, open(path) as f:
		for line in f:
			game = json.loads(line)
			cur.execute(UPSERT, (game["id"], Jsonb(game)))
			row = cur.fetchone()
			if row is None:
				unchanged += 1
			elif row[0]:
				inserted += 1
			else:
				updated += 1

	print(f"{path.name}: {inserted} inserted, {updated} updated, {unchanged} unchanged")


if __name__ == "__main__":
	main()
