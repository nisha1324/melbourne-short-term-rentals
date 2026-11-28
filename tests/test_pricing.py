"""Part 2 pricing queries on a second hand-made snapshot (expected values worked out by hand).

All listings scraped on Friday 2026-09-18 and reviewed in the last 12 months unless noted.
Thresholds for this fixture: min_peers = 3, min_council_listings = 2.

id council room          beds guests price  quote (nights, night of week)   open nights from (count)
1  Alpha   Entire home   1    2      $200   18-20 Sep (2, Fri+Sat)           18 Sep (5)
2  Alpha   Entire home   1    2      $100   21-22 Sep (1, Mon)               21 Sep (3)
3  Alpha   Entire home   1    4      $300   25-26 Sep (1, Fri 25 = GF eve)   25 Sep (40)
4  Alpha   Entire home   2    4      $400   20 Sep-18 Oct (28)               20 Sep (28)
5  Alpha   Entire home   2    4      $500   22-29 Sep (7, covers 25 + 26)    22 Sep (10)
6  Alpha   Entire home   2    6      $600   27-28 Sep (1, Sun)               27 Sep (2)
7  Beta    Entire home   1    2      $150   18-19 Sep (1, Fri)               18 Sep (1)
8  Beta    Entire home   3    6      $900   1-3 Dec (2, Tue+Wed)             1 Dec (2)
9  Beta    Private room  1    2      $80    (excluded: not an entire home)
10 Beta    Entire home   1    2      (none) (excluded: no price)
11 Beta    Entire home   -    2      $250   (excluded: no bedroom count)
12 Beta    Entire home   1    2      $999   (excluded: no review in 12 months, so not active)

Peer groups: Alpha 1-bed {1, 2, 3} median 200 -> ratios 1.0, 0.5, 1.5; Alpha 2-bed {4, 5, 6}
median 500 -> 0.8, 1.0, 1.2; Beta 1-bed {7} and Beta 3-bed {8} are below min_peers: not scored.
"""
from __future__ import annotations

import pandas as pd
import pytest

from str_market import build, pricing, profile

from conftest import write_fixture


def _listing(i, lga, room, price, qin=None, qout=None, nights=None, ltm=5):
    p = f"${price:,.2f}" if price else ""
    return (i, 100 + i, "", lga, room, p, qin or "", qout or "", price * nights if price and nights else "",
            price or "", 1, 100, ltm, ltm, "2026-01-01" if ltm else "2024-01-01",
            "2026-09-01" if ltm else "2024-01-01")


E, R = "Entire home/apt", "Private room"
LISTINGS = [
    _listing(1, "Alpha", E, 200, "2026-09-18", "2026-09-20", 2, ltm=10),
    _listing(2, "Alpha", E, 100, "2026-09-21", "2026-09-22", 1, ltm=20),
    _listing(3, "Alpha", E, 300, "2026-09-25", "2026-09-26", 1, ltm=4),
    _listing(4, "Alpha", E, 400, "2026-09-20", "2026-10-18", 28, ltm=2),
    _listing(5, "Alpha", E, 500, "2026-09-22", "2026-09-29", 7, ltm=6),
    _listing(6, "Alpha", E, 600, "2026-09-27", "2026-09-28", 1, ltm=8),
    _listing(7, "Beta", E, 150, "2026-09-18", "2026-09-19", 1, ltm=12),
    _listing(8, "Beta", E, 900, "2026-12-01", "2026-12-03", 2, ltm=3),
    _listing(9, "Beta", R, 80, "2026-09-18", "2026-09-19", 1),
    _listing(10, "Beta", E, None),
    _listing(11, "Beta", E, 250, "2026-09-18", "2026-09-19", 1),
    _listing(12, "Beta", E, 999, "2026-09-18", "2026-09-19", 1, ltm=0),
]
SIZES = {1: (2, 1), 2: (2, 1), 3: (4, 1), 4: (4, 2), 5: (4, 2), 6: (6, 2), 7: (2, 1), 8: (6, 3), 11: (2, "")}
CALENDAR = {1: (365, "2026-09-18", 5), 2: (365, "2026-09-21", 3), 3: (365, "2026-09-25", 40),
            4: (365, "2026-09-20", 28), 5: (365, "2026-09-22", 10), 6: (365, "2026-09-27", 2),
            7: (365, "2026-09-18", 1), 8: (365, "2026-12-01", 2), 9: (365, None, 0), 10: (365, None, 0),
            11: (365, None, 0), 12: (365, None, 0)}


