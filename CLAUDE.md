# Chess Analytics

Personal analytics on my Lichess games (user `lismobegins`). Learning project for a
pivot into data engineering — Claude works as a full collaborator here, but explains
every change like a teacher (what, why, and the DE concept behind it).

## Pipeline

```
Lichess API ──fetch_games.py──▶ data/raw/*.jsonl ─┬─load_games.py──────▶ Postgres raw.games ─────────dbt──▶ dbt_dev.*
                                                  └─load_databricks.py─▶ raw.lichess.games (bronze) ─dbt──▶ analytics.dbt_dev.*
```

- `raw.games(id text pk, data jsonb, loaded_at timestamptz)` — one row per game, full API payload. DDL in `sql/postgres/001_create_raw.sql`.
- Extract writes one immutable timestamped batch file per run to `data/raw/` (gitignored). Load upserts on `id` and skips unchanged payloads, so it's idempotent.
- Fetch is incremental: newest `createdAt` in raw.games minus a 14-day lookback (Lichess `since` filters on creation time, so late-finishing correspondence games need the overlap).
- Shared script config (paths, username, DB connection) in `scripts/common.py`.
- dbt project lives in `chess_dbt/`. Targets: `dev` (Postgres, default) and `databricks`. Profile committed at `chess_dbt/profiles.yml`.
- Layers: `models/staging/` (1:1 with source, rename + cast only) → `models/marts/` (`fct_`, `dim_`, `agg_`).
- dbt vars in `dbt_project.yml`: `lichess_username`, `setup_game_max_plies`, `local_timezone` (day boundaries — never cast a timestamp to date directly; use the `local_date` macro), `complete_history` (CI sets false; gates whole-history tests). Username also lives in `.env` as `LICHESS_USERNAME` for the Python side — keep in sync.
- Packages: `dbt_utils` (packages.yml + committed package-lock.yml). Run `../venv/bin/dbt deps` after cloning or changing packages. Jinja is NOT rendered inside generic-test arguments — use a package test (e.g. `dbt_utils.unique_combination_of_columns`) instead of macro-built expressions.

## Commands

All run from the repo root unless noted. The venv is NOT auto-activated; use the full path.

- Fetch: `venv/bin/python scripts/fetch_games.py` (`--full` for whole history)
- Load:  `venv/bin/python scripts/load_games.py [file]` (default: newest batch)
- dbt (from `chess_dbt/`): `../venv/bin/dbt build` (run + test), `../venv/bin/dbt build -s <model>+` (model and downstream)
- Ad-hoc SQL: `set -a; . ./.env; set +a; PGPASSWORD="$PG_PASSWORD" psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB"`

- Databricks: `venv/bin/python scripts/load_databricks.py` then `../venv/bin/dbt build --target databricks`
- Parity (after building both): `venv/bin/python scripts/check_parity.py` — exit 1 on any row difference

### Databricks

- Workspace catalogs: `raw` (landing — only `lichess` + the auto-created `default`), `analytics` (dbt output). Default `workspace` catalog unused. dbt tutorial schemas were dropped 2026-11-22; `~/.dbt/profiles.yml` deleted (repo profile is the only one).
- `raw.lichess.landing` volume holds batch files; `raw.lichess.games` bronze is APPEND-ONLY (id, data VARIANT, source_file, loaded_at) with duplicate games across files. `stg_games` dedupes by latest `lastMoveAt`.
- COPY INTO is file-idempotent; never "fix" duplicates in bronze — that's staging's job.
- PATs expire: an `Invalid access token` 403 means the user must generate a new one (Settings > Developer > Access tokens) into `.env`.
- `pydantic.v1` UserWarning on every dbt run comes from metricflow (pulled in by dbt-databricks) on Python 3.14 — harmless, upstream.

### Env / secrets

- `.env` (repo root) is the single source for DB settings. `chess_dbt/profiles.yml` is committed and reads host/port/dbname/user/pass via `env_var('PG_*')` — no values in it. dbt picks it over `~/.dbt/` when run from `chess_dbt/`.
- dbt 1.12 auto-loads `.env` itself (`find_dotenv(usecwd=True)` in `dbt/cli/main.py`, walks up from cwd; shell vars win over `.env`). So dbt works from anywhere inside the repo, but fails outside it without the vars exported.
- The user's interactive shell uses direnv (root `.envrc` = `dotenv`). Claude's non-interactive shell does NOT trigger the direnv hook — keep the `set -a; . ./.env; set +a` prefix, or `direnv exec . <cmd>`.
- Never echo a secret var, even to check it's set — test with `[ -n "$VAR" ]` and print only yes/no.

