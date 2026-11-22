-- Landing table for the Lichess API. Run once per database:
--   psql -h $PG_HOST -U $PG_USER -d $PG_DB -f sql/001_create_raw.sql
-- Idempotent (IF NOT EXISTS), so re-running is safe.

create schema if not exists raw;

create table if not exists raw.games (
	id		text		primary key,		-- Lichess game id
	data		jsonb		not null,		-- full API payload, untouched
	loaded_at	timestamptz	not null default now()	-- last time this row was written
);
