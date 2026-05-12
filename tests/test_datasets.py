"""Sanity checks for benchmark datasets (CSVs only — no LLM calls)."""

from pathlib import Path

import pandas as pd
import pytest

_DATASETS = Path(__file__).parent.parent / "benchmarks" / "datasets"


# ---------------------------------------------------------------------------
# movies.csv
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def movies() -> pd.DataFrame:
    return pd.read_csv(_DATASETS / "movies.csv")


def test_movies_row_count(movies):
    assert len(movies) == 120


def test_movies_column_names(movies):
    expected = {"title", "genre", "release_year", "runtime_min",
                "imdb_rating", "box_office_usd", "studio", "is_sequel"}
    assert expected.issubset(set(movies.columns))


def test_movies_release_year_dtype(movies):
    assert pd.api.types.is_integer_dtype(movies["release_year"])


def test_movies_release_year_range(movies):
    assert movies["release_year"].min() >= 1990
    assert movies["release_year"].max() <= 2024


def test_movies_imdb_rating_range(movies):
    assert movies["imdb_rating"].min() >= 1.0
    assert movies["imdb_rating"].max() <= 9.5


def test_movies_box_office_null_rate(movies):
    null_rate = movies["box_office_usd"].isna().mean()
    assert 0.05 <= null_rate <= 0.15, (
        f"Expected box_office_usd null rate 5–15%, got {null_rate:.1%}"
    )


def test_movies_runtime_null_rate(movies):
    null_rate = movies["runtime_min"].isna().mean()
    assert null_rate <= 0.10, f"Expected runtime_min null rate ≤10%, got {null_rate:.1%}"


def test_movies_box_office_range(movies):
    bo = movies["box_office_usd"].dropna()
    assert bo.min() >= 100_000
    assert bo.max() <= 2_000_000_000


def test_movies_genre_values(movies):
    valid = {"Action", "Comedy", "Drama", "Horror", "Sci-Fi", "Documentary"}
    assert set(movies["genre"].unique()).issubset(valid)


def test_movies_studio_values(movies):
    valid = {"Universal", "Warner", "Disney", "A24", "Netflix", "Paramount", "Sony"}
    assert set(movies["studio"].unique()).issubset(valid)


def test_movies_titles_are_unique(movies):
    assert movies["title"].nunique() == len(movies)


def test_movies_titles_no_template_pattern(movies):
    """Catches the old 'The {Adj} {Noun}{suffix}' template — no more than
    a third of the first 30 titles should start with 'The '."""
    first30 = movies["title"].iloc[:30]
    starts_with_the = (first30.str.startswith("The ")).sum()
    assert starts_with_the <= 10, (
        f"{starts_with_the}/30 titles start with 'The ' — likely still using template"
    )


# ---------------------------------------------------------------------------
# weather.csv
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def weather() -> pd.DataFrame:
    df = pd.read_csv(_DATASETS / "weather.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_weather_row_count(weather):
    assert len(weather) == 1460


def test_weather_column_names(weather):
    expected = {"date", "city", "temp_high_f", "temp_low_f",
                "precipitation_in", "wind_mph", "conditions"}
    assert expected.issubset(set(weather.columns))


def test_weather_all_four_cities_present(weather):
    assert set(weather["city"].unique()) == {"Boston", "Seattle", "Miami", "Phoenix"}


def test_weather_each_city_has_365_rows(weather):
    counts = weather["city"].value_counts()
    assert (counts == 365).all(), f"Expected 365 rows per city, got: {counts.to_dict()}"


def test_weather_date_range(weather):
    assert weather["date"].min() == pd.Timestamp("2024-01-01")
    assert weather["date"].max() == pd.Timestamp("2024-12-30")


def test_weather_no_nulls(weather):
    assert weather.isnull().sum().sum() == 0


def test_weather_temp_high_range(weather):
    assert weather["temp_high_f"].min() >= 15.0
    assert weather["temp_high_f"].max() <= 120.0


def test_weather_temp_low_le_temp_high(weather):
    violations = (weather["temp_low_f"] > weather["temp_high_f"]).sum()
    assert violations == 0, f"{violations} rows have temp_low_f > temp_high_f"


def test_weather_date_city_unique(weather):
    pairs = weather[["date", "city"]]
    assert not pairs.duplicated().any(), "Found duplicate (date, city) pairs"


def test_weather_precipitation_non_negative(weather):
    assert (weather["precipitation_in"] >= 0).all()


def test_weather_precipitation_has_nonzero_rows(weather):
    assert (weather["precipitation_in"] > 0).sum() > 200


def test_weather_conditions_values(weather):
    valid = {"Sunny", "Cloudy", "Rainy", "Snowy", "Foggy"}
    assert set(weather["conditions"].unique()).issubset(valid)


def test_weather_wind_non_negative(weather):
    assert (weather["wind_mph"] >= 0).all()
