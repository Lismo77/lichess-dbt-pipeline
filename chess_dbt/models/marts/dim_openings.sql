select distinct
	opening_eco,
	opening_name,
	split_part(opening_name, ':', 1) as opening_family,
	case
		when opening_name like '%:%'
			then trim(split_part(opening_name, ':', 2))
		else null
	end as opening_variation
from {{ ref('stg_games') }}
where opening_eco is not null
