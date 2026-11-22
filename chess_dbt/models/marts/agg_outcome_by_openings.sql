with games as (
	select * from {{ ref('fct_my_games') }}
),

openings as (
	select * from {{ ref('dim_openings') }}
)

select
	o.opening_family,
	count(*) as total_games,
	count(*) filter (where g.result = 'win') as wins,
	count(*) filter (where g.result = 'loss') as losses,
	count(*) filter (where g.result = 'draw') as draws,
	round(100.0 * count(*) filter (where g.result = 'win') / nullif(count(*),0), 1) as win_pct
from games g
join openings o on g.opening_eco = o.opening_eco
	and g.opening_name = o.opening_name
where g.is_rated = true
	and not g.is_vs_bot
group by o.opening_family
order by total_games desc
