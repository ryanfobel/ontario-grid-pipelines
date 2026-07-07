# Ontario Electricity Rates (OEB)

```sql tou
SELECT * FROM ontario_grid.tou
```

```sql current_rates
SELECT * FROM ontario_grid.current_rates
```

<LineChart
    data={tou}
    x=effective_date
    y=value_cents_per_kwh
    series=rate_column
    title='Time-of-Use Prices Over Time (¢/kWh)'
    yAxisTitle='¢/kWh'
    chartAreaHeight=280
/>

## Current Rates

<DataTable data={current_rates}/>

---

*Data source: Ontario Energy Board (OEB). Rates updated when changed.*
