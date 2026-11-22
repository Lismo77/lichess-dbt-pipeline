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
direnv allow                      # optional: auto-loads .env in this repo (see below)
set -a; . ./.env; set +a          # ...or load it manually for this shell
PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -f sql/001_create_raw.sql
```

dbt needs a `chess_dbt` profile in `~/.dbt/profiles.yml`. Credentials come from `.env`, never
from the profile itself:

```yaml
chess_dbt:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('PG_HOST') }}"
      port: 5432
      dbname: "{{ env_var('PG_DB') }}"
      user: "{{ env_var('PG_USER') }}"
      pass: "{{ env_var('PG_PASSWORD') }}"
      schema: dbt_dev
      threads: 1
```

dbt (1.12+) loads `.env` automatically from the current directory or any parent, so this works
anywhere inside the repo. Check with `cd chess_dbt && ../venv/bin/dbt debug`.

**direnv** (optional): the committed `.envrc` loads `.env` into your shell whenever you `cd`
into the repo, so `psql` and other tools see the variables too. Install with
`sudo dnf install direnv`, add `eval "$(direnv hook bash)"` to `~/.bashrc`, then `direnv allow`.

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
