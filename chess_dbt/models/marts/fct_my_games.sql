-- One row per real game I played, from my perspective.
-- Excludes stream-setup games vs the Lichess AI (see var setup_game_max_plies).

with games as (
	select * from {{ ref('stg_games') }}
),

-- Decide which side I'm on once; every perspective column below keys off it.
-- "is not distinct from" is null-safe: an anonymous/AI white player has a null
-- username, and null = 'x' is null (not false).
sided as (
	select
		*,
		white_username is not distinct from '{{ var("lichess_username") }}' as i_am_white
	from games
),

perspective as (
	select
		game_id,
		speed,
		status,
		is_rated,
		created_at,
		ply_count,
		case when i_am_white then 'white' else 'black' end		as my_color,
		case when i_am_white then white_rating else black_rating end	as my_rating,
		case when i_am_white then black_username else white_username end as opponent_username,
		case
			when (case when i_am_white then black_ai_level else white_ai_level end) is not null then 'ai'
			when (case when i_am_white then black_has_account else white_has_account end) then 'human'
			else 'anonymous'
		end as opponent_type,
		case when i_am_white then black_ai_level else white_ai_level end as opponent_ai_level,
		case
			when winner is null then 'draw'
			when winner = case when i_am_white then 'white' else 'black' end then 'win'
			else 'loss'
		end as result,
		opening_eco,
		opening_name
	from sided
)

select *
from perspective
where not (
	opponent_type = 'ai'
	and ply_count <= {{ var('setup_game_max_plies') }}
)
