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
