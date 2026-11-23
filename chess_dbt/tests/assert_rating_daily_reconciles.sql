-- The day's net change must equal the sum of that day's per-game rating diffs.
-- Checks agg_rating_daily's first/last-game logic independently: if the ordering
-- or the day assignment were wrong, these two numbers would drift apart.
with diffs as (
	select
		speed,
		{{ local_date('created_at') }}	as played_on,
		sum(my_rating_diff)		as sum_of_diffs
	from {{ ref('fct_my_games') }}
	where is_rated
		and opponent_type = 'human'
	group by 1, 2
)

select d.speed, d.played_on, d.net_change, x.sum_of_diffs
from {{ ref('agg_rating_daily') }} d
join diffs x on x.speed = d.speed and x.played_on = d.played_on
where d.net_change <> x.sum_of_diffs
