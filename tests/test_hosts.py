"""Part 3 host queries on a third hand-made snapshot (expected values worked out by hand).

All listings scraped 2026-09-18, 1 bedroom; Part 2 thresholds for this fixture: min_peers = 3.
Councils: Alpha, Beta and Yarra (one of the "inner three", to test those columns).

host listings (active)               where                         room / price                  Superhost
1    50                              45 Alpha, 5 Beta              entire; $100 (one: min stay 28) no
2    10 (+2 dormant)                 4 Alpha, 3 Beta, 3 Yarra      Alpha $200 x4, Beta $100 x3,   yes
                                                                   Yarra 1 entire $100 + 2 rooms
3    5                               5 Beta                        entire $150                    yes
4    2 (+3 dormant)                  2 Yarra                       1 entire $100, 1 room          no
5-10 1 each                          5, 6 Alpha; 7, 8 Beta;        entire: 5 $100, 6 $300,         5 yes
                                     9, 10 Yarra                   7 $100, 8 $50, 9 $100, 10 $200
11   0 (+1 dormant)

Active: 73 listings from 10 hosts (70 entire homes). Peer medians (council x 1 bedroom), all $100:
Alpha 46 x $100, 4 x $200, 1 x $300; Beta $50, 9 x $100, 5 x $150; Yarra 3 x $100, 1 x $200.
So ratios: host 1 all 1.0; host 2 2.0 (Alpha) and 1.0 (Beta, Yarra); host 3 1.5; host 4 1.0;
singles 1.0, 3.0, 1.0, 0.5, 1.0, 2.0.
"""
from __future__ import annotations

import pandas as pd
import pytest

from str_market import build, hosts, profile

from conftest import write_fixture

E, R = "Entire home/apt", "Private room"


def _listing(i, host, lga, room, price, ltm=5, min_nights=1):
    return (i, host, "", lga, room, f"${price:,.2f}", "", "", "", price, min_nights, 100, ltm, ltm,
            "2026-01-01" if ltm else "2024-01-01", "2026-09-01" if ltm else "2024-01-01")


def _listings() -> list[tuple]:
    rows: list[tuple] = []
    add = lambda *a, **k: rows.append(_listing(len(rows) + 1, *a, **k))  # noqa: E731
    for j in range(50):
        add(1, "Alpha" if j < 45 else "Beta", E, 100, min_nights=28 if j == 0 else 1)
    for _ in range(4):
        add(2, "Alpha", E, 200)
    for _ in range(3):
        add(2, "Beta", E, 100)
    add(2, "Yarra", E, 100)
    add(2, "Yarra", R, 50)
    add(2, "Yarra", R, 50)
    for _ in range(5):
        add(3, "Beta", E, 150)
    add(4, "Yarra", E, 100)
    add(4, "Yarra", R, 50)
    for host, lga, price in ((5, "Alpha", 100), (6, "Alpha", 300), (7, "Beta", 100), (8, "Beta", 50),
                             (9, "Yarra", 100), (10, "Yarra", 200)):
        add(host, lga, E, price, ltm=10)
    for host, n in ((2, 2), (4, 3), (11, 1)):        # dormant: no review in 12 months, so not active
        for _ in range(n):
            add(host, "Alpha", E, 100, ltm=0)
    return rows


LISTINGS = _listings()
HOST_COUNTS = {1: 50, 2: 12, 3: 5, 4: 5, **{h: 1 for h in range(5, 12)}}


@pytest.fixture(scope="module")
def hcon(tmp_path_factory):
    root = tmp_path_factory.mktemp("hosts")
    write_fixture(root / "raw", listings=LISTINGS, calendar={r[0]: (1, None, 0) for r in LISTINGS}, reviews={},
                  host_counts=HOST_COUNTS, superhosts=frozenset({2, 3, 5}))
    db = root / "hosts.duckdb"
    build.build(raw_dir=root / "raw", db_path=db)
    c = profile.connect(db)
    hosts.prepare(c, min_peers=3, min_council_listings=2)
    yield c
    c.close()


