{{ config(materialized='view') }}

select
    timestamp::timestamptz              as ts,
    imports_mw::double                  as imports_mw,
    exports_mw::double                  as exports_mw,
    net_import_exports_mw::double       as net_import_exports_mw,
    power_generated_mw::double          as power_generated_mw,
    ontario_demand_mw::double           as ontario_demand_mw,
    total_emissions_tonnes::double      as total_emissions_tonnes,
    co2e_intensity_gco2_per_kwh::double as co2e_intensity_gco2_per_kwh,
    nuclear_mw::double                  as nuclear_mw,
    nuclear_pct::double                 as nuclear_pct,
    hydro_mw::double                    as hydro_mw,
    hydro_pct::double                   as hydro_pct,
    gas_mw::double                      as gas_mw,
    gas_pct::double                     as gas_pct,
    wind_mw::double                     as wind_mw,
    wind_pct::double                    as wind_pct,
    biofuel_mw::double                  as biofuel_mw,
    biofuel_pct::double                 as biofuel_pct,
    solar_mw::double                    as solar_mw,
    solar_pct::double                   as solar_pct
from {{ source('raw', 'gridwatch_readings') }}
