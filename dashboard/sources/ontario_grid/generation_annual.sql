SELECT
    YEAR(hour) as year,
    ROUND(AVG(nuclear_mw), 0) as avg_nuclear_mw,
    ROUND(AVG(hydro_mw), 0) as avg_hydro_mw,
    ROUND(AVG(wind_mw), 0) as avg_wind_mw,
    ROUND(AVG(solar_mw), 0) as avg_solar_mw,
    ROUND(AVG(biofuel_mw), 0) as avg_biofuel_mw,
    ROUND(AVG(gas_mw), 0) as avg_gas_mw,
    ROUND(AVG(total_mw), 0) as avg_total_mw,
    ROUND(AVG(clean_pct), 1) as avg_clean_pct
FROM main.fct_grid_generation
GROUP BY YEAR(hour)
ORDER BY year
