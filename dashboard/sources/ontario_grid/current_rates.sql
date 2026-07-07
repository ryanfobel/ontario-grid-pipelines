SELECT
    rate_column,
    value_cents_per_kwh
FROM main.stg_oeb_rates
WHERE rate_type = 'Time-of-Use (TOU) rates'
  AND effective_date = (
      SELECT MAX(effective_date)
      FROM main.stg_oeb_rates
      WHERE rate_type = 'Time-of-Use (TOU) rates'
  )
ORDER BY value_cents_per_kwh DESC
