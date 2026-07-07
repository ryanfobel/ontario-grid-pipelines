SELECT
    DATE_TRUNC('month', hour) as month,
    ROUND(AVG(nuclear_mw), 0) as avg_nuclear,
    ROUND(AVG(hydro_mw), 0) as avg_hydro,
    ROUND(AVG(wind_mw), 0) as avg_wind,
    ROUND(AVG(solar_mw), 0) as avg_solar,
    ROUND(AVG(biofuel_mw), 0) as avg_biofuel,
    ROUND(AVG(gas_mw), 0) as avg_gas,
    ROUND(AVG(total_mw), 0) as avg_total,
    ROUND(AVG(clean_pct), 1) as avg_clean_pct
FROM main.fct_grid_generation
GROUP BY DATE_TRUNC('month', hour)
ORDER BY month
