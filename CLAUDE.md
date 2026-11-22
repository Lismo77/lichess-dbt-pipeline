# Chess Analytics

Personal analytics on my Lichess games (user `lismobegins`). Learning project for a
pivot into data engineering — Claude works as a full collaborator here, but explains
every change like a teacher (what, why, and the DE concept behind it).

## Pipeline

```
Lichess API ──fetch_games.py──▶ data/raw/*.jsonl ──load_games.py──▶ Postgres raw.games ──dbt──▶ dbt_dev.*
```

- `raw.games(id text pk, data jsonb, loaded_at timestamptz)` — one row per game, full API payload; loads upsert on `id`.
- dbt project lives in `chess_dbt/`. Target schema: `dbt_dev`. Profile is in `~/.dbt/profiles.yml` (not in repo).
- Layers: `models/staging/` (1:1 with source, rename + cast only) → `models/marts/` (`fct_`, `dim_`, `agg_`).
- `models/example/` is dbt init scaffolding — slated for deletion.

## Commands

All run from the repo root unless noted. The venv is NOT auto-activated; use the full path.

- Fetch: `venv/bin/python scripts/fetch_games.py`
- Load:  `venv/bin/python scripts/load_games.py`
- dbt (from `chess_dbt/`): `../venv/bin/dbt build` (run + test), `../venv/bin/dbt build -s <model>+` (model and downstream)
- Ad-hoc SQL: `set -a; . ./.env; set +a; PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB"`

## Conventions

- Postgres SQL, lowercase keywords, tabs for indentation, CTEs that `select * from {{ ref(...) }}` at the top.
- Percentages: `round(100.0 * x / nullif(n, 0), 1)` — always guard the divisor.
- Analysis marts filter to `is_rated and not is_vs_bot` unless the model name says otherwise.

## Data facts (verified 2026-11-22, 374 games)

- `winner` is null only for real draws (stalemate, draw, and timeout/outoftime with insufficient material). No `aborted` games seen yet — if they appear, `fct_my_games.result` will wrongly call them draws.
- Bot opponents have no `players.<color>.user` key; that's how `is_vs_bot` is derived (and why usernames can be null).
- `dim_openings` grain is `(opening_eco, opening_name)` — names repeat across ECO codes.
- One game has a null ECO; it drops out of opening aggregates via inner join.

## Testing

- Generic tests live in each folder's `schema.yml` (dbt 1.12 syntax: test params go under `arguments:`).
- Singular tests in `chess_dbt/tests/`. `accepted_values` lists encode the *valid domain*, not just observed values.
- When adding a test, make it fail once on purpose to prove it can — stage the file first so `git restore` works.

## Working agreement

- Verify before claiming done: `dbt build` passes for the touched models, and query the output when logic changed.
- Never print or commit `.env` contents.
- Small, reviewable changes; one concern per commit. Explain the change and the concept in the reply.
- Loop me in (ask) on modeling decisions — grain, naming, what a metric means. Mechanical work (tests, docs, refactors with no output change) can just be done and explained.
