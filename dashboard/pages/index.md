# Ontario Grid — Overview

```sql latest
SELECT * FROM ontario_grid.latest
```

```sql generation
SELECT * FROM ontario_grid.generation
```

```sql monthly
SELECT * FROM ontario_grid.monthly
```

```sql co2trend
SELECT * FROM ontario_grid.co2trend
```

## Current Snapshot

<BigValue
    data={latest}
    value=clean_pct
    fmt='#,##0.0'
    title='Clean Energy %'
/>

<BigValue
    data={latest}
    value=total_mw
    fmt='#,##0'
    title='Total Output (MW)'
/>

<BigValue
    data={latest}
    value=co2e_intensity_gco2_per_kwh
    fmt='#,##0'
    title='CO₂ Intensity (g/kWh)'
/>

<BigValue
    data={latest}
    value=hour
    fmt='mmm d, yyyy h:mm a'
    title='As of'
/>

## Generation Mix (Last 30 Days)

<AreaChart
    data={monthly}
    x=day
    y={['nuclear', 'hydro', 'wind', 'solar', 'biofuel', 'gas']}
    title='Daily Average Generation by Fuel Type (MW)'
    yAxisTitle='MW'
    chartAreaHeight=300
/>

## CO₂ Intensity (Last 30 Days)

<LineChart
    data={co2trend}
    x=hour
    y=co2
    title='CO₂ Intensity (g CO₂e / kWh)'
    yAxisTitle='g/kWh'
    chartAreaHeight=250
/>

## Recent Generation (Last Year - Hourly)

<AreaChart
    data={generation}
    x=hour
    y={['nuclear_mw', 'hydro_mw', 'wind_mw', 'solar_mw', 'biofuel_mw', 'gas_mw']}
    title='Hourly Generation by Fuel Type (MW) - Last 8760 Hours'
    yAxisTitle='MW'
    chartAreaHeight=300
/>

---

## Data Sources

This dashboard combines three authoritative Ontario electricity data sources:

- **[IESO (Independent Electricity System Operator)](https://www.ieso.ca/)** - Hourly generation by fuel type (nuclear, hydro, wind, solar, biofuel, gas)
  - Source: [Generator Output by Fuel Type Reports](https://www.ieso.ca/Power-Data/Data-Directory) (monthly CSV files, 2010-present)

- **[Gridwatch.ca](https://live.gridwatch.ca/)** - Real-time CO₂ intensity monitoring
  - Calculates grid carbon intensity using IESO generation data + fuel emission factors
  - Updates hourly with current grid conditions

- **[Ontario Energy Board (OEB)](https://www.oeb.ca/)** - Electricity rates
  - Time-of-Use (TOU), Tiered, and Ultra-Low Overnight (ULO) pricing
  - Historical rate changes since 2010

**Update Frequency**: Dashboard data refreshes nightly via automated GitHub Actions pipeline.

**Historical Coverage**: 16+ years (2010-present) of hourly electricity generation and carbon intensity data.
