# Ontario Grid — Generation & Emissions

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
    fmt='pct1'
    title='Clean Energy'
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
    fmt='mmm d, yyyy'
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

---

*Data sources: IESO (fuel mix), Gridwatch.ca (CO₂ intensity), OEB (electricity rates). Updated nightly.*
