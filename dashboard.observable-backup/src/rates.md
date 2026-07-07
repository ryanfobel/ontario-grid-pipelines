# Ontario Electricity Rates (OEB)

```js
const db = await DuckDBClient.of({
  rates: FileAttachment("data/stg_oeb_rates.parquet"),
});
```

```js
const tou = await db.query(`
  SELECT effective_date, rate_column, value_cents_per_kwh
  FROM rates
  WHERE rate_type = 'Time-of-Use Prices'
  ORDER BY effective_date DESC
  LIMIT 60
`);
```

```js
Plot.plot({
  title: "Time-of-Use prices over time (¢/kWh)",
  width,
  height: 280,
  x: {type: "utc", label: null},
  y: {label: "¢/kWh", grid: true},
  color: {legend: true},
  marks: [
    Plot.lineY(tou, {
      x: "effective_date",
      y: "value_cents_per_kwh",
      stroke: "rate_column",
      tip: true,
    }),
  ],
})
```
