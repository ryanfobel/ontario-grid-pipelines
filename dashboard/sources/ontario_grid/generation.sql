SELECT
    hour,
    nuclear_mw,
    hydro_mw,
    wind_mw,
    solar_mw,
    biofuel_mw,
    gas_mw,
    total_mw,
    clean_pct
FROM main.fct_grid_generation
ORDER BY hour DESC
LIMIT 8760
