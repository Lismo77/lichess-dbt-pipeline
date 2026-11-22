-- fct_my_games assumes I'm in every game: if I'm not white, it labels me black.
-- A game I'm not in would get a wrong color, rating, and result with no error.
-- Singular test: returns the offending rows; dbt fails the test if any come back.
select game_id, white_username, black_username
from {{ ref('stg_games') }}
where white_username is distinct from '{{ var("lichess_username") }}'
	and black_username is distinct from '{{ var("lichess_username") }}'
