{{ config(materialized='view') }}

select
    effective_date::date            as effective_date,
    rate_class,
    rate_cents_per_kwh::double      as rate_cents_per_kwh
from {{ source('raw', 'oeb_rates') }}