@pytest.fixture(scope="module")
def pcon(tmp_path_factory):
    root = tmp_path_factory.mktemp("pricing")
    write_fixture(root / "raw", listings=LISTINGS, calendar=CALENDAR, reviews={},
                  host_counts={100 + i: 1 for i in range(1, 13)}, sizes=SIZES)
    db = root / "pricing.duckdb"
    build.build(raw_dir=root / "raw", db_path=db)
    c = profile.connect(db)
    pricing.prepare(c, min_peers=3, min_council_listings=2)
    yield c
    c.close()


@pytest.fixture(scope="module")
def out(pcon):
    return pricing.run_all(pcon)


def rows(df: pd.DataFrame, *cols: str) -> list[tuple]:
    return [tuple(None if pd.isna(v) else v for v in r) for r in df[list(cols)].itertuples(index=False)]


def test_priced_homes_keeps_active_priced_entire_homes_with_bedrooms(pcon):
    got = pcon.execute("""SELECT listing_id, bed_band, peer_n, round(ratio, 4), stay_nights, lead_days,
                                 open_30, open_90, gf_weekend, has_weekend
                          FROM priced_homes ORDER BY listing_id""").fetchall()
    assert got == [
        (1, 1, 3, 1.0, 2, 0, 5, 5, False, True),
        (2, 1, 3, 0.5, 1, 3, 3, 3, False, False),
        (3, 1, 3, 1.5, 1, 7, 23, 40, True, True),        # open 25 Sep - 3 Nov; 23 of them before 18 Oct
        (4, 2, 3, 0.8, 28, 2, 28, 28, True, True),       # a 28-night stay still gets its nights checked
        (5, 2, 3, 1.0, 7, 4, 10, 10, True, True),
        (6, 2, 3, 1.2, 1, 9, 2, 2, False, False),
        (7, 1, 1, None, 1, 0, 1, 1, False, True),        # alone in its peer group: not scored
        (8, 3, 1, None, 2, 74, 0, 2, False, False),      # 1-2 Dec fall inside 90 days, not 30
    ]


def test_headline(pcon):
    h = pricing.headline(pcon)
    assert h == {"active": 11, "entire": 10, "entire_priced": 9, "homes": 8, "no_bedrooms": 1, "scored": 6,
                 "median_price": 350.0, "small_pct": 50.0, "groups": 4, "groups_scored": 2, "short_stays": 4}


def test_price_by_size(out):
    # 1-bed: 200, 100, 300, 150 -> median 175, quartiles 137.5 / 225; per guest 100, 50, 75, 75 -> 75
    assert rows(out["price_by_size"], "size", "listings", "price_p25", "price_median", "price_p75", "median_guests",
                "per_guest_median") == [("1 bedroom", 4, 138, 175, 225, 2.0, 75),
                                        ("2 bedrooms", 3, 450, 500, 550, 4.0, 100),
                                        ("3 bedrooms", 1, 900, 900, 900, 6.0, 150)]


def test_price_by_guests(out):
    assert rows(out["price_by_guests"], "guests", "listings", "price_median", "per_guest_median") == [
        ("1-2 guests", 3, 150, 75), ("3-4 guests", 3, 400, 100), ("5-6 guests", 2, 750, 125)]


def test_price_by_council_allows_for_size(out):
    # market median 350; size medians 175 / 500 / 900.
    # Alpha: median 350 (0%); ratios .571 .8 1 1.143 1.2 1.714 -> 1.0714 (+7.1%); 3 of 6 are 1-bed.
    # Beta: 150 and 900 -> median 525 (+50%); ratios .857 and 1 -> .9286 (-7.1%).
    assert rows(out["price_by_council"], "lga", "listings", "price_median", "studio_or_1bed_pct",
                "raw_vs_market_pct", "same_size_vs_market_pct", "raw_rank", "same_size_rank",
                "two_bed_listings", "two_bed_median") == [
        ("Alpha", 6, 350, 50.0, 0.0, 7.1, 2, 1, 3, 500),
        ("Beta", 2, 525, 50.0, 50.0, -7.1, 1, 2, 0, None)]


