select 
        speed,    
        count(*) as total_games,
        count(*) filter (where result= 'win') as wins,
        count(*) filter (where result = 'loss') as losses,
        count(*) filter (where result = 'draw') as draws,
        round(
                100.0 * count(*) filter (where result = 'win') / count(*),
                1
        ) as win_rate_pct
from {{ ref('fct_my_games') }}
where is_rated = true
	and not is_vs_bot
group by speed
order by total_games desc
