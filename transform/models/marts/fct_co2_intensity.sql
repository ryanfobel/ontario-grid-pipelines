{{ config(materialized='table') }}

-- Join IESO generation with gridwatch CO2 intensity on the same hour.
-- gridwatch.ca provides the measured intensity; we can also derive a proxy
-- from the fuel mix (useful for hours with missing gridwatch data).
select
    g.hour,
    g.total_mw,
    g.clean_pct,
    gw.co2_intensity_gco2_per_kwh
from {{ ref('fct_grid_generation') }} g
left join {{ ref('stg_gridwatch') }} gw
    on date_trunc('hour', gw.ts) = g.hour
