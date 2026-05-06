"""CSV loading and dataset context construction."""

from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    sample_values: list[str]
    n_unique: int
    n_null: int


class DatasetContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    df: pd.DataFrame = Field(exclude=True)
    column_schema: list[ColumnInfo]
    row_count: int


def build_dataset_context(csv_path: Path) -> DatasetContext:
    df = pd.read_csv(csv_path, nrows=10000)
    columns: list[ColumnInfo] = []
    for col in df.columns:
        series = df[col]
        unique_nonnull = series.dropna().unique()
        columns.append(
            ColumnInfo(
                name=col,
                dtype=str(series.dtype),
                sample_values=[str(v) for v in unique_nonnull[:3]],
                n_unique=int(series.nunique()),
                n_null=int(series.isna().sum()),
            )
        )
    return DatasetContext(
        name=csv_path.stem,
        df=df,
        column_schema=columns,
        row_count=len(df),
    )
