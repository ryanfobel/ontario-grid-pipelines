SELECT
    hour,
    total_mw,
    clean_pct,
    co2e_intensity_gco2_per_kwh
FROM main_marts.fct_co2_intensity
ORDER BY hour DESC
LIMIT 1
