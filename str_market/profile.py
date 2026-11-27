"""Part 1 profile: run the profile queries against the DuckDB database and return DataFrames."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from str_market import source

SQL_DIR = source.ROOT / "sql"

# Output name -> SQL file. Each runs after sql/active_listings.sql has created the `active` view.
QUERIES = {
    "market_size": "market_size.sql",
    "by_scrape_source": "by_scrape_source.sql",
    "by_room_type": "by_room_type.sql",
    "by_lga": "by_lga.sql",
    "price_bands": "price_bands.sql",
    "minimum_nights": "minimum_nights.sql",
    "host_size": "host_size.sql",
    "reviews_by_month": "reviews_by_month.sql",
    "quality_checks": "quality_checks.sql",
}


def connect(db_path: Path = source.DB_PATH) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(db_path), read_only=True)
    con.execute("SET enable_progress_bar = false")
    con.execute((SQL_DIR / "active_listings.sql").read_text())
    return con


def run_all(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    out = {name: con.execute((SQL_DIR / f).read_text()).df() for name, f in QUERIES.items()}
    qc = out["quality_checks"]
    qc["expected"] = qc["expected"].astype("Int64")
    qc["status"] = ["info" if pd.isna(e) else ("pass" if f == e else "note")
                    for f, e in zip(qc["found"], qc["expected"])]
    return out


def column_profile(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Share of empty values per kept listings column, for all and for active listings."""
    cols = [r[0] for r in con.execute("DESCRIBE listings").fetchall()]
    rows = []
    for c in cols:
        n_all, null_all, distinct = con.execute(
            f'SELECT count(*), count(*) - count("{c}"), count(DISTINCT "{c}") FROM listings').fetchone()
        n_act, null_act = con.execute(f'SELECT count(*), count(*) - count("{c}") FROM active').fetchone()
        rows.append({"column": c, "distinct_values": distinct,
                     "empty_pct_all": round(100 * null_all / n_all, 1),
                     "empty_pct_active": round(100 * null_act / n_act, 1)})
    return pd.DataFrame(rows)


def headline(con: duckdb.DuckDBPyConnection) -> dict:
    """Single figures quoted in the report and README."""
    q = lambda s: con.execute(s).fetchone()  # noqa: E731
    snap_min, snap_max = q("SELECT min(last_scraped), max(last_scraped) FROM listings")
    cal_min, cal_max = q("SELECT min(date), max(date) FROM calendar")
    rev_min, rev_max, rev_n = q("SELECT min(date), max(date), count(*) FROM reviews")
    act_n, act_hosts = q("SELECT count(*), count(DISTINCT host_id) FROM active")
    entire = q("SELECT count(*) FROM active WHERE room_type = 'Entire home/apt'")[0]
    multi = q("""SELECT coalesce(sum(n) FILTER (WHERE n >= 2), 0), coalesce(sum(n) FILTER (WHERE n >= 10), 0),
                        count(*) FILTER (WHERE n >= 10)
                 FROM (SELECT host_id, count(*) n FROM active GROUP BY host_id)""")
    top_lga = q("SELECT lga, count(*) FROM active GROUP BY lga ORDER BY 2 DESC LIMIT 1")
    inner3 = q("SELECT count(*) FROM active WHERE lga IN ('Melbourne', 'Port Phillip', 'Yarra')")[0]
    min28 = q("SELECT count(*) FROM active WHERE minimum_nights >= 28")[0]
    open_entire = q("""SELECT count(*), count(*) FILTER (WHERE availability_365 >= 180)
                       FROM active WHERE room_type = 'Entire home/apt'""")
    carried = q("""SELECT count(*), count(*) FILTER (WHERE availability_365 = 0)
                   FROM listings WHERE scrape_source = 'previous scrape'""")
    price_ent = q("""SELECT median(price), count(price) FROM active WHERE room_type = 'Entire home/apt'""")
    price_pr = q("""SELECT median(price), count(price) FROM active WHERE room_type = 'Private room'""")
    covid = q("""SELECT
          (SELECT count(*) FROM reviews WHERE date >= DATE '2019-01-01' AND date < DATE '2020-01-01'),
          (SELECT count(*) FROM reviews WHERE date >= DATE '2020-04-01' AND date < DATE '2021-04-01'),
          (SELECT count(*) FROM reviews WHERE date >= DATE '2025-09-01' AND date < DATE '2026-09-01')""")
    quote = q("""WITH f AS (SELECT listing_id, min(date) AS first_open FROM calendar WHERE available GROUP BY 1)
                 SELECT count(*),
                        count(*) FILTER (WHERE date_diff('day', quote_checkin, quote_checkout) = minimum_nights),
                        count(*) FILTER (WHERE date_diff('day', quote_checkin, quote_checkout) < minimum_nights),
                        count(*) FILTER (WHERE quote_checkin = first_open)
                 FROM listings LEFT JOIN f USING (listing_id) WHERE price IS NOT NULL""")
    inactive = q("""SELECT count(*) FILTER (WHERE scrape_source = 'previous scrape'),
                           count(*) FILTER (WHERE scrape_source = 'city scrape')
                    FROM listings WHERE number_of_reviews_ltm = 0""")
    return {
        "quotes": quote[0], "quotes_for_minimum_stay": quote[1], "quotes_shorter_than_minimum": quote[2],
        "quotes_from_first_open_night": quote[3],
        "inactive_carried_over": inactive[0], "inactive_found": inactive[1],
        "listings": q("SELECT count(*) FROM listings")[0],
        "hosts": q("SELECT count(DISTINCT host_id) FROM listings")[0],
        "scraped": (str(snap_min), str(snap_max)),
        "calendar": (str(cal_min), str(cal_max)),
        "reviews": (str(rev_min), str(rev_max), rev_n),
        "active": act_n, "active_hosts": act_hosts,
        "active_entire": entire,
        "active_multi_host_listings": int(multi[0]), "active_10plus_listings": int(multi[1]),
        "hosts_10plus": int(multi[2]),
        "top_lga": (top_lga[0], top_lga[1]), "inner3": inner3,
        "min28": min28,
        "entire_open_180": (open_entire[0], open_entire[1]),
        "carried_over": (carried[0], carried[1]),
        "median_price_entire": (float(price_ent[0]), price_ent[1]),
        "median_price_private": (float(price_pr[0]), price_pr[1]),
        "reviews_2019": covid[0], "reviews_apr20_mar21": covid[1], "reviews_sep25_aug26": covid[2],
    }
