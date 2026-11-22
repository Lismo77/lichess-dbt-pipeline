"""Load (Databricks): upload JSONL batch files to a UC volume, then COPY INTO bronze.

Two layers of idempotency, so this is always safe to re-run:
  1. Upload skips files already in the volume.
  2. COPY INTO tracks which files it has loaded and never loads one twice.

Bronze is append-only — duplicate games across files are expected and removed
in stg_games. Compare load_games.py (Postgres), which upserts instead.

Usage: venv/bin/python scripts/load_databricks.py   (syncs every file in data/raw/)
"""
import os
from pathlib import Path

from databricks import sql
from databricks.sdk import WorkspaceClient

from common import RAW_DIR, REPO_ROOT

VOLUME = "/Volumes/raw/lichess/landing"
DDL = REPO_ROOT / "sql" / "databricks" / "001_create_raw.sql"

COPY_INTO = f"""
	copy into raw.lichess.games
	from (
		select
			data:id::string		as id,
			data,
			_metadata.file_path	as source_file,
			current_timestamp()	as loaded_at
		from '{VOLUME}'
	)
	fileformat = json
	format_options ('singleVariantColumn' = 'data')
"""
# singleVariantColumn: parse each JSON line into ONE variant column instead of
# inferring a schema — the bronze equivalent of Postgres jsonb.
# _metadata is a hidden column Databricks exposes on file sources.


def sql_statements(path):
	"""Split a .sql file on ';', dropping comment-only chunks."""
	text = "\n".join(l for l in Path(path).read_text().splitlines() if not l.strip().startswith("--"))
	return [s.strip() for s in text.split(";") if s.strip()]


def main():
	host = os.environ["DATABRICKS_HOST"]
	conn = sql.connect(
		server_hostname=host,
		http_path=os.environ["DATABRICKS_HTTP_PATH"],
		access_token=os.environ["DATABRICKS_TOKEN"],
	)
	with conn, conn.cursor() as cur:
		for stmt in sql_statements(DDL):
			cur.execute(stmt)

		# 1. Upload any local batch file the volume doesn't have yet.
		ws = WorkspaceClient(host=f"https://{host}", token=os.environ["DATABRICKS_TOKEN"])
		in_volume = {f.name for f in ws.files.list_directory_contents(VOLUME)}
		uploaded = 0
		for path in sorted(RAW_DIR.glob("*.jsonl")):
			if path.name not in in_volume:
				with open(path, "rb") as f:
					ws.files.upload(f"{VOLUME}/{path.name}", f, overwrite=False)
				uploaded += 1
		print(f"Uploaded {uploaded} new file(s) to {VOLUME} ({len(in_volume) + uploaded} total)")

		# 2. COPY INTO picks up only files it hasn't loaded before.
		cur.execute(COPY_INTO)
		affected, inserted = cur.fetchone()[:2]
		print(f"COPY INTO raw.lichess.games: {inserted} rows inserted")

		cur.execute("select count(*), count(distinct id) from raw.lichess.games")
		rows, games = cur.fetchone()
		print(f"Bronze now: {rows} rows, {games} distinct games ({rows - games} duplicates for staging to resolve)")


if __name__ == "__main__":
	main()
