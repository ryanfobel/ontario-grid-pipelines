{{ config(materialized='view') }}

{% set has_live = source_exists('oeb_rates') %}
{% set has_hist = source_exists('oeb_rates_historical') %}

{% if not has_live and not has_hist %}
select null::date as effective_date, null::varchar as rate_type,
       null::varchar as rate_column, 0::double as value_cents_per_kwh
where false

{% else %}

with combined as (
    {% if has_hist %}
    select
        effective_date::date        as effective_date,
        rate_type,
        rate_column,
        value_cents_per_kwh::double as value_cents_per_kwh,
        0 as _priority
    from raw.oeb_rates_historical
    {% endif %}

    {% if has_hist and has_live %}union all{% endif %}

    {% if has_live %}
    select
        effective_date::date        as effective_date,
        rate_type,
        rate_column,
        value_cents_per_kwh::double as value_cents_per_kwh,
        1 as _priority
    from raw.oeb_rates
    {% endif %}
)

select effective_date, rate_type, rate_column, value_cents_per_kwh
from combined
qualify row_number() over (
    partition by effective_date, rate_type, rate_column
    order by _priority desc
) = 1

{% endif %}
