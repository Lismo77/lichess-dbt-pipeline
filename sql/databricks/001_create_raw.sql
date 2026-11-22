-- Bronze landing zone for Lichess games on Databricks (Unity Catalog).
-- Idempotent; run once per workspace (scripts/load_databricks.py runs it for you).
--
--   raw.lichess.landing  volume: one JSONL file per fetch run, never modified
--   raw.lichess.games    bronze table: APPEND-ONLY copy of every row of every file
--
-- Unlike Postgres (upsert = dedupe on write), bronze keeps duplicates: the fetch
-- lookback puts the same game in several files. stg_games dedupes on read.

create schema if not exists raw.lichess
	comment 'Lichess API extracts (bronze)';

create volume if not exists raw.lichess.landing
	comment 'Raw JSONL batch files from scripts/fetch_games.py';

create table if not exists raw.lichess.games (
	id		string		comment 'Lichess game id (not unique here: duplicates across batch files)',
	data		variant		comment 'Full API payload, untouched',
	source_file	string		comment 'Volume path of the batch file this row came from',
	loaded_at	timestamp	comment 'When COPY INTO ingested the row'
)
comment 'Bronze: append-only, one row per game per batch file';