### CI

- `.github/workflows/dbt-ci.yml`: on push to main / PRs, spins up `postgres:18`, runs `sql/postgres/001_create_raw.sql`, loads `ci/fixtures/games.jsonl` with the real loader, then `dbt build`. Throwaway creds in the workflow env — no GitHub Secrets needed for Postgres.
- Fixture = 25 anonymized edge-case games. When a model handles a new edge case, add a game that hits it.
- Reproduce CI locally: export tracked files with `git archive "$(git write-tree)"`, fresh venv from requirements.txt, `podman run --rm -p 5433:5432 postgres:18`, set `PG_PORT=5433`, run the workflow steps.
- Review `git status` before every commit — `git add -A` sweeps in untracked files.
- Check a pushed run with `gh run list` / `gh run watch <id> --exit-status`.

### Git / GitHub

- Remote: PUBLIC repo `Lismo77/lichess-dbt-pipeline` (portfolio piece). Assume anything committed is world-readable.
- Repo-local git email is the GitHub noreply address — never commit with a personal email.
- main has been pushed: never rewrite its history (no rebase/amend/force-push of pushed commits).
- Workflow: every change goes branch → commits → push → PR (`gh pr create`) → CI green → the user reviews and merges on GitHub. Never commit directly to main.

## Conventions

- Lowercase keywords, tabs for indentation, CTEs that `select * from {{ ref(...) }}` at the top.
- Models must run on BOTH Postgres and Databricks. No dialect-specific syntax in models (`->>`, `?`, `::`, `string_to_array`, `split`, …) — add or reuse a dispatch macro in `macros/cross_db.sql`. Prefer portable `cast(x as t)`. Verify with `check_parity.py`.
- Percentages: `round(100.0 * x / nullif(n, 0), 1)` — always guard the divisor.
- Analysis marts filter to `is_rated and opponent_type = 'human'` unless the model name says otherwise.
- Raw is a faithful copy of the API — never filter at ingest. Junk/exclusion rules live in dbt where they're reversible.

## Data facts (verified 2026-11-22, 452 games / 440 in fct, identical on both targets)

- `winner` is null only for real draws (stalemate, draw, and timeout/outoftime with insufficient material). No `aborted` games seen yet — if they appear, `fct_my_games.result` will wrongly call them draws.
- A player with no `players.<color>.user` key is either the Lichess AI (has `aiLevel`) or an anonymous human (neither key) — no account ≠ bot. `fct_my_games.opponent_type` = human / anonymous / ai.
- AI games with ≤ `setup_game_max_plies` (dbt var, 20) are OBS stream-setup junk; excluded in `fct_my_games`, kept in raw. Real Stockfish practice games are expected later and must stay in.
- The 6 anonymous games (May 2026) are probably real late-night games vs a friend — kept.
- `dim_openings` grain is `(opening_eco, opening_name)` — names repeat across ECO codes.
- Games with a null ECO drop out of opening aggregates via inner join.
- Games with 0 plies (ended before a move; Lichess still records a result) are excluded from fct. One seen: unrated, recorded as a timeout win.
- Ratings are per speed. Rating chain is continuous: each rated game's `my_rating` = previous game's `my_rating_after` (398/398 pairs; enforced by a test). First ~11 games per speed are provisional (swings up to −257 vs ±32 established) — kept and flagged.
- ~23% of games fall on a different calendar day in UTC vs America/New_York. Postgres session tz is New York, Databricks is UTC — a naive date cast silently disagrees across targets.

## Testing

- Generic tests live in each folder's `schema.yml` (dbt 1.12 syntax: test params go under `arguments:`).
- Singular tests in `chess_dbt/tests/`. `accepted_values` lists encode the *valid domain*, not just observed values.
- When adding a test, make it fail once on purpose to prove it can — stage the file first so `git restore` works.

## Working agreement

- Verify before claiming done: `dbt build` passes for the touched models, and query the output when logic changed.
- Never print or commit `.env` contents.
- Small, reviewable changes; one concern per commit. Explain the change and the concept in the reply.
- Loop me in (ask) on modeling decisions — grain, naming, what a metric means. Mechanical work (tests, docs, refactors with no output change) can just be done and explained.
