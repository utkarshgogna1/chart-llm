# movies.csv — Dataset Reference

120 rows. One row per movie. Covers 1990–2024 across six genres and seven studios.
Generated deterministically with `seed=2026`.

## Columns

| Column | Dtype | Example Values | Notes |
|---|---|---|---|
| `title` | string | "The Dark Night", "The Iron World II" | Unique. Format: "The {Adj} {Noun}{optional suffix}". No true apostrophes/quotes in this seed's output. |
| `genre` | string | Action, Comedy, Drama, Horror, Sci-Fi, Documentary | 6 categories. Sci-Fi and Documentary are slightly over-represented (~28% and ~21%) due to RNG. |
| `release_year` | int | 1990–2024 | Uniform draw. |
| `runtime_min` | int | 71–199 | ~3% nulls (4 rows). Null means runtime not reported. |
| `imdb_rating` | float | 1.1–9.5 | 1 decimal place. Uniform, not bell-curved. |
| `box_office_usd` | float | 275,427 – 2,000,000,000 | **10% nulls** (12 rows). Log-normal distribution; most films cluster in the low millions, a few hit the $2B cap. |
| `studio` | string | Universal, Warner, Disney, A24, Netflix, Paramount, Sony | 7 categories. Disney and Paramount are slightly over-represented. |
| `is_sequel` | bool | True, False | ~30% True (36/120). |

## Quirks

- `box_office_usd` and `runtime_min` have real NULL values (empty CSV cells). Queries involving these columns should handle missing data.
- `genre` is **case-sensitive** as written (e.g., "Sci-Fi" not "sci-fi").
- IMDB ratings are uniformly distributed 1.1–9.5, not normally distributed — do not assume a bell curve.
- `is_sequel` is stored as Python bool (`True`/`False`), which pandas reads as object dtype unless coerced.

## Sample Questions

1. Which studio has the highest average box office revenue?
2. How does average IMDB rating vary by genre? Show as a bar chart.
3. Plot the distribution of runtime across all movies as a histogram.
4. Show box office revenue vs. IMDB rating as a scatter plot, colored by genre.
5. How many sequels vs. non-sequels are there per studio?
