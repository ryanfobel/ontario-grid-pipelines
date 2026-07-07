# Ontario Grid — Generation & Emissions

```js
import * as duckdb from "npm:@duckdb/duckdb-wasm";
import {DuckDBClient} from "npm:@observablehq/duckdb";
```

```js
const db = await DuckDBClient.of({
  generation: FileAttachment("data/fct_grid_generation.parquet"),
  co2: FileAttachment("data/fct_co2_intensity.parquet"),
});
```

```js
const generation = await db.query(`
  SELECT
    hour,
    nuclear_mw, hydro_mw, wind_mw, solar_mw, biofuel_mw, gas_mw,
    total_mw, clean_pct
  FROM generation
  ORDER BY hour DESC
  LIMIT 8760
`);
```

```js
const latest = await db.queryRow(`
  SELECT hour, total_mw, clean_pct, co2e_intensity_gco2_per_kwh
  FROM co2
  ORDER BY hour DESC
  LIMIT 1
`);
```

## Current snapshot

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Clean energy</h2>
    <span class="big">${latest ? latest.clean_pct?.toFixed(1) + "%" : "—"}</span>
    <p>of total generation</p>
  </div>
  <div class="card">
    <h2>Total output</h2>
    <span class="big">${latest ? (latest.total_mw / 1000).toFixed(1) + " GW" : "—"}</span>
  </div>
  <div class="card">
    <h2>CO₂ intensity</h2>
    <span class="big">${latest ? latest.co2e_intensity_gco2_per_kwh?.toFixed(0) + " g/kWh" : "—"}</span>
    <p>from gridwatch</p>
  </div>
  <div class="card">
    <h2>As of</h2>
    <span class="big">${latest ? new Date(latest.hour).toLocaleDateString("en-CA") : "—"}</span>
  </div>
</div>

## Generation mix (last 30 days)

```js
const monthly = await db.query(`
  SELECT
    hour::date as day,
    avg(nuclear_mw) as nuclear,
    avg(hydro_mw)   as hydro,
    avg(wind_mw)    as wind,
    avg(solar_mw)   as solar,
    avg(biofuel_mw) as biofuel,
    avg(gas_mw)     as gas
  FROM generation
  WHERE hour >= current_date - INTERVAL 30 DAY
  GROUP BY 1
  ORDER BY 1
`);
```

```js
Plot.plot({
  title: "Daily average generation by fuel type (MW)",
  width,
  height: 300,
  x: {type: "utc", label: null},
  y: {label: "MW", grid: true},
  color: {
    domain: ["nuclear", "hydro", "wind", "solar", "biofuel", "gas"],
    range: ["#7B68EE", "#4FC3F7", "#81C784", "#FFF176", "#A5D6A7", "#EF9A9A"],
    legend: true,
  },
  marks: [
    Plot.areaY(monthly, {x: "day", y: "nuclear",  fill: "#7B68EE", tip: true}),
    Plot.areaY(monthly, {x: "day", y: "hydro",    fill: "#4FC3F7", tip: true}),
    Plot.areaY(monthly, {x: "day", y: "wind",     fill: "#81C784", tip: true}),
    Plot.areaY(monthly, {x: "day", y: "solar",    fill: "#FFF176", tip: true}),
    Plot.areaY(monthly, {x: "day", y: "biofuel",  fill: "#A5D6A7", tip: true}),
    Plot.areaY(monthly, {x: "day", y: "gas",      fill: "#EF9A9A", tip: true}),
  ],
})
```

## CO₂ intensity (last 30 days)

```js
const co2trend = await db.query(`
  SELECT hour, co2e_intensity_gco2_per_kwh as co2
  FROM co2
  WHERE hour >= current_date - INTERVAL 30 DAY
    AND co2e_intensity_gco2_per_kwh IS NOT NULL
  ORDER BY hour
`);
```

```js
Plot.plot({
  title: "CO₂ intensity (g CO₂e / kWh)",
  width,
  height: 200,
  x: {type: "utc", label: null},
  y: {label: "g/kWh", grid: true},
  marks: [
    Plot.lineY(co2trend, {x: "hour", y: "co2", stroke: "#EF9A9A", tip: true}),
    Plot.ruleY([50], {stroke: "#81C784", strokeDasharray: "4,4"}),
  ],
})
```