def test_price_by_council_drops_small_councils(pcon):
    pricing.prepare(pcon, min_peers=3, min_council_listings=3)
    try:
        assert list(pricing.run_all(pcon)["price_by_council"]["lga"]) == ["Alpha"]
    finally:
        pricing.prepare(pcon, min_peers=3, min_council_listings=2)


def test_price_by_stay_length(out):
    # scored only: 1 night = 2, 3, 6 (ratios .5, 1.5, 1.2); 2 nights = 1; 7-27 = 5; 28+ = 4
    assert rows(out["price_by_stay_length"], "quoted_stay", "listings", "price_median", "vs_peers_pct") == [
        ("1 night", 3, 300, 20.0), ("2 nights", 1, 200, 0.0), ("7-27 nights", 1, 500, 0.0),
        ("28+ nights", 1, 400, -20.0)]


def test_price_by_stay_dates(out):
    # 1-3 night stays within 60 days: 3 covers Fri 25 Sep; 1 covers Fri 18 + Sat 19; 2 (Mon) and 6 (Sun) weekdays.
    # 5 covers 25-26 Sep too but is a 7-night stay, so it is not in this table.
    assert rows(out["price_by_stay_dates"], "band", "listings", "price_median", "vs_peers_pct") == [
        (1, 1, 300, 50.0), (2, 1, 200, 0.0), (3, 2, 350, -15.0)]


def test_price_by_lead_time(out):
    # lead days: 1 -> 0; 4 -> 2, 2 -> 3, 5 -> 4; 3 -> 7, 6 -> 9
    assert rows(out["price_by_lead_time"], "starts_in", "listings", "vs_peers_pct") == [
        ("0-1 days", 1, 0.0), ("2-6 days", 3, -20.0), ("7-13 days", 2, 35.0)]


def test_price_vs_peers_bands_and_demand(out):
    # ratio 0.5 -> band 1; 0.8 -> 2; 1.0 (1 and 5) -> 3; 1.2 -> 4; exactly 1.5 -> 5 ("50% or more above")
    assert rows(out["price_vs_peers"], "band", "listings", "share_pct", "price_median", "reviews_ltm_median",
                "open_30_median", "open_90_median") == [
        (1, 1, 16.7, 100, 20.0, 3.0, 3.0), (2, 1, 16.7, 400, 2.0, 28.0, 28.0), (3, 2, 33.3, 350, 8.0, 7.5, 7.5),
        (4, 1, 16.7, 600, 8.0, 2.0, 2.0), (5, 1, 16.7, 300, 4.0, 23.0, 40.0)]


def test_peer_price_guide_only_lists_scored_groups(out):
    assert rows(out["peer_price_guide"], "lga", "size", "listings", "price_p25", "price_median", "price_p75") == [
        ("Alpha", "1 bedroom", 3, 150, 200, 250), ("Alpha", "2 bedrooms", 3, 450, 500, 550)]


def test_weekend_open_counts_scored_homes_with_friday_or_saturday_open(out):
    w = out["weekend_open"]
    assert [str(d.date()) for d in pd.to_datetime(w["friday"])] == [
        "2026-09-18", "2026-09-25", "2026-10-02", "2026-10-09", "2026-10-16", "2026-10-23", "2026-10-30",
        "2026-11-06"]
    # 18 Sep: 1; 25 Sep: 3, 4, 5; 2-16 Oct: 3, 4; 23 and 30 Oct: 3 (open to 3 Nov); 6 Nov: none
    assert list(w["open_listings"]) == [1, 3, 2, 2, 2, 1, 1, 0]
    assert set(w["scored_listings"]) == {6}
    assert list(w["open_pct"]) == [16.7, 50.0, 33.3, 33.3, 33.3, 16.7, 16.7, 0.0]