@pytest.fixture(scope="module")
def out(hcon):
    return hosts.run_all(hcon)


def rows(df: pd.DataFrame, *cols: str) -> list[tuple]:
    return [tuple(None if pd.isna(v) else v for v in r) for r in df[list(cols)].itertuples(index=False)]


def test_fixture_counts(hcon):
    assert len(LISTINGS) == 79
    assert hcon.execute("SELECT count(*), count(DISTINCT host_id), count(*) FILTER (WHERE is_entire) "
                        "FROM host_listings").fetchone() == (73, 10, 70)


def test_host_bands_count_active_listings_only(hcon):
    # host 2 has 12 listings in the snapshot but 10 active; host 4 has 5 but 2 active
    got = hcon.execute("SELECT host_id, listings, host_band, councils, in_main_council, in_inner3, entire_homes "
                       "FROM hosts WHERE host_id <= 4 ORDER BY host_id").fetchall()
    assert got == [(1, 50, 5, 2, 45, 0, 50), (2, 10, 4, 3, 4, 3, 8), (3, 5, 3, 1, 5, 0, 5), (4, 2, 2, 1, 2, 2, 1)]


def test_concentration_summary(out):
    # all: shares 50, 10, 5, 2, 1 x 6 of 73 -> HHI 10,000 x 2,635 / 5,329 = 4,944.6; 5,329 / 2,635 = 2.02 -> 2
    # entire: 50, 8, 5, 1, 1 x 6 of 70 -> 10,000 x 2,596 / 4,900 = 5,298.0; 4,900 / 2,596 = 1.89 -> 2
    assert rows(out["concentration_summary"], "market", "hosts", "listings", "listings_per_host", "hhi",
                "equivalent_hosts", "hosts_for_half", "hosts_for_half_pct", "operators", "operator_share_pct",
                "single_listing_share_pct") == [
        ("All active listings", 10, 73, 7.3, 4944.6, 2, 1, 10.0, 2, 82.2, 8.2),
        ("Active entire homes", 10, 70, 7.0, 5298.0, 2, 1, 10.0, 2, 82.9, 8.6)]


def test_largest_hosts(out):
    # only k <= the number of hosts (10) is reported
    assert rows(out["largest_hosts"], "largest_hosts", "share_of_hosts_pct", "active_listings",
                "share_of_listings_pct", "share_of_entire_homes_pct") == [
        (1, 10.0, 50, 68.5, 71.4), (10, 100.0, 73, 100.0, 100.0)]


def test_host_curve(out):
    c = out["host_curve"].set_index("share_of_hosts_pct")
    assert len(c) == 101
    # 25% of 10 hosts = 2.5, rounded half away from zero to 3 hosts: 50 + 10 + 5 = 65 of 73
    assert [(p, c.loc[p, "hosts"], c.loc[p, "share_of_listings_pct"]) for p in (0, 10, 20, 25, 100)] == [
        (0, 0, 0.0), (10, 1, 68.49), (20, 2, 82.19), (25, 3, 89.04), (100, 10, 100.0)]


def test_council_hosts(out):
    # Alpha: hosts 1 (45), 2 (4), 5, 6 -> HHI 10,000 x 2,043 / 2,601 = 7,855; half: host 1 alone
    # Beta: hosts 1 (5), 3 (5), 2 (3), 7, 8 -> HHI 10,000 x 61 / 225 = 2,711; half: two hosts (10 of 15)
    # Yarra: hosts 2 (3), 4 (2), 9, 10 -> HHI 10,000 x 15 / 49 = 3,061; half: two hosts (5 of 7)
    assert rows(out["council_hosts"], "lga", "active_listings", "hosts", "single_host_pct", "two_to_nine_pct",
                "operator_pct", "operators_present", "entire_homes", "operator_entire_pct",
                "single_host_entire_homes", "top10_share_pct", "hosts_for_half", "hhi") == [
        ("Alpha", 51, 4, 3.9, 0.0, 96.1, 2, 51, 96.1, 2, 100.0, 1, 7855),
        ("Beta", 15, 5, 13.3, 33.3, 53.3, 2, 15, 53.3, 2, 100.0, 2, 2711),
        ("Yarra", 7, 4, 28.6, 28.6, 42.9, 1, 4, 25.0, 2, 100.0, 2, 3061)]


