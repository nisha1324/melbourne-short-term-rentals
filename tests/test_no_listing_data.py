"""Inside Airbnb asks users not to republish its data: nothing committed may hold listing-level rows."""
from __future__ import annotations

import subprocess

import pandas as pd

from str_market import source

ID_COLUMNS = {"listing_id", "id", "host_id", "host_name", "latitude", "longitude", "listing_url"}


def committed_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=source.ROOT, capture_output=True, text=True, check=True).stdout
    return out.split()


def test_no_raw_or_database_files_are_committed():
    files = committed_files()
    assert not [f for f in files if f.startswith("data/raw/") or f.endswith((".duckdb", ".gz", ".parquet"))]
    assert [f for f in files if f.startswith("data/")] == ["data/SNAPSHOT.json"]


def test_result_tables_are_aggregates():
    for f in committed_files():
        if f.endswith(".csv"):
            df = pd.read_csv(source.ROOT / f)
            assert not ID_COLUMNS & set(df.columns), f
            assert len(df) <= 500, f"{f} has {len(df)} rows; results should be aggregates"
