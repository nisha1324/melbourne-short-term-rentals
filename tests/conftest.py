"""A hand-made six-listing snapshot in the same format as Inside Airbnb's files.

Every expected value in the tests is worked out by hand from the table below,
so the tests run in CI without the real data (which is never committed).

All listings were scraped on 2026-09-18, so "the last 12 months" starts on
2025-09-18 (inclusive). Councils in the boundary file: Alpha, Beta, Gamma
and Delta (Delta has no listings).

id host source          council room          price   quote (nights)        min  avail365  reviews (dates)
1  10   city            Alpha   Entire home   $300    18-20 Sep (2)          2    100       3: 2024-01-01, 2026-05-01, 2026-09-01
2  10   city            Alpha   Private room  $100    19-20 Sep (1)          1    0 *       1: 2025-09-18 (on the 12-month boundary)
3  20   city            Beta    Entire home   $2,500  20 Sep-20 Oct (30)     30   200       1: 2026-01-10
4  30   previous scrape Beta    Entire home   (none)  (none)                 2    0         1: 2023-03-05
5  40   city            Alpha   Entire home   $200    18-21 Sep (3)          3    365       0
6  20   city            Gamma   Entire home   $400    25-28 Sep (3)          2    50        2: 2026-02-01, 2026-03-01

* listing 2's calendar has 10 open nights (19-28 Sep) though availability_365 says 0 (a planted mismatch).
Listing 4's calendar has 366 days, all closed (as one real listing has).
Open nights start on 18 Sep (1, 5), 19 Sep (2), 20 Sep (3, 6); listing 6's quote starts on 25 Sep, not its first open night.
Active (reviewed since 2025-09-18): listings 1, 2, 3, 6, from hosts 10 and 20.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from str_market import build, profile

SCRAPED = "2026-09-18"

LISTINGS = [
    # id, host, source, lga, room, price, qin, qout, qtotal, qpn, min, av365, nrev, ltm, first, last
    (1, 10, "", "Alpha", "Entire home/apt", "$300.00", "2026-09-18", "2026-09-20", 600, 300, 2, 100, 3, 2,
     "2024-01-01", "2026-09-01"),
    (2, 10, "", "Alpha", "Private room", "$100.00", "2026-09-19", "2026-09-20", 100, 100, 1, 0, 1, 1,
     "2025-09-18", "2025-09-18"),
    (3, 20, "", "Beta", "Entire home/apt", "$2,500.00", "2026-09-20", "2026-10-20", 75000, 2500, 30, 200, 1, 1,
     "2026-01-10", "2026-01-10"),
    (4, 30, "previous scrape", "Beta", "Entire home/apt", "", "", "", "", "", 2, 0, 1, 0,
     "2023-03-05", "2023-03-05"),
    (5, 40, "", "Alpha", "Entire home/apt", "$200.00", "2026-09-18", "2026-09-21", 600, 200, 3, 365, 0, 0, "", ""),
    (6, 20, "", "Gamma", "Entire home/apt", "$400.00", "2026-09-25", "2026-09-28", 1200, 400, 2, 50, 2, 2,
     "2026-02-01", "2026-03-01"),
]
HOST_COUNTS = {10: 2, 20: 2, 30: 1, 40: 1}
REVIEWS = {1: ["2024-01-01", "2026-05-01", "2026-09-01"], 2: ["2025-09-18"], 3: ["2026-01-10"],
           4: ["2023-03-05"], 6: ["2026-02-01", "2026-03-01"]}
# listing -> (calendar days, first open day, open nights)
CALENDAR = {1: (365, "2026-09-18", 100), 2: (365, "2026-09-19", 10), 3: (365, "2026-09-20", 200),
            4: (366, None, 0), 5: (365, "2026-09-18", 365), 6: (365, "2026-09-20", 50)}

HEADER = ["id", "listing_url", "host_id", "host_name", "source", "last_scraped", "description",
          "neighbourhood_cleansed", "latitude", "longitude", "property_type", "room_type", "accommodates",
          "bedrooms", "beds", "bathrooms_text", "price", "price_quote_checkin_date", "price_quote_checkout_date",
          "price_quote_total_price", "price_quote_price_per_night", "minimum_nights", "maximum_nights",
          "has_availability", "availability_30", "availability_90", "availability_365", "number_of_reviews",
          "number_of_reviews_ltm", "first_review", "last_review", "review_scores_rating",
          "estimated_occupancy_l365d", "estimated_revenue_l365d", "calculated_host_listings_count", "host_since",
          "host_is_superhost", "instant_bookable", "license"]


def _gz_csv(path: Path, header: list[str], rows: list[list]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    with gzip.open(path, "wt", newline="") as f:
        f.write(buf.getvalue())


def write_fixture(raw: Path, listings=LISTINGS, calendar=CALENDAR, reviews=REVIEWS, host_counts=HOST_COUNTS,
                  sizes: dict | None = None, superhosts: frozenset = frozenset()) -> None:
    """Write a snapshot in Inside Airbnb's format. `sizes` maps listing id -> (guests, bedrooms);
    listings not in it take 2 guests and 1 bedroom (as every listing in the Part 1 snapshot does).
    Hosts in `superhosts` are marked as Superhosts (none are in the Part 1 and 2 snapshots)."""
    raw.mkdir(parents=True, exist_ok=True)
    sizes = sizes or {}
    rows = []
    for (i, host, src, lga, room, price, qin, qout, qtot, qpn, mn, av, nrev, ltm, first, last) in listings:
        guests, bedrooms = sizes.get(i, (2, 1))
        rows.append([i, f"https://example.invalid/{i}", host, f"Host Name {host}", src, SCRAPED, "a description",
                     lga, -37.8, 144.9, "Entire rental unit", room, guests, bedrooms, 1, "1 bath", price, qin, qout,
                     qtot, qpn,
                     mn, 365, "t", min(av, 30), min(av, 90), av, nrev, ltm, first, last, 4.8 if nrev else "",
                     0, "", host_counts[host], "", "t" if host in superhosts else "f", "", ""])
    _gz_csv(raw / "listings.csv.gz", HEADER, rows)

    cal = []
    for i, (days, first_open, open_n) in calendar.items():
        start = date(2026, 9, 18)
        fo = date.fromisoformat(first_open) if first_open else None
        for d in range(days):
            day = start + timedelta(days=d)
            is_open = fo is not None and fo <= day < fo + timedelta(days=open_n)
            cal.append([i, day.isoformat(), "t" if is_open else "f", 1, 365])
    _gz_csv(raw / "calendar.csv.gz", ["listing_id", "date", "available", "minimum_nights", "maximum_nights"], cal)

    with open(raw / "reviews.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["listing_id", "date"])
        for i, dates in reviews.items():
            w.writerows([i, d] for d in dates)

    feats = [{"type": "Feature", "geometry": None, "properties": {"neighbourhood": n, "neighbourhood_group": None}}
             for n in ("Alpha", "Beta", "Gamma", "Delta")]
    (raw / "neighbourhoods.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("snapshot")
    write_fixture(root / "raw")
    db = root / "fixture.duckdb"
    counts = build.build(raw_dir=root / "raw", db_path=db)
    assert counts == {"listings": 6, "calendar": 6 * 365 + 1, "reviews": 8, "lgas": 4}
    return db


@pytest.fixture()
def con(fixture_db):
    c = profile.connect(fixture_db)
    yield c
    c.close()


@pytest.fixture()
def results(con):
    return profile.run_all(con)