def test_host_size_profile(out):
    # band 1 ratios .5 1 1 1 2 3 -> median 1.0, 2 of 6 at 1.5+; band 4 ratios 1 x4, 2 x4 -> 1.5, 4 of 8 at 1.5+
    assert rows(out["host_size_profile"], "host_size", "hosts", "active_listings", "share_of_listings_pct",
                "entire_pct", "entire_price_median", "vs_peers_pct", "far_above_pct", "reviews_ltm_median",
                "min_28_pct", "superhost_pct", "median_councils") == [
        ("1 listing", 6, 6, 8.2, 100.0, 100, 0.0, 33.3, 10.0, 0.0, 16.7, 1.0),
        ("2-4 listings", 1, 2, 2.7, 50.0, 100, 0.0, 0.0, 5.0, 0.0, 0.0, 1.0),
        ("5-9 listings", 1, 5, 6.8, 100.0, 150, 50.0, 100.0, 5.0, 0.0, 100.0, 1.0),
        ("10-49 listings", 1, 10, 13.7, 80.0, 150, 50.0, 50.0, 5.0, 0.0, 100.0, 3.0),
        ("50+ listings", 1, 50, 68.5, 100.0, 100, 0.0, 0.0, 5.0, 2.0, 0.0, 2.0)]


def test_operator_spread(out):
    # hosts 1 (2 councils) and 2 (3 councils); main-council shares 45/50 and 4/10 -> median 65%
    assert rows(out["operator_spread"], "councils", "operators", "active_listings", "median_listings", "entire_pct",
                "median_main_council_pct", "inner3_pct") == [("2-3 councils", 2, 60, 30.0, 96.7, 65.0, 5.0)]


def test_typical_operator(out):
    # host 2's scored homes: ratios 2 x4, 1 x4 -> median 1.5; host 1's: 1.0; across both: 1.25
    assert rows(out["typical_operator"], "operators", "hosts", "median_listings", "median_councils",
                "only_entire_pct", "one_council_mostly_pct", "any_inner3_pct", "vs_peers_pct", "superhost_pct") == [
        ("10-49 listings", 1, 10.0, 3.0, 0.0, 0.0, 100.0, 50.0, 100.0),
        ("50+ listings", 1, 50.0, 2.0, 100.0, 100.0, 0.0, 0.0, 0.0),
        ("All operators (10+)", 2, 30.0, 2.5, 50.0, 50.0, 50.0, 25.0, 50.0)]


def test_host_count_check_shows_inside_airbnbs_count(out):
    # by snapshot count: hosts 5-11 have 1; hosts 3 and 4 have 5; host 2 has 12; host 1 has 50
    assert rows(out["host_count_check"], "host_size", "hosts_by_active_listings", "hosts_by_all_listings") == [
        ("1 listing", 6, 7), ("2-4 listings", 1, 0), ("5-9 listings", 1, 2), ("10-49 listings", 1, 1),
        ("50+ listings", 1, 1)]


def test_no_per_host_rows_leave_the_module(out):
    for name, df in out.items():
        assert "host_id" not in df.columns, name


# ------------------------------------------------------------------ boundaries on an in-memory table
# Three hosts in council Zed: 49 listings (top of "10-49"), 50 (bottom of "50+") and 1: 100 in all,
# so the 50-listing host runs exactly half the market.

