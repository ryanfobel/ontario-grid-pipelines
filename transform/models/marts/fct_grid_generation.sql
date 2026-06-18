{{ config(materialized='table') }}

select
    date_trunc('hour',  ts) as hour,
    date_trunc('day',   ts) as day,
    date_trunc('month', ts) as month,
    nuclear_mw,
    gas_mw,
    hydro_mw,
    wind_mw,
    solar_mw,
    biofuel_mw,
    total_mw,
    -- Zero-emission sources: nuclear, hydro, wind, solar, biofuel
    round(
        100.0 * (nuclear_mw + hydro_mw + wind_mw + solar_mw + biofuel_mw)
        / nullif(total_mw, 0),
        1
    ) as clean_pct
from {{ ref('stg_ieso_generation') }}
