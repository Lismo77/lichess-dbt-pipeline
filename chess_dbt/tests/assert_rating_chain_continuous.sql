-- Invariant: within a speed, each rated game starts at the rating the previous one
-- ended at. agg_rating_daily relies on this (net change = sum of diffs).
-- A failure means something other than a game moved my rating — e.g. Lichess
-- refunding points after an opponent is banned for cheating. Investigate, then
-- decide whether the daily model needs to account for it.
-- Needs the complete game history (a sample has gaps by definition), so it is
-- disabled when var complete_history is false, as in CI.
{{ config(enabled=var('complete_history')) }}

with rated as (
	select
		game_id,
		speed,
		created_at,
		my_rating,
		lag(my_rating_after) over (partition by speed order by created_at, game_id) as previous_rating_after
	from {{ ref('fct_my_games') }}
	where is_rated
)

select *
from rated
where previous_rating_after is not null
	and my_rating <> previous_rating_after
