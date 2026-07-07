SELECT
    DATE_TRUNC('month', hour) as month,
    ROUND(AVG(co2e_intensity_gco2_per_kwh), 1) as avg_co2_intensity,
    ROUND(MIN(co2e_intensity_gco2_per_kwh), 1) as min_co2_intensity,
    ROUND(MAX(co2e_intensity_gco2_per_kwh), 1) as max_co2_intensity
FROM main.fct_co2_intensity
WHERE co2e_intensity_gco2_per_kwh IS NOT NULL
GROUP BY DATE_TRUNC('month', hour)
ORDER BY month
