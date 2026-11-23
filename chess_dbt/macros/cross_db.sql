{#
	Cross-database helpers: one call site in the models, one implementation per adapter.

	adapter.dispatch('name') looks for <adapter>__name (postgres__, databricks__),
	falling back to default__name. Models stay dialect-free; dialect lives here.
#}


{# ---- json_text: text value at a JSON path; null if missing ----
	json_text('data', ['players', 'white', 'rating'])
	  postgres   -> data->'players'->'white'->>'rating'
	  databricks -> data:players.white.rating::string
#}
{% macro json_text(column, path) -%}
	{{ return(adapter.dispatch('json_text')(column, path)) }}
{%- endmacro %}

{% macro default__json_text(column, path) -%}
	{{ exceptions.raise_compiler_error("json_text: no implementation for " ~ target.type) }}
{%- endmacro %}

{% macro postgres__json_text(column, path) -%}
	{{ column }}{% for key in path[:-1] %}->'{{ key }}'{% endfor %}->>'{{ path[-1] }}'
{%- endmacro %}

{% macro databricks__json_text(column, path) -%}
	{{ column }}:{{ path | join('.') }}::string
{%- endmacro %}


{# ---- json_has_key: does the object at path contain key? ----
	json_has_key('data', ['players', 'white'], 'user')
	  postgres   -> (data->'players'->'white' ? 'user')
	  databricks -> (data:players.white.user is not null)
#}
{% macro json_has_key(column, path, key) -%}
	{{ return(adapter.dispatch('json_has_key')(column, path, key)) }}
{%- endmacro %}

{% macro default__json_has_key(column, path, key) -%}
	{{ exceptions.raise_compiler_error("json_has_key: no implementation for " ~ target.type) }}
{%- endmacro %}

{% macro postgres__json_has_key(column, path, key) -%}
	({{ column }}{% for k in path %}->'{{ k }}'{% endfor %} ? '{{ key }}')
{%- endmacro %}

{% macro databricks__json_has_key(column, path, key) -%}
	({{ column }}:{{ (path + [key]) | join('.') }} is not null)
{%- endmacro %}


{# ---- epoch_ms_to_timestamp: epoch milliseconds -> timestamp, truncated to the second ---- #}
{% macro epoch_ms_to_timestamp(expr) -%}
	{{ return(adapter.dispatch('epoch_ms_to_timestamp')(expr)) }}
{%- endmacro %}

{% macro default__epoch_ms_to_timestamp(expr) -%}
	{{ exceptions.raise_compiler_error("epoch_ms_to_timestamp: no implementation for " ~ target.type) }}
{%- endmacro %}

{% macro postgres__epoch_ms_to_timestamp(expr) -%}
	to_timestamp(cast({{ expr }} as bigint) / 1000)
{%- endmacro %}

{% macro databricks__epoch_ms_to_timestamp(expr) -%}
	timestamp_seconds(cast({{ expr }} as bigint) div 1000)
{%- endmacro %}


{# ---- local_date: calendar date of a timestamp in var('local_timezone') ----
	Must not depend on the session time zone (Postgres here runs in New York,
	the Databricks warehouse in UTC — a plain cast to date would silently differ).
	  postgres:   timestamptz AT TIME ZONE 'tz' -> local wall-clock timestamp
	  databricks: convert_timezone('tz', ts)  -> local wall-clock TIMESTAMP_NTZ
#}
{% macro local_date(ts) -%}
	{{ return(adapter.dispatch('local_date')(ts)) }}
{%- endmacro %}

{% macro default__local_date(ts) -%}
	{{ exceptions.raise_compiler_error("local_date: no implementation for " ~ target.type) }}
{%- endmacro %}

{% macro postgres__local_date(ts) -%}
	cast(({{ ts }}) at time zone '{{ var("local_timezone") }}' as date)
{%- endmacro %}

{% macro databricks__local_date(ts) -%}
	cast(convert_timezone('{{ var("local_timezone") }}', {{ ts }}) as date)
{%- endmacro %}


{# ---- word_count: number of space-separated tokens; 0 for null or '' ----
	Gotcha: Spark's split('', ' ') returns [''] (size 1), so Databricks needs an
	explicit empty check. Postgres string_to_array('', ' ') is {} (length null).
#}
{% macro word_count(expr) -%}
	{{ return(adapter.dispatch('word_count')(expr)) }}
{%- endmacro %}

{% macro default__word_count(expr) -%}
	{{ exceptions.raise_compiler_error("word_count: no implementation for " ~ target.type) }}
{%- endmacro %}

{% macro postgres__word_count(expr) -%}
	coalesce(array_length(string_to_array({{ expr }}, ' '), 1), 0)
{%- endmacro %}

{% macro databricks__word_count(expr) -%}
	case when coalesce({{ expr }}, '') = '' then 0 else size(split({{ expr }}, ' ')) end
{%- endmacro %}
