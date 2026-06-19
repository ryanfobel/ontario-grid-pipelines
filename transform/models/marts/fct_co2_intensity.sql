{{ config(materialized='table') }}

-- Wide hourly fact table: IESO fuel mix + gridwatch live readings joined on hour.
-- IESO is the authoritative source for generation; gridwatch adds demand,
-- import/export, emissions, and CO2 intensity from the live scraper.
select
    coalesce(g.hour, date_trunc('hour', gw.ts))    as hour,

    -- IESO fuel mix (MW)
    g.nuclear_mw,
    g.gas_mw,
    g.hydro_mw,
    g.wind_mw,
    g.solar_mw,
    g.biofuel_mw,
    g.total_mw,
    g.clean_pct,

    -- Gridwatch live readings
    gw.ontario_demand_mw,
    gw.imports_mw,
    gw.exports_mw,
    gw.net_import_exports_mw,
    gw.total_emissions_tonnes,
    gw.co2e_intensity_gco2_per_kwh,

    -- Gridwatch per-source detail (percentage + MW as reported by gridwatch)
    gw.nuclear_mw       as gw_nuclear_mw,
    gw.nuclear_pct      as gw_nuclear_pct,
    gw.hydro_mw         as gw_hydro_mw,
    gw.hydro_pct        as gw_hydro_pct,
    gw.gas_mw           as gw_gas_mw,
    gw.gas_pct          as gw_gas_pct,
    gw.wind_mw          as gw_wind_mw,
    gw.wind_pct         as gw_wind_pct,
    gw.solar_mw         as gw_solar_mw,
    gw.solar_pct        as gw_solar_pct,
    gw.biofuel_mw       as gw_biofuel_mw,
    gw.biofuel_pct      as gw_biofuel_pct,

    -- Provenance flags
    (g.hour is not null)  as has_ieso,
    (gw.ts  is not null)  as has_gridwatch

from {{ ref('fct_grid_generation') }} g
full outer join {{ ref('stg_gridwatch') }} gw
    on date_trunc('hour', gw.ts) = g.hour
