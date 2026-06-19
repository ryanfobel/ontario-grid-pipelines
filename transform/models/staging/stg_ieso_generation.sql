{{ config(materialized='view') }}

select
    timestamp::timestamptz          as ts,
    coalesce(nuclear, 0)::double    as nuclear_mw,
    coalesce(gas, 0)::double        as gas_mw,
    coalesce(hydro, 0)::double      as hydro_mw,
    coalesce(wind, 0)::double       as wind_mw,
    coalesce(solar, 0)::double      as solar_mw,
    coalesce(biofuel, 0)::double    as biofuel_mw,
    -- "other" is NULL for 2019-05+ fuel-mix CSV rows (no such category in that source)
    coalesce(other, 0)::double      as other_mw,
    coalesce(total, 0)::double      as total_mw
from {{ source('raw', 'ieso_generation') }}
