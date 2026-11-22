-- One row per game. JSON paths and dialect-specific functions go through the
-- cross-db macros in macros/cross_db.sql, so this model runs on Postgres and Databricks.

with source as (
	select * from {{ source('raw', 'games') }}
),

-- Databricks bronze is append-only and holds the same game once per batch file
-- (fetch lookback). Keep the copy with the latest move = most recent game state.
-- On Postgres (upserted, already unique) this is a no-op.
deduped as (
	select
		*,
		row_number() over (
			partition by id
			order by cast({{ json_text('data', ['lastMoveAt']) }} as bigint) desc, loaded_at desc
		) as copy_rank
	from source
)

select
	id								as game_id,
	cast({{ json_text('data', ['rated']) }} as boolean)		as is_rated,
	{{ json_text('data', ['speed']) }}				as speed,
	{{ json_text('data', ['status']) }}				as status,
	{{ json_text('data', ['winner']) }}				as winner,
	{{ epoch_ms_to_timestamp(json_text('data', ['createdAt'])) }}	as created_at,
	{{ json_text('data', ['players', 'white', 'user', 'name']) }}	as white_username,
	{{ json_text('data', ['players', 'black', 'user', 'name']) }}	as black_username,
	cast({{ json_text('data', ['players', 'white', 'rating']) }} as int)	as white_rating,
	cast({{ json_text('data', ['players', 'black', 'rating']) }} as int)	as black_rating,
	{{ json_has_key('data', ['players', 'white'], 'user') }}	as white_has_account,
	{{ json_has_key('data', ['players', 'black'], 'user') }}	as black_has_account,
	cast({{ json_text('data', ['players', 'white', 'aiLevel']) }} as int)	as white_ai_level,
	cast({{ json_text('data', ['players', 'black', 'aiLevel']) }} as int)	as black_ai_level,
	{{ word_count(json_text('data', ['moves'])) }}			as ply_count,
	{{ json_text('data', ['opening', 'eco']) }}			as opening_eco,
	{{ json_text('data', ['opening', 'name']) }}			as opening_name,
	cast({{ json_text('data', ['opening', 'ply']) }} as int)	as opening_ply
from deduped
where copy_rank = 1
