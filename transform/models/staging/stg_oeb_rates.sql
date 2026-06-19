{{ config(materialized='view') }}

{% if not source_exists('oeb_rates') %}
select null::date as effective_date, null::varchar as rate_type,
       null::varchar as rate_column, 0::double as value_cents_per_kwh
where false
{% else %}
select
    effective_date::date        as effective_date,
    rate_type,
    rate_column,
    value_cents_per_kwh::double as value_cents_per_kwh
from {{ source('raw', 'oeb_rates') }}
{% endif %}
