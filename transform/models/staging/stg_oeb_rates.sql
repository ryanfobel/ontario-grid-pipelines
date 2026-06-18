{{ config(materialized='view') }}

select
    effective_date::date        as effective_date,
    rate_type,
    rate_column,
    value_cents_per_kwh::double as value_cents_per_kwh
from {{ source('raw', 'oeb_rates') }}
