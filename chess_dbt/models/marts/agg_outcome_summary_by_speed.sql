select
	speed,
	count(*) as total_games,
	count(*) filter (where result = 'win') as wins,
	count(*) filter (where result = 'loss') as losses,
	count(*) filter (where result = 'draw') as draws,
	round(100.0 * count(*) filter (where result = 'win') / nullif(count(*),0),1) as win_pct,
	round(100.0 * count(*) filter (where result = 'loss') / nullif(count(*),0),1) as loss_pct,
	round(100.0 * count(*) filter (where result = 'draw') / nullif(count(*),0),1) as draw_pct
from {{ ref('fct_my_games') }}
where is_rated = true
	and opponent_type = 'human'
group by speed
order by total_games desc

