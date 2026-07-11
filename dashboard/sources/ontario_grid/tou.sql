SELECT
    effective_date,
    rate_column,
    value_cents_per_kwh
FROM main_staging.stg_oeb_rates
WHERE rate_type = 'Time-of-Use (TOU) rates'
ORDER BY effective_date DESC
LIMIT 90
