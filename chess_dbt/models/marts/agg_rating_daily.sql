-- Rating history: one row per speed per local calendar day with rated games.
-- Lichess rates each speed separately, so each speed is its own line on a chart.
-- Provisional games are kept; includes_provisional flags the days they touch.

with games as (
	select
		*,
		{{ local_date('created_at') }} as played_on
	from {{ ref('fct_my_games') }}
	where is_rated
		and opponent_type = 'human'
),

-- Number each day's games from both ends to find the first and last game.
ordered as (
	select
		*,
		row_number() over (partition by speed, played_on order by created_at, game_id)			as nth_game,
		row_number() over (partition by speed, played_on order by created_at desc, game_id desc)	as nth_from_last
	from games
)

select
	speed,
	played_on,
	count(*)						as games_played,
	count(*) filter (where result = 'win')			as wins,
	count(*) filter (where result = 'loss')			as losses,
	count(*) filter (where result = 'draw')			as draws,
	max(case when nth_game = 1 then my_rating end)		as opening_rating,
	max(case when nth_from_last = 1 then my_rating_after end) as closing_rating,
	max(case when nth_from_last = 1 then my_rating_after end)
		- max(case when nth_game = 1 then my_rating end)	as net_change,
	max(greatest(my_rating, my_rating_after))		as day_high,
	min(least(my_rating, my_rating_after))			as day_low,
	max(case when my_rating_is_provisional then 1 else 0 end) = 1 as includes_provisional
from ordered
group by speed, played_on
