with games as (
	select * from {{ ref('stg_games') }}
)

select
	game_id,
	speed,
	status,
	is_rated,
	created_at,
	case
		when white_username = 'lismobegins' then 'white'
		else 'black'
	end as my_color,
	case
		when white_username = 'lismobegins' then white_rating
		else black_rating
	end as my_rating,
	case
		when white_username = 'lismobegins' then black_username
		else white_username
	end as opponent_username,
	case
		when winner is null then 'draw'
		when winner = 'white' and white_username = 'lismobegins' then 'win'
		when winner = 'black' and black_username = 'lismobegins' then 'win'
		else 'loss'
	end as result,
	not (white_is_human and black_is_human) as is_vs_bot,
	opening_eco,
	opening_name
from games
