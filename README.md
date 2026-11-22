# Chess Analytics

ELT pipeline over my Lichess games: Python extracts from the Lichess API and loads raw JSON
into Postgres; dbt transforms it into tested, documented analytics tables.

```
Lichess API ─▶ fetch_games.py ─▶ data/raw/*.jsonl ─▶ load_games.py ─▶ raw.games ─▶ dbt ─▶ marts
```

## Setup from scratch

Requires Python 3.12+ and a local Postgres.

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env              # then fill in token, username, DB credentials
set -a; . ./.env; set +a
PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -f sql/001_create_raw.sql
```

dbt also needs a `chess_dbt` profile in `~/.dbt/profiles.yml` pointing at the same database
(target schema `dbt_dev`). Check it with `cd chess_dbt && ../venv/bin/dbt debug`.

## Run

```bash
venv/bin/python scripts/fetch_games.py    # incremental; --full for entire history
venv/bin/python scripts/load_games.py     # loads newest batch; idempotent
cd chess_dbt && ../venv/bin/dbt build     # build models + run all tests
```

## Models

| Model | Grain | Notes |
|---|---|---|
| `stg_games` | game | JSON → typed columns, no logic |
| `fct_my_games` | game I played | my color/rating/result, `opponent_type`; stream-setup games excluded |
| `dim_openings` | (eco, name) | opening family / variation split |
| `agg_outcome_summary_by_speed` | speed | rated games vs humans |
| `agg_outcome_by_openings` | opening family | rated games vs humans |
