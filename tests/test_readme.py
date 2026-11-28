"""Every figure in the README's Part 1 findings is rebuilt from the committed results (runs in CI)."""
from __future__ import annotations

import json
import re

import pandas as pd
import pytest

from str_market import source

README = (source.ROOT / "README.md").read_text()
R = source.RESULTS


def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(R / f"{name}.csv")


def text() -> str:
    return re.sub(r"\s+", " ", README)


def pct(part: float, whole: float) -> str:
    return f"{100 * part / whole:.1f}%"


def statements() -> list[str]:
    ms = csv("market_size").set_index("row_no")
    src = csv("by_scrape_source").set_index("scrape_source")
    room = csv("by_room_type").set_index("room_type")
    lga = csv("by_lga")
    mn = csv("minimum_nights").set_index("bucket")
    hosts = csv("host_size").set_index("band")
    qc = csv("quality_checks").set_index("check_no")
    profile = (R / "PROFILE.md").read_text()
    act, act_hosts = ms.loc[5, "listings"], ms.loc[5, "hosts"]
    prev = src.loc["previous scrape"]
    ent, prv = room.loc["Entire home/apt"], room.loc["Private room"]
    inner3 = lga[lga["lga"].isin(["Melbourne", "Port Phillip", "Yarra"])]["active_listings"].sum()
    top10 = lga[lga["lga"] == "Melbourne"].iloc[0]
    big = hosts.loc[[4, 5], "active_listings"].sum()
    n_pass = int((qc["found"] == qc["expected"]).sum())
    calendar_mismatch = int(qc.loc[[9, 10], "found"].sum())
    snap = json.loads((source.ROOT / "data" / "SNAPSHOT.json").read_text())
    cal_rows = re.search(r"`calendar.csv.gz` \| ([\d,]+) \|", profile).group(1)
    rev_rows = re.search(r"`reviews.csv` \| ([\d,]+) \|", profile).group(1)
    raw_mb = sum(f["bytes"] for f in snap["files"].values()) / 1e6
    assert round((ms.loc[1, "listings"] - act) / act, 2) == pytest.approx(0.65)   # "about two-thirds"
    return [
        f"The snapshot has {ms.loc[1, 'listings']:,} listings",
        f"only **{act:,}** (from {act_hosts:,} hosts) had a review in the 12 months",
        f"{prev['listings']:,} listings were carried over",
        f"({prev['no_open_nights']:,} have no open night",
        f"median last review is {pd.Timestamp(prev['median_last_review']):%B %Y}",
        f"{ent['share_pct']}% of active listings are entire homes",
        f"price of ${int(ent['price_median'])} a night "
        f"(${int(ent['price_p25'])} to ${int(ent['price_p75'])} for the middle half)",
        f"a private room's median is ${int(prv['price_median'])}",
        f"The City of Melbourne alone has {top10['share_of_market_pct']}% of active listings",
        f"the three inner councils have {pct(inner3, act)}",
        f"{mn.loc[1, 'share_pct'] + mn.loc[2, 'share_pct']:.1f}% accept one or two nights",
        f"only {mn.loc[5, 'active_listings']:,} ({mn.loc[5, 'share_pct']}%) need 28 nights or more",
        f"Hosts with two or more active listings have {pct(act - hosts.loc[1, 'active_listings'], act)} of them",
        f"{hosts.loc[[4, 5], 'hosts'].sum():,} hosts with 10 or more have {pct(big, act)}",
        f"{n_pass} of {len(qc)} quality checks pass outright",
        f"Two small calendar mismatches ({calendar_mismatch} listings)",
        f"the detailed listings ({ms.loc[1, 'listings']:,} listings)",
        f"the 365-day calendar ({cal_rows} listing-days)",
        f"the date of every review ({rev_rows} reviews)",
        f"~{raw_mb:.0f} MB into data/raw/",
        f"snapshot of {pd.Timestamp(snap['snapshot']):%-d %B %Y}",
        f"over {ms.loc[1, 'listings'] // 1000 * 1000:,} places to stay",
        "20 data-quality checks" if len(qc) == 20 else "MISMATCH",
    ]


@pytest.mark.parametrize("statement", statements())
def test_readme_figure_matches_results(statement):
    assert statement in text()


