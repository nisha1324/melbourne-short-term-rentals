"""Part 2 pricing: compare each active entire home's quoted price with similar listings.

A listing's peers are the active entire homes in the same council with the same
number of bedrooms (5 or more grouped). Its price is compared with the peer
group's median; groups smaller than MIN_PEERS are not scored.
"""
from __future__ import annotations

import duckdb
import pandas as pd

from str_market import profile

SQL_DIR = profile.SQL_DIR
MIN_PEERS = 10              # smallest peer group (council x bedrooms) whose listings are scored
MIN_COUNCIL_LISTINGS = 30   # smallest council (priced entire homes) shown in the council table

QUERIES = {
    "price_by_size": "price_by_size.sql",
    "price_by_guests": "price_by_guests.sql",
    "price_by_council": "price_by_council.sql",
    "price_by_stay_length": "price_by_stay_length.sql",
    "price_by_stay_dates": "price_by_stay_dates.sql",
    "price_by_lead_time": "price_by_lead_time.sql",
    "price_vs_peers": "price_vs_peers.sql",
    "peer_price_guide": "peer_price_guide.sql",
    "weekend_open": "weekend_open.sql",
}


def prepare(con: duckdb.DuckDBPyConnection, min_peers: int = MIN_PEERS,
            min_council_listings: int = MIN_COUNCIL_LISTINGS) -> None:
    """Set the thresholds and create the `priced_homes` view (needs the `active` view)."""
    con.execute(f"SET VARIABLE min_peers = {int(min_peers)}")
    con.execute(f"SET VARIABLE min_council_listings = {int(min_council_listings)}")
    con.execute((SQL_DIR / "priced_homes.sql").read_text())


def run_all(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    return {name: con.execute((SQL_DIR / f).read_text()).df() for name, f in QUERIES.items()}


def headline(con: duckdb.DuckDBPyConnection) -> dict:
    """Single figures quoted in the Part 2 report and README."""
    q = lambda s: con.execute(s).fetchone()  # noqa: E731
    entire, entire_priced = q("""SELECT count(*), count(price) FROM active WHERE room_type = 'Entire home/apt'""")
    homes, scored, median_price, small = q("""SELECT count(*), count(ratio), median(price),
                                                     100.0 * count(*) FILTER (WHERE bed_band <= 1) / count(*)
                                              FROM priced_homes""")
    groups, groups_scored = q("""SELECT count(*), count(*) FILTER (WHERE peer_n >= getvariable('min_peers'))
                                 FROM (SELECT DISTINCT lga, bed_band, peer_n FROM priced_homes)""")
    short_stays = q("""SELECT count(*) FROM priced_homes
                       WHERE ratio IS NOT NULL AND stay_nights BETWEEN 1 AND 3 AND lead_days < 60""")[0]
    return {
        "active": q("SELECT count(*) FROM active")[0], "entire": entire, "entire_priced": entire_priced, "homes": homes, "no_bedrooms": entire_priced - homes,
        "scored": scored, "median_price": float(median_price), "small_pct": float(small),
        "groups": groups, "groups_scored": groups_scored,
        "short_stays": short_stays,
    }
