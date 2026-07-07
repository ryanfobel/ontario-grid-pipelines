SELECT
    hour,
    co2e_intensity_gco2_per_kwh as co2
FROM main.fct_co2_intensity
WHERE hour >= (SELECT MAX(hour) FROM main.fct_co2_intensity) - INTERVAL 30 DAY
  AND co2e_intensity_gco2_per_kwh IS NOT NULL
ORDER BY hour
