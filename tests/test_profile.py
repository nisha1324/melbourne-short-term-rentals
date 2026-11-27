"""The build and every Part 1 query on the hand-made snapshot in conftest.py (expected values worked by hand)."""
from __future__ import annotations

import datetime as dt

import shutil

import duckdb
import pandas as pd

from str_market import profile


def rows(df: pd.DataFrame, *cols: str) -> list[tuple]:
    return [tuple(r) for r in df[list(cols)].itertuples(index=False)]


def test_build_drops_personal_and_free_text_columns(con):
    cols = {r[0] for r in con.execute("DESCRIBE listings").fetchall()}
    assert {"host_name", "description", "listing_url"}.isdisjoint(cols)
    assert {"listing_id", "host_id", "lga", "price"} <= cols


def test_build_parses_price_and_marks_carried_over(con):
    got = con.execute("SELECT listing_id, price, scrape_source FROM listings ORDER BY listing_id").fetchall()
    assert got == [(1, 300.0, "city scrape"), (2, 100.0, "city scrape"), (3, 2500.0, "city scrape"),
                   (4, None, "previous scrape"), (5, 200.0, "city scrape"), (6, 400.0, "city scrape")]


def test_active_view_uses_the_inclusive_12_month_window(con):
    # listing 2's only review is on 2025-09-18, exactly 365 days before the scrape: it counts
    assert [r[0] for r in con.execute("SELECT listing_id FROM active ORDER BY 1").fetchall()] == [1, 2, 3, 6]


def test_market_size(results):
    assert rows(results["market_size"], "listings", "hosts") == [(6, 4), (5, 3), (5, 3), (4, 3), (4, 2), (4, 2)]


def test_by_scrape_source(results):
    d = results["by_scrape_source"].set_index("scrape_source")
    assert tuple(d.loc["city scrape", ["listings", "with_price", "no_open_nights", "reviewed_last_12m",
                                        "never_reviewed"]]) == (5, 5, 1, 4, 1)
    assert tuple(d.loc["previous scrape", ["listings", "with_price", "no_open_nights", "reviewed_last_12m",
                                            "never_reviewed"]]) == (1, 0, 1, 0, 0)
    assert pd.Timestamp(d.loc["previous scrape", "median_last_review"]) == pd.Timestamp("2023-03-05")


def test_by_room_type(results):
    d = results["by_room_type"].set_index("room_type")
    # entire homes 1, 3, 6: prices 300, 2,500, 400 -> quartiles 350 / 400 / 1,450
    assert tuple(d.loc["Entire home/apt", ["active_listings", "share_pct", "with_price", "price_p25",
                                           "price_median", "price_p75"]]) == (3, 75.0, 3, 350, 400, 1450)
    assert tuple(d.loc["Private room", ["active_listings", "share_pct", "price_median"]]) == (1, 25.0, 100)


def test_by_lga(results):
    got = rows(results["by_lga"], "lga", "active_listings", "entire_homes", "entire_home_pct",
               "entire_home_median_price", "share_of_market_pct")
    assert got == [("Alpha", 2, 1, 50.0, 300, 50.0), ("Beta", 1, 1, 100.0, 2500, 25.0),
                   ("Gamma", 1, 1, 100.0, 400, 25.0)]


def test_price_bands(results):
    got = rows(results["price_bands"], "room_type", "price_band", "listings", "share_pct")
    assert got == [("Entire home/apt", "$300-499", 2, 66.7), ("Entire home/apt", "$2,000+", 1, 33.3),
                   ("Private room", "$100-149", 1, 100.0)]


def test_minimum_nights(results):
    got = rows(results["minimum_nights"], "minimum_stay", "active_listings", "entire_homes")
    assert got == [("1 night", 1, 0), ("2 nights", 2, 2), ("28+ nights", 1, 1)]


def test_host_size_counts_active_listings_only(results):
    # host 20 has listings 3 and 6 (both active); host 10 has 1 and 2 (both active); 30 and 40 are not active
    assert rows(results["host_size"], "host_size", "hosts", "active_listings", "share_of_listings_pct") == \
        [("2-4 listings", 2, 4, 100.0)]


def test_quality_checks_find_exactly_the_planted_problems(results):
    qc = results["quality_checks"].set_index("check_no")
    found = qc["found"].to_dict()
    planted = {3: 1, 9: 1, 10: 1, 17: 1, 19: 1}   # Delta empty; 366-day calendar; listing 2; listing 4; $2,500
    assert found == {k: planted.get(k, 0) for k in range(1, 21)}
    assert qc.loc[3, "status"] == "note" and qc.loc[1, "status"] == "pass" and qc.loc[17, "status"] == "info"


def test_review_reconciliation_catches_a_wrong_count(fixture_db, tmp_path):
    db = tmp_path / "copy.duckdb"
    shutil.copy(fixture_db, db)
    w = duckdb.connect(str(db))
    w.execute("UPDATE listings SET number_of_reviews_ltm = 3 WHERE listing_id = 1")
    w.execute("UPDATE listings SET last_review = DATE '2026-09-02' WHERE listing_id = 6")
    w.close()
    c = profile.connect(db)
    qc = profile.run_all(c)["quality_checks"].set_index("check_no")["found"]
    c.close()
    assert qc[14] == 1 and qc[13] == 1


def test_headline(con):
    h = profile.headline(con)
    assert h["listings"] == 6 and h["hosts"] == 4 and h["active"] == 4 and h["active_hosts"] == 2
    assert h["active_entire"] == 3
    assert (h["active_multi_host_listings"], h["active_10plus_listings"], h["hosts_10plus"]) == (4, 0, 0)
    assert h["carried_over"] == (1, 1)
    assert (h["inactive_carried_over"], h["inactive_found"]) == (1, 1)
    # quotes: 1, 2, 3, 5, 6; listing 6 quotes 3 nights against a 2-night minimum and starts after its first open night
    assert (h["quotes"], h["quotes_for_minimum_stay"], h["quotes_shorter_than_minimum"],
            h["quotes_from_first_open_night"]) == (5, 4, 0, 4)
    assert h["median_price_entire"] == (400.0, 3)
    assert h["scraped"] == ("2026-09-18", "2026-09-18")
    assert h["reviews"] == ("2023-03-05", "2026-09-01", 8)
    assert dt.date.fromisoformat(h["calendar"][1]) == dt.date(2027, 9, 18)   # listing 4's 366th day
