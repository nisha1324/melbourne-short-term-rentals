"""Part 3 host concentration: who runs the active market, council by council.

A host's size is its number of active listings across all 30 councils; operators
are hosts with 10 or more. Only aggregates leave this module: the per-host view
(`hosts`) is never written to results/.
"""
from __future__ import annotations

import duckdb
import pandas as pd

from str_market import pricing, profile

SQL_DIR = profile.SQL_DIR

QUERIES = {
    "concentration_summary": "concentration_summary.sql",
    "largest_hosts": "largest_hosts.sql",
    "host_curve": "host_curve.sql",
    "council_hosts": "council_hosts.sql",
    "host_size_profile": "host_size_profile.sql",
    "operator_spread": "operator_spread.sql",
    "typical_operator": "typical_operator.sql",
    "host_count_check": "host_count_check.sql",
}


def prepare(con: duckdb.DuckDBPyConnection, **pricing_thresholds) -> None:
    """Create Part 2's `priced_homes` view, then the `host_listings` and `hosts` views (needs `active`)."""
    pricing.prepare(con, **pricing_thresholds)
    con.execute((SQL_DIR / "host_listings.sql").read_text())


def run_all(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    return {name: con.execute((SQL_DIR / f).read_text()).df() for name, f in QUERIES.items()}