@pytest.fixture(scope="module")
def edge():
    import duckdb
    c = duckdb.connect()
    c.execute("""CREATE TABLE active AS
                 SELECT row_number() OVER () AS listing_id, host_id, 'Zed' AS lga, 'Entire home/apt' AS room_type,
                        100.0 AS price, 1 AS bedrooms, 1 AS minimum_nights, 5 AS number_of_reviews_ltm,
                        4.8 AS review_scores_rating, false AS host_is_superhost
                 FROM (SELECT unnest([49, 50, 1]) AS n, unnest([1, 2, 3]) AS host_id), range(100) r(i)
                 WHERE i < n""")
    c.execute("CREATE TABLE priced_homes AS SELECT listing_id, 1.0 AS ratio, 0 AS open_30 FROM active")
    c.execute((hosts.SQL_DIR / "host_listings.sql").read_text())
    yield c
    c.close()


def test_edge_49_and_50_listings_fall_in_different_bands(edge):
    assert edge.execute("SELECT listings, host_band FROM hosts ORDER BY listings").fetchall() == [
        (1, 1), (49, 4), (50, 5)]


def test_edge_exactly_half_needs_one_host(edge):
    s = edge.execute((hosts.SQL_DIR / "concentration_summary.sql").read_text()).df().iloc[0]
    assert (s["listings"], s["hosts_for_half"], s["operators"], s["operator_share_pct"]) == (100, 1, 2, 99.0)


# ------------------------------------------------------------------ queries on hand-built base tables
# The later queries read only the `hosts` or `host_listings` views, so these tests build those directly.

def _run(tables: dict[str, str], query: str) -> pd.DataFrame:
    import duckdb
    c = duckdb.connect()
    for name, sql in tables.items():
        c.execute(f"CREATE TABLE {name} AS {sql}")
    try:
        return c.execute((hosts.SQL_DIR / query).read_text()).df()
    finally:
        c.close()


HOSTS_TABLE = """SELECT * FROM (VALUES
    -- host_id, listings, host_band, entire_homes, councils, in_main_council, in_inner3, superhost, median_ratio
    (1, 60, 5, 0, 2, 10, 0, false, 1.0),   -- the largest host by listings has no entire homes
    (2, 20, 4, 20, 2, 10, 0, false, 1.0),
    (3, 50, 5, 50, 3, 20, 0, false, 1.6),
    (4, 2, 2, 2, 1, 2, 0, false, 1.0)
) t(host_id, listings, host_band, entire_homes, councils, in_main_council, in_inner3, superhost, median_ratio)"""


def test_largest_hosts_ranks_entire_homes_separately():
    # by listings: 60 (no entire homes), 50, 20, 2 of 132; by entire homes: 50, 20, 2, 0 of 72
    got = _run({"hosts": HOSTS_TABLE}, "largest_hosts.sql")
    assert rows(got, "largest_hosts", "active_listings", "share_of_listings_pct", "share_of_entire_homes_pct") == [
        (1, 60, 45.5, 69.4)]


def test_operator_medians_are_medians():
    # operators 1-3: main-council shares 10/60, 10/20, 20/50 -> median 40% (mean 35.6%);
    # their median ratios 1.0, 1.0, 1.6 -> median +0% (mean +20%)
    spread = _run({"hosts": HOSTS_TABLE}, "operator_spread.sql")
    assert rows(spread, "councils", "operators", "median_main_council_pct") == [("2-3 councils", 3, 40.0)]
    typical = _run({"hosts": HOSTS_TABLE}, "typical_operator.sql").set_index("row_no")
    assert typical.loc[3, "vs_peers_pct"] == 0.0


def test_council_top10_and_one_listing_entire_homes():
    # 11 one-listing hosts in one council; host 11's listing is a private room
    got = _run({"host_listings": """SELECT i AS listing_id, i AS host_id, 'Zed' AS lga, 1 AS host_band,
                                           i < 11 AS is_entire FROM range(1, 12) r(i)"""}, "council_hosts.sql")
    assert rows(got, "active_listings", "hosts", "top10_share_pct", "single_host_entire_homes", "hosts_for_half") == [
        (11, 11, 90.9, 10, 6)]
