# Historical Trends (2010-Present)

Comprehensive analysis of 16+ years of Ontario grid data.

```sql generation_history
SELECT * FROM ontario_grid.generation_full_history
```

```sql co2_history
SELECT * FROM ontario_grid.co2_full_history
```

```sql annual_stats
SELECT * FROM ontario_grid.generation_annual
```

## Generation Mix Evolution (2010-Present)

Monthly average generation by fuel type over the complete historical period:

<AreaChart
    data={generation_history}
    x=month
    y={['avg_nuclear', 'avg_hydro', 'avg_wind', 'avg_solar', 'avg_biofuel', 'avg_gas']}
    title='Ontario Generation Mix - Monthly Averages (MW)'
    yAxisTitle='Average MW'
    chartAreaHeight=400
/>

## Clean Energy Percentage Over Time

<LineChart
    data={generation_history}
    x=month
    y=avg_clean_pct
    title='Clean Energy Percentage - Monthly Average'
    yAxisTitle='Clean Energy %'
    chartAreaHeight=300
/>

**Clean Energy** includes: Nuclear, Hydro, Wind, Solar, and Biofuel (excludes Natural Gas)

## CO₂ Intensity Historical Trend

<LineChart
    data={co2_history}
    x=month
    y={['avg_co2_intensity', 'min_co2_intensity', 'max_co2_intensity']}
    title='Grid Carbon Intensity - Monthly Statistics (g CO₂e/kWh)'
    yAxisTitle='g CO₂e/kWh'
    chartAreaHeight=350
    yMin=0
/>

Lower values indicate cleaner grid conditions. Ontario's grid is one of the cleanest in North America.

## Annual Statistics

<DataTable
    data={annual_stats}
    rows=all
>
    <Column id=year/>
    <Column id=avg_nuclear_mw fmt='#,##0' title='Nuclear (MW)'/>
    <Column id=avg_hydro_mw fmt='#,##0' title='Hydro (MW)'/>
    <Column id=avg_wind_mw fmt='#,##0' title='Wind (MW)'/>
    <Column id=avg_solar_mw fmt='#,##0' title='Solar (MW)'/>
    <Column id=avg_biofuel_mw fmt='#,##0' title='Biofuel (MW)'/>
    <Column id=avg_gas_mw fmt='#,##0' title='Gas (MW)'/>
    <Column id=avg_total_mw fmt='#,##0' title='Total (MW)'/>
    <Column id=avg_clean_pct fmt='pct1' title='Clean %'/>
</DataTable>

---

## Key Insights from Historical Data

### Fuel Mix Evolution

**Nuclear** remains Ontario's baseload power source, providing consistent ~60% of generation since coal phase-out completed in 2014.

**Hydro** provides flexible, clean generation that varies with precipitation and seasonal water availability (typically 20-25%).

**Wind** capacity has grown significantly from near-zero in 2010 to ~2,000 MW average by 2025, driven by provincial renewable energy policies.

**Solar** deployment accelerated post-2015 through Feed-in Tariff programs, though remains smaller than wind due to seasonal/diurnal generation patterns.

**Gas** serves as flexible peaking capacity and backup, filling gaps when renewables are low. Usage decreased after coal phase-out but remains essential for grid reliability.

**Coal** was completely phased out by 2014, making Ontario one of the first jurisdictions in North America to eliminate coal-fired generation.

### Carbon Intensity Trends

Ontario's grid carbon intensity is among the lowest in North America due to:
- Nuclear baseload (~60% of generation, zero emissions)
- Hydroelectric resources (~25%, zero emissions)
- Growing wind and solar capacity
- Complete coal phase-out (2014)

Typical CO₂ intensity: 20-40 g CO₂e/kWh (vs. 400-600 g/kWh for coal-heavy grids)

### Seasonal Patterns

- **Summer peaks**: Higher demand for cooling, more solar generation
- **Winter peaks**: Heating demand, lower solar output
- **Spring/Fall**: Lowest demand periods, maximum hydro generation from runoff

---

## Data Sources

- **Generation Data**: [IESO Generator Output by Fuel Type](https://www.ieso.ca/Power-Data/Data-Directory)
- **CO₂ Calculations**: [Gridwatch.ca](https://live.gridwatch.ca/) using IESO data + emission factors
- **Coverage**: 2010-present, hourly resolution
- **Update Frequency**: Nightly automated pipeline

For methodology details on carbon intensity calculations, see [Gridwatch.ca documentation](https://live.gridwatch.ca/).
