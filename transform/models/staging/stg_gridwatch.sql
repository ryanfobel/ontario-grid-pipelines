{{ config(materialized='view') }}

select
    timestamp::timestamptz                          as ts,
    co2_intensity_gco2_per_kwh::double              as co2_intensity_gco2_per_kwh,
    generation_mw::double                           as generation_mw
from {{ source('raw', 'gridwatch_readings') }}
