SELECT
    CAST(hour AS DATE) as day,
    AVG(nuclear_mw) as nuclear,
    AVG(hydro_mw) as hydro,
    AVG(wind_mw) as wind,
    AVG(solar_mw) as solar,
    AVG(biofuel_mw) as biofuel,
    AVG(gas_mw) as gas
FROM main.fct_grid_generation
WHERE hour >= (SELECT MAX(hour) FROM main.fct_grid_generation) - INTERVAL 30 DAY
GROUP BY 1
ORDER BY 1
