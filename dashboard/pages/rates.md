# Ontario Electricity Rates

Ontario has three residential electricity pricing structures regulated by the Ontario Energy Board (OEB).

```sql tou
SELECT * FROM ontario_grid.tou
```

```sql tiered
SELECT * FROM ontario_grid.tiered_rates
```

```sql ulo
SELECT * FROM ontario_grid.ulo_rates
```

```sql current_rates
SELECT * FROM ontario_grid.current_rates
```

## Time-of-Use (TOU) Prices

Most residential customers pay Time-of-Use rates with three pricing periods:

<LineChart
    data={tou}
    x=effective_date
    y=value_cents_per_kwh
    series=rate_column
    title='Time-of-Use Price History (¢/kWh)'
    yAxisTitle='¢/kWh'
    chartAreaHeight=300
/>

### Current TOU Rates

<DataTable data={current_rates}/>

**Pricing Periods:**
- **Off-Peak**: Weekends, holidays, weekday evenings/nights (lowest rate)
- **Mid-Peak**: Weekday shoulder hours
- **On-Peak**: Weekday afternoons/early evening (highest rate)

## Tiered Rates

Alternative pricing for customers who prefer predictable costs regardless of time-of-day:

<LineChart
    data={tiered}
    x=effective_date
    y=value_cents_per_kwh
    series=rate_column
    title='Tiered Rate History (¢/kWh)'
    yAxisTitle='¢/kWh'
    chartAreaHeight=300
/>

**How it works:**
- **Tier 1**: Lower rate for first ~1000 kWh/month (residential) or ~750 kWh/month (non-residential)
- **Tier 2**: Higher rate for consumption above threshold

## Ultra-Low Overnight (ULO) Rates

Newest pricing structure with four periods, incentivizing overnight EV charging:

<LineChart
    data={ulo}
    x=effective_date
    y=value_cents_per_kwh
    series=rate_column
    title='Ultra-Low Overnight Rate History (¢/kWh)'
    yAxisTitle='¢/kWh'
    chartAreaHeight=300
/>

**Pricing Periods:**
- **Ultra-Low Overnight**: 11pm-7am every day (lowest rate - typically 40% less than off-peak)
- **Weekend Off-Peak**: Weekends and holidays 7am-11pm
- **Mid-Peak**: Weekdays 7am-4pm and 9pm-11pm
- **On-Peak**: Weekdays 4pm-9pm

ULO rates launched in May 2023 to support electric vehicle adoption and reduce grid strain.

---

## About Ontario Electricity Rates

**Source**: [Ontario Energy Board (OEB)](https://www.oeb.ca/consumer-information-and-protection/electricity-rates)

**Regulation**: The OEB sets electricity prices for residential and small business customers based on:
- Wholesale electricity market costs
- Transmission and distribution costs
- Conservation and demand management programs
- Global adjustment (difference between market price and contracted/regulated rates)

**Rate Adjustments**: Rates are reviewed quarterly (May 1 and November 1) and adjusted based on market forecasts.

**Coverage**: Historical data from 2010-present showing evolution of Ontario's electricity pricing structures.

**How to Choose**:
- **TOU**: Best for customers who can shift usage to off-peak times
- **Tiered**: Best for predictable bills regardless of timing
- **ULO**: Best for EV owners who charge overnight or those with flexible overnight loads
