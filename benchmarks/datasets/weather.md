# weather.csv — Dataset Reference

1460 rows. One row per (date, city) pair — every calendar day in 2024
(2024-01-01 through 2024-12-30) crossed with all four cities. Each city
therefore has a complete, continuous 365-day time series.
Generated deterministically with `seed=2026`.

## Columns

| Column | Dtype | Example Values | Notes |
|---|---|---|---|
| `date` | string (ISO 8601) | "2024-01-01", "2024-07-04" | One per day. Parse with `pd.to_datetime()` for time-series queries. |
| `city` | string | Boston, Seattle, Miami, Phoenix | 4 cities, cycling by day index. Each city appears ~91–92 times. |
| `temp_high_f` | float | 30.4–112.5 | Seasonal baseline + Gaussian noise (σ=5°F). |
| `temp_low_f` | float | 11.4–92.8 | ~15–25°F below `temp_high_f` with additional noise. Can exceed high in edge noise cases (rare). |
| `precipitation_in` | float | 0.0–2.5 | ~23% of rows have non-zero precipitation. Zero means no measurable precip. |
| `wind_mph` | float | 0.1–30.0 | Right-skewed; most days are calm (0–10 mph). |
| `conditions` | string | Sunny, Cloudy, Rainy, Snowy, Foggy | Weighted by city + season. Snowy only realistic for Boston winter. Phoenix is mostly Sunny. |

## City Profiles

| City | Temp Range (high) | Dominant Conditions |
|---|---|---|
| Boston | 30–84°F | Snowy in winter, Sunny in summer |
| Seattle | 45–77°F | Rainy/Cloudy year-round, Sunny in summer |
| Miami | 76–92°F | Sunny with summer afternoon rain |
| Phoenix | 65–105°F | Mostly Sunny, monsoon rain in summer |

## Quirks

- `date` is a string, not a native date — needs parsing for temporal queries.
- Each city has exactly 365 rows (one per day); `(date, city)` is unique across all rows.
- `temp_low_f` is always ≤ `temp_high_f` by construction: `temp_low = temp_high - abs(gauss(20, 5))`.
- `precipitation_in` is exactly `0.0` (not null) on dry days.

## Sample Questions

1. What is the average high temperature per city by month? Show as a line chart.
2. Which city has the most rainy days?
3. Show the distribution of daily high temperatures for each city as a box plot.
4. How does precipitation vary across the four seasons in Seattle?
5. Plot wind speed vs. temperature for all cities, colored by conditions.
