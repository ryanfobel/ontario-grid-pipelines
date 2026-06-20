{{ config(materialized='view') }}

{% set has_live = source_exists('gridwatch_readings') %}
{% set has_hist = source_exists('gridwatch_readings_historical') %}

{% if not has_live and not has_hist %}
select null::timestamptz as ts, 0::double as imports_mw, 0::double as exports_mw,
       0::double as net_import_exports_mw, 0::double as power_generated_mw,
       0::double as ontario_demand_mw, 0::double as total_emissions_tonnes,
       0::double as co2e_intensity_gco2_per_kwh, 0::double as nuclear_mw,
       0::double as nuclear_pct, 0::double as hydro_mw, 0::double as hydro_pct,
       0::double as gas_mw, 0::double as gas_pct, 0::double as wind_mw,
       0::double as wind_pct, 0::double as biofuel_mw, 0::double as biofuel_pct,
       0::double as solar_mw, 0::double as solar_pct
where false

{% else %}

with combined as (
    {% if has_hist %}
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
        solar_pct::double                   as solar_pct,
        0 as _priority
    from raw.gridwatch_readings_historical
    {% endif %}

    {% if has_hist and has_live %}union all{% endif %}

    {% if has_live %}
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
        solar_pct::double                   as solar_pct,
        1 as _priority
    from raw.gridwatch_readings
    {% endif %}
)

select ts, imports_mw, exports_mw, net_import_exports_mw, power_generated_mw,
       ontario_demand_mw, total_emissions_tonnes, co2e_intensity_gco2_per_kwh,
       nuclear_mw, nuclear_pct, hydro_mw, hydro_pct, gas_mw, gas_pct,
       wind_mw, wind_pct, biofuel_mw, biofuel_pct, solar_mw, solar_pct
from combined
qualify row_number() over (partition by ts order by _priority desc) = 1

{% endif %}
