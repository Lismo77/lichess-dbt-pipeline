import json
import os

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()

conn = psycopg.connect(
	host=os.getenv("PG_HOST"),
	dbname=os.getenv("PG_DB"),
	user=os.getenv("PG_USER"),
	password=os.getenv("PG_PASSWORD"),
)

inserted = 0
with conn, conn.cursor() as cur:
	with open("data/raw/lismobegins_games.jsonl") as f:
		for line in f:
			game = json.loads(line)
			cur.execute(
				"""
				INSERT INTO raw.games (id, data)
				VALUES (%s, %s)
				ON CONFLICT (id) DO UPDATE
				SET data = EXCLUDED.data,
					loaded_at = now()
				""",
				(game["id"], Jsonb(game)),
			)
			inserted += cur.rowcount

print(f"Inserted {inserted} new games")