def test_roadmap_points_at_existing_reports():
    for link in re.findall(r"\]\((results/[^)]+)\)", README):
        assert (source.ROOT / link).exists(), link


def ordinal(k: float) -> str:
    k = int(k)
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def part2_statements() -> list[str]:
    size = csv("price_by_size").set_index("bed_band")
    guests = csv("price_by_guests").set_index("band")
    council = csv("price_by_council").set_index("lga")
    stay = csv("price_by_stay_length").set_index("band")
    dates = csv("price_by_stay_dates").set_index("band")
    peers = csv("price_vs_peers").set_index("band")
    guide = csv("peer_price_guide")
    wk = csv("weekend_open").set_index("friday")
    homes = int(size["listings"].sum())
    scored = int(peers["listings"].sum())
    ca, wy, st, pp = (council.loc[c] for c in ("Casey", "Wyndham", "Stonnington", "Port Phillip"))
    return [
        f"It covers the {homes:,} active entire homes with a quoted price and a bedroom count",
        f"(groups of 10 or more, which hold {pct(scored, homes)} of the homes)",
        f"Casey and Wyndham are the {ordinal(ca['raw_rank'])} and {ordinal(wy['raw_rank'])} dearest of "
        f"{len(council)} councils",
        f"(a median {ca['median_bedrooms']:.0f} bedrooms)" if ca["median_bedrooms"] == wy["median_bedrooms"]
        else "MISMATCH",
        f"Size for size they price {-ca['same_size_vs_market_pct']:.1f}% and {-wy['same_size_vs_market_pct']:.1f}% "
        f"below the market and rank {ordinal(ca['same_size_rank'])} and {ordinal(wy['same_size_rank'])}",
        f"Stonnington and Port Phillip go the other way ({ordinal(st['raw_rank'])} → {ordinal(st['same_size_rank'])} "
        f"and {ordinal(pp['raw_rank'])} → {ordinal(pp['same_size_rank'])})",
        f"a price guide for {len(guide)} council × size groups",
        f"The median quote rises from ${size.loc[1, 'price_median']} for 1 bedroom to ${size.loc[2, 'price_median']} "
        f"for 2 and ${size.loc[3, 'price_median']} for 3",
        f"price per guest falls from ${guests.loc[1, 'per_guest_median']} (homes taking 1-2 guests) to "
        f"${guests.loc[5, 'per_guest_median']} (9 or more)",
        f"quotes for 7-27 nights are {-stay.loc[4, 'vs_peers_pct']:.1f}% below and quotes for 28 nights or more "
        f"{-stay.loc[5, 'vs_peers_pct']:.1f}% below",
        f"Only {wk.loc['2026-09-25', 'open_pct']:.1f}% of homes still had the Friday or Saturday of 25-26 September 2026 "
        f"open, against {wk.loc['2026-10-02', 'open_pct']:.1f}% the weekend after",
        f"Short stays covering those nights quoted {dates.loc[1, 'vs_peers_pct']:.1f}% above peers",
        f"The {peers.loc[5, 'share_pct']:.1f}% priced 50% or more above their peers have a median of "
        f"{peers.loc[5, 'reviews_ltm_median']:g} reviews in the year against {peers.loc[3, 'reviews_ltm_median']:g} "
        f"for homes within 10%, and {peers.loc[5, 'open_30_median']:g} of the next 30 nights open against "
        f"{peers.loc[3, 'open_30_median']:g}",
        "though they are rated slightly higher" if peers.loc[5, "rating_median"] > peers.loc[3, "rating_median"]
        else "MISMATCH",
    ]


@pytest.mark.parametrize("statement", part2_statements())
def test_readme_part2_figure_matches_results(statement):
    assert statement in text()


def test_part2_ranking_claims_hold():
    council = csv("price_by_council")
    moved = council.assign(move=council["raw_rank"] - council["same_size_rank"])
    # the two councils named as rising are the two biggest risers; Casey and Wyndham are among the four biggest fallers
    assert set(moved.nlargest(2, "move")["lga"]) == {"Stonnington", "Port Phillip"}
    assert {"Casey", "Wyndham"} <= set(moved.nsmallest(4, "move")["lga"])
