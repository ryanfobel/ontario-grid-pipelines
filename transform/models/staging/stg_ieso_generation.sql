{{ config(materialized='view') }}

{% set has_live = source_exists('ieso_generation') %}
{% set has_hist = source_exists('ieso_generation_historical') %}

{% if not has_live and not has_hist %}
select null::timestamptz as ts, 0::double as nuclear_mw, 0::double as gas_mw,
       0::double as hydro_mw, 0::double as wind_mw, 0::double as solar_mw,
       0::double as biofuel_mw, 0::double as other_mw, 0::double as total_mw
where false

{% else %}

with combined as (
    {% if has_hist %}
    select
        timestamp::timestamptz          as ts,
        coalesce(nuclear, 0)::double    as nuclear_mw,
        coalesce(gas, 0)::double        as gas_mw,
        coalesce(hydro, 0)::double      as hydro_mw,
        coalesce(wind, 0)::double       as wind_mw,
        coalesce(solar, 0)::double      as solar_mw,
        coalesce(biofuel, 0)::double    as biofuel_mw,
        coalesce(other, 0)::double      as other_mw,
        coalesce(total, 0)::double      as total_mw,
        0 as _priority
    from raw.ieso_generation_historical
    {% endif %}

    {% if has_hist and has_live %}union all{% endif %}

    {% if has_live %}
    select
        timestamp::timestamptz          as ts,
        coalesce(nuclear, 0)::double    as nuclear_mw,
        coalesce(gas, 0)::double        as gas_mw,
        coalesce(hydro, 0)::double      as hydro_mw,
        coalesce(wind, 0)::double       as wind_mw,
        coalesce(solar, 0)::double      as solar_mw,
        coalesce(biofuel, 0)::double    as biofuel_mw,
        coalesce(other, 0)::double      as other_mw,
        coalesce(total, 0)::double      as total_mw,
        1 as _priority
    from raw.ieso_generation
    {% endif %}
)

select ts, nuclear_mw, gas_mw, hydro_mw, wind_mw, solar_mw, biofuel_mw, other_mw, total_mw
from combined
qualify row_number() over (partition by ts order by _priority desc) = 1

{% endif %}
