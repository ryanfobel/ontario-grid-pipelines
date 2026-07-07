SELECT
    effective_date,
    rate_column,
    value_cents_per_kwh
FROM main.stg_oeb_rates
WHERE rate_type = 'Ultra-Low Overnight (ULO)'
ORDER BY effective_date DESC
LIMIT 90
