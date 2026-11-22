# Chess Analytics

[![dbt CI](https://github.com/Lismo77/lichess-dbt-pipeline/actions/workflows/dbt-ci.yml/badge.svg)](https://github.com/Lismo77/lichess-dbt-pipeline/actions/workflows/dbt-ci.yml)

ELT pipeline over my Lichess games. Python extracts from the Lichess API and lands raw JSON;
one dbt project transforms it into tested, documented analytics tables on **both Postgres and
Databricks**, with identical results.

```
                                   ┌─ load_games.py ──────▶ Postgres raw.games ──────────┐
Lichess API ─▶ fetch_games.py ─▶ data/raw/*.jsonl                                    dbt ─▶ marts
                                   └─ load_databricks.py ─▶ UC volume ─▶ COPY INTO ─▶ ┘
                                                            raw.lichess.games (bronze)
```

## Design notes

- **Raw is a faithful copy of the API.** Nothing is filtered at ingest; junk (stream-setup games,
  zero-move games) is excluded in dbt, where rules are versioned, tested, and reversible.
- **Incremental, idempotent loads.** Fetch pulls from the newest stored game minus a 14-day
  lookback (Lichess filters on creation time, so late-finishing correspondence games need the
  overlap). Re-running any step is safe.
- **Two dedupe strategies, same answer.** Postgres upserts on game id (dedupe on write).
  Databricks bronze is append-only and `stg_games` keeps the latest copy (dedupe on read).
- **One project, two dialects.** Models never contain dialect-specific SQL; JSON access and
  date/array functions go through `adapter.dispatch` macros in `macros/cross_db.sql`.
  `scripts/check_parity.py` verifies both targets produce identical rows.
- **CI** builds and tests every model on a throwaway Postgres 18 with a fixture of 25
  anonymized edge-case games.

## Setup from scratch

Requires Python 3.12+ and a local Postgres. Databricks is optional.

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env              # then fill in token, username, DB credentials
direnv allow                      # optional: auto-loads .env in this repo (see below)
set -a; . ./.env; set +a          # ...or load it manually for this shell
PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -f sql/postgres/001_create_raw.sql
```

The dbt profile is committed at `chess_dbt/profiles.yml` and holds no secrets — every value is
an `env_var()` reference. dbt (1.12+) loads `.env` automatically from the current directory or
any parent. Check with `cd chess_dbt && ../venv/bin/dbt debug`.

**direnv** (optional): the committed `.envrc` loads `.env` into your shell whenever you `cd`
into the repo, so `psql` and other tools see the variables too. Install with
`sudo dnf install direnv`, add `eval "$(direnv hook bash)"` to `~/.bashrc`, then `direnv allow`.

## Run

```bash
venv/bin/python scripts/fetch_games.py      # incremental; --full for entire history

# Postgres
venv/bin/python scripts/load_games.py       # upserts newest batch
cd chess_dbt && ../venv/bin/dbt build       # build models + run all tests

# Databricks (needs DATABRICKS_* in .env)
venv/bin/python scripts/load_databricks.py  # creates bronze if needed, uploads new files, COPY INTO
cd chess_dbt && ../venv/bin/dbt build --target databricks

venv/bin/python scripts/check_parity.py     # both targets, every model, row-for-row
```

## Models

| Model | Grain | Notes |
|---|---|---|
| `stg_games` | game | JSON → typed columns; dedupes Databricks bronze |
| `fct_my_games` | game I played | my color/rating/result, `opponent_type`; setup and zero-move games excluded |
| `dim_openings` | (eco, name) | opening family / variation split |
| `agg_outcome_summary_by_speed` | speed | rated games vs humans |
| `agg_outcome_by_openings` | opening family | rated games vs humans |
