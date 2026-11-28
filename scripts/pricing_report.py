"""Part 2: write results/PRICING.md, its CSVs and charts 05-08 from the local database.

    python scripts/profile_report.py    # Part 1; also builds data/str_melbourne.duckdb
    python scripts/pricing_report.py    # Part 2, reading the same database

Every figure in the report is read from the query results; none is typed in.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.profile_report import (BLUE, GRID, INK, INK_2, MUTED, ORANGE, SAVE, SURFACE,  # noqa: E402
                                    _clean_axes, _titles, md_table, money, n)
from str_market import pricing as PR, profile as P, source  # noqa: E402

TWO_BED_CHECK_MIN = 30    # councils with this many 2-bedroom homes are used to check the same-size ranking
GF_FRIDAY = "2026-09-25"   # Grand Final eve public holiday; the AFL Grand Final was on Saturday 26 September 2026


def signed(x: float, nd: int = 1) -> str:
    return f"{x:+.{nd}f}%".replace("-", "−")


def plain_pct(x: float) -> str:
    """'−24.9%' as '24.9% below', '+17.9%' as '17.9% above'."""
    return f"{abs(x):.1f}% {'below' if x < 0 else 'above'}"


# ---------------------------------------------------------------- charts

def chart_councils(c: pd.DataFrame, path: Path) -> None:
    d = c.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 8.6))
    y = range(len(d))
    for i, (r, s) in enumerate(zip(d["raw_vs_market_pct"], d["same_size_vs_market_pct"])):
        ax.plot([r, s], [i, i], color=GRID, linewidth=2.2, zorder=1, solid_capstyle="round")
    ax.scatter(d["raw_vs_market_pct"], y, s=46, facecolor=SURFACE, edgecolor=MUTED, linewidth=1.6, zorder=2,
               label="As quoted: council median against the market median")
    ax.scatter(d["same_size_vs_market_pct"], y, s=52, color=BLUE, edgecolor=SURFACE, linewidth=1.2, zorder=3,
               label="Same size: against homes with the same bedrooms market-wide")
    ax.axvline(0, color=INK_2, linewidth=0.9, zorder=0)
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{lga}  ({n(k)})" for lga, k in zip(d["lga"], d["listings"])])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _p: f"{x:+.0f}%".replace("-", "−")
                                                      if x else "0"))
    lo = min(d["raw_vs_market_pct"].min(), d["same_size_vs_market_pct"].min())
    hi = max(d["raw_vs_market_pct"].max(), d["same_size_vs_market_pct"].max())
    ax.set_xlim(lo - 4, hi + 4)
    ax.set_ylim(-0.7, len(d) - 0.3)
    _clean_axes(ax, "x")
    ax.tick_params(axis="y", labelcolor=INK, labelsize=9)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.045), ncol=1, frameon=False, fontsize=9)
    _titles(fig, "Entire-home prices by council, as quoted and for the same size of home",
            "Median quoted nightly price against the median for all 30 councils; sorted by the same-size figure. "
            "Priced active entire homes in brackets.", 0.952)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_size(size: pd.DataFrame, guests: pd.DataFrame, path: Path) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    x = range(len(size))
    a1.bar(x, size["price_median"], color=BLUE, width=0.62)
    a1.errorbar(x, size["price_median"], yerr=[size["price_median"] - size["price_p25"],
                                               size["price_p75"] - size["price_median"]],
                fmt="none", ecolor=INK_2, elinewidth=1, capsize=4)
    for i, (m, hi) in enumerate(zip(size["price_median"], size["price_p75"])):
        a1.text(i, hi + 14, money(m), ha="center", fontsize=8.8, color=INK)
    a1.set_xticks(list(x))
    a1.set_xticklabels([s.replace(" bed", "\nbed") for s in size["size"]], fontsize=8.8)
    a1.set_ylim(0, size["price_p75"].max() * 1.12)
    a1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: money(v)))
    a1.set_title("Median nightly price by bedrooms (bars show the middle half)", loc="left", fontsize=10)
    _clean_axes(a1, "y")
    xg = range(len(guests))
    a2.bar(xg, guests["per_guest_median"], color=BLUE, width=0.62)
    for i, v in enumerate(guests["per_guest_median"]):
        a2.text(i, v + 2, money(v), ha="center", fontsize=8.8, color=INK)
    a2.set_xticks(list(xg))
    a2.set_xticklabels(guests["guests"], fontsize=8.8)
    a2.set_ylim(0, guests["per_guest_median"].max() * 1.15)
    a2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: money(v)))
    a2.set_title("Median price per guest per night, by guests the home takes", loc="left", fontsize=10)
    _clean_axes(a2, "y")
    _titles(fig, "Bigger homes cost more a night but less per guest",
            f"{n(size['listings'].sum())} priced active entire homes; quoted price per night, AUD.", 0.915)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_timing(stay: pd.DataFrame, weekends: pd.DataFrame, path: Path) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [1, 1.25]})
    x = range(len(stay))
    a1.bar(x, stay["vs_peers_pct"], color=BLUE, width=0.62)
    for i, v in enumerate(stay["vs_peers_pct"]):
        a1.text(i, v + (1.2 if v >= 0 else -1.2), signed(v), ha="center", va="bottom" if v >= 0 else "top",
                fontsize=8.8, color=INK)
    a1.axhline(0, color=INK_2, linewidth=0.9)
    a1.set_xticks(list(x))
    a1.set_xticklabels(stay["quoted_stay"], fontsize=8.8)
    a1.set_ylim(stay["vs_peers_pct"].min() * 1.25, max(stay["vs_peers_pct"].max(), 0) + 8)
    a1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:+.0f}%".replace("-", "−") if v else "0"))
    a1.set_title("Nightly price against peers, by length of the quoted stay", loc="left", fontsize=10)
    _clean_axes(a1, "y")
    w = weekends.copy()
    w["friday"] = pd.to_datetime(w["friday"])
    colours = [ORANGE if f == pd.Timestamp(GF_FRIDAY) else BLUE for f in w["friday"]]
    xw = range(len(w))
    a2.bar(xw, w["open_pct"], color=colours, width=0.62)
    for i, v in enumerate(w["open_pct"]):
        a2.text(i, v + 1.2, f"{v:.0f}%", ha="center", fontsize=8.8, color=INK)
    a2.set_xticks(list(xw))
    a2.set_xticklabels([f"{f:%-d %b}" for f in w["friday"]], fontsize=8.8)
    a2.set_ylim(0, w["open_pct"].max() * 1.18)
    a2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    a2.set_title("Share with the Friday or Saturday night still open, by Friday", loc="left", fontsize=10)
    gi = int((w["friday"] == pd.Timestamp(GF_FRIDAY)).to_numpy().argmax())
    a2.text(gi, w["open_pct"].iloc[gi] + 6, "Grand Final\nweekend", ha="center", va="bottom", fontsize=8.8,
            color=INK)
    _clean_axes(a2, "y")
    _titles(fig, "Long stays are discounted, and Grand Final weekend was mostly gone",
            "Left: median of price / peer median (same council and bedrooms). Right: open in the calendar on the "
            "scrape date (17-18 Sep 2026).", 0.915)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_peers(peers: pd.DataFrame, path: Path) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4), sharex=True)
    labels = [s.replace(" or more ", "+ ").replace("A third", "33%") for s in peers["price_vs_peers"]]
    x = range(len(peers))
    for ax, col, title, fmt in (
            (a1, "reviews_ltm_median", "Median reviews in the 12 months to the scrape", lambda v: f"{v:g}"),
            (a2, "open_30_median", "Median open nights in the next 30 days", lambda v: f"{v:g}")):
        ax.bar(x, peers[col], color=BLUE, width=0.62)
        for i, v in enumerate(peers[col]):
            ax.text(i, v + peers[col].max() * 0.02, fmt(v), ha="center", fontsize=8.8, color=INK)
        ax.set_ylim(0, peers[col].max() * 1.15)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8.6, rotation=20, ha="right")
        ax.set_title(title, loc="left", fontsize=10)
        _clean_axes(ax, "y")
    a1.set_xlabel("Price against the peer median", color=INK_2, fontsize=9)
    a2.set_xlabel("Price against the peer median", color=INK_2, fontsize=9)
    _titles(fig, "Homes priced well above their peers get fewer reviews and have more nights open",
            f"{n(peers['listings'].sum())} active entire homes; peers = same council and bedrooms. Open nights are "
            "unbooked or blocked by the host.", 0.915)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, **SAVE)
    plt.close(fig)


# ---------------------------------------------------------------- report

def write_report(out: dict[str, pd.DataFrame], h: dict, results: Path) -> str:
    size, guests, council = out["price_by_size"], out["price_by_guests"], out["price_by_council"]
    stay, dates, lead = out["price_by_stay_length"], out["price_by_stay_dates"], out["price_by_lead_time"]
    peers, guide, wk = out["price_vs_peers"], out["peer_price_guide"], out["weekend_open"]
    sz = size.set_index("bed_band")
    gs = guests.set_index("band")
    st = stay.set_index("band")
    dt = dates.set_index("band")
    pe = peers.set_index("band")
    wk = wk.assign(friday=pd.to_datetime(wk["friday"]))
    gi = int((wk["friday"] == pd.Timestamp(GF_FRIDAY)).to_numpy().argmax())
    gf, after = wk.iloc[gi], wk.iloc[gi + 1]   # weekends are consecutive Fridays
    before = wk.iloc[0]
    late = wk.iloc[-1]
    cs = council.set_index("lga")
    movers = council.assign(move=council["raw_rank"] - council["same_size_rank"])
    fell = movers.nsmallest(4, "move")
    rose = movers.nlargest(2, "move")
    top, bottom = council.iloc[0], council.iloc[-1]
    n_councils = len(council)
    above_market = council[council["same_size_vs_market_pct"] > 0]
    lead_lo, lead_hi = lead["vs_peers_pct"].min(), lead["vs_peers_pct"].max()
    mel2 = guide[(guide["lga"] == "Melbourne") & (guide["bed_band"] == 2)].iloc[0]
    hi_share = pe.loc[5, "share_pct"]
    lo_share = pe.loc[1, "share_pct"]
    rev_ratio = pe.loc[5, "reviews_ltm_median"] / pe.loc[3, "reviews_ltm_median"]
    big_far = pe.loc[[1, 5], "listings"].sum()
    two_bed = council[council["two_bed_listings"] >= TWO_BED_CHECK_MIN]
    rho_same = two_bed["same_size_vs_market_pct"].rank().corr(two_bed["two_bed_median"].rank())
    rho_raw = two_bed["raw_vs_market_pct"].rank().corr(two_bed["two_bed_median"].rank())
    n_two_median = int((council["median_bedrooms"] == 2).sum())

    size_tab = size[["size", "listings", "price_p25", "price_median", "price_p75", "median_guests",
                     "per_guest_median"]].rename(columns={
        "size": "Size", "listings": "Listings", "price_p25": "25th pct $", "price_median": "Median $",
        "price_p75": "75th pct $", "median_guests": "Median guests", "per_guest_median": "Per guest $"})
    guests_tab = guests[["guests", "listings", "price_median", "per_guest_median"]].rename(columns={
        "guests": "Takes", "listings": "Listings", "price_median": "Median $", "per_guest_median": "Per guest $"})
    council_tab = council[["lga", "listings", "price_median", "studio_or_1bed_pct", "raw_vs_market_pct", "raw_rank",
                           "same_size_vs_market_pct", "same_size_rank", "two_bed_median"]].rename(columns={
        "lga": "Council", "listings": "Listings", "price_median": "Median $", "studio_or_1bed_pct": "Studio or 1-bed %",
        "raw_vs_market_pct": "As quoted vs market %", "raw_rank": "Rank as quoted",
        "same_size_vs_market_pct": "Same size vs market %", "same_size_rank": "Rank, same size",
        "two_bed_median": "2-bedroom median $"})
    stay_tab = stay[["quoted_stay", "listings", "price_median", "vs_peers_pct"]].rename(columns={
        "quoted_stay": "Quoted stay", "listings": "Listings", "price_median": "Median $",
        "vs_peers_pct": "Against peers %"})
    dates_tab = dates[["stay_covers", "listings", "price_median", "vs_peers_pct"]].rename(columns={
        "stay_covers": "The quoted stay", "listings": "Listings", "price_median": "Median $",
        "vs_peers_pct": "Against peers %"})
    lead_tab = lead[["starts_in", "listings", "price_median", "vs_peers_pct"]].rename(columns={
        "starts_in": "Stay starts in", "listings": "Listings", "price_median": "Median $",
        "vs_peers_pct": "Against peers %"})
    wk_tab = wk.assign(weekend=[f"Fri {f:%-d %b}" + (" (Grand Final)" if f == pd.Timestamp(GF_FRIDAY) else "")
                                for f in wk["friday"]])[["weekend", "open_listings", "open_pct"]].rename(columns={
        "weekend": "Weekend", "open_listings": "Friday or Saturday open", "open_pct": "Share %"})
    peers_tab = peers[["price_vs_peers", "listings", "share_pct", "price_median", "median_guests",
                       "reviews_ltm_median", "reviews_ltm_mean", "open_30_median", "open_90_median",
                       "rating_median"]].rename(columns={
        "price_vs_peers": "Price against peers", "listings": "Listings", "share_pct": "Share %",
        "price_median": "Median $", "median_guests": "Median guests", "reviews_ltm_median": "Reviews, 12 m (median)",
        "reviews_ltm_mean": "Reviews, 12 m (mean)", "open_30_median": "Open of next 30",
        "open_90_median": "Open of next 90", "rating_median": "Rating"})
    peers_tab["Rating"] = peers_tab["Rating"].map(lambda v: f"{v:.2f}")
    inner = guide[guide["lga"].isin(["Melbourne", "Port Phillip", "Yarra"])].pivot(
        index="size", columns="lga", values="price_median")
    inner = inner.reindex([s for s in size["size"] if s in inner.index]).reset_index().rename(columns={"size": "Size"})

    md = f"""# Part 2: what a night costs

*Written by `scripts/pricing_report.py` from Inside Airbnb's Melbourne snapshot of {source.SNAPSHOT_DATE}. Every
number below is read from the query results.*

## What is compared

This part looks at **active entire homes and apartments** (the {n(h['entire'])} reviewed in the 12 months to the
scrape; Part 1 defines "active"), because they are {n(h['entire'])} of the {n(h['active'])} active listings and the kind a
property manager runs or an investor buys. {n(h['entire_priced'])} have a quoted price and {n(h['homes'])} of those a
bedroom count ({n(h['no_bedrooms'])} have none and are left out).

Two things about the price matter for everything below (Part 1, check 5):

- **It is a quote, not a list price.** `price` is the average nightly price of a real quoted stay: usually the
  listing's minimum stay, starting on its next open night. So each listing has one price, for one set of dates.
- **The calendar has no prices.** It says which nights are open, not what they cost, so price cannot be followed
  through the year for one listing; differences by date are differences between listings.

**Peers.** A listing's peers are the active entire homes in the same council with the same number of bedrooms
(studio, 1, 2, 3, 4, 5 or more). Each listing's price is divided by its peer group's median (the group includes
the listing itself). Groups with fewer than {PR.MIN_PEERS} listings are not scored: {n(h['groups_scored'])} of
{n(h['groups'])} groups are large enough, and they hold {n(h['scored'])} of the {n(h['homes'])} homes
({100 * h['scored'] / h['homes']:.1f}%). Medians throughout, so a few extreme quotes barely move the results.

## Size: price per night rises, price per guest falls

![Price by size](charts/06_price_by_size.png)

{md_table(size_tab, 'lrrrrrr')}

A 2-bedroom home's median quote is {money(sz.loc[2, 'price_median'])} a night against {money(sz.loc[1, 'price_median'])}
for 1 bedroom, and a 3-bedroom's is {money(sz.loc[3, 'price_median'])}. Per guest it runs the other way: from
{money(gs.loc[1, 'per_guest_median'])} a night for homes taking 1-2 guests to {money(gs.loc[5, 'per_guest_median'])}
for homes taking 9 or more.

{md_table(guests_tab, 'lrrr')}

**So what:** per head, a large home is the cheapest way to stay, so large homes compete for groups and families,
and a host pricing a large home per guest like a 1-bedroom would sit far above the market. Bedrooms, not guests, are used for peer groups below, because a host
can change the guest limit but not the floor plan.

## Councils: the raw median misleads

![Entire-home prices by council](charts/05_council_prices_same_size.png)

The market median for a priced active entire home is {money(h['median_price'])}. Ranked by their own medians,
outer-suburban councils look expensive: {fell.iloc[0]['lga']} is {plain_pct(cs.loc[fell.iloc[0]['lga'], 'raw_vs_market_pct'])} the
market and ranks {cs.loc[fell.iloc[0]['lga'], 'raw_rank']} of {n_councils}. But its homes are bigger: its median
entire home has {cs.loc[fell.iloc[0]['lga'], 'median_bedrooms']:.0f} bedrooms, against 2 in {n_two_median} of the
{n_councils} councils. Compared with homes of the same size, the order changes:

- **Down the ranking:** {', '.join(f"{r.lga} {r.raw_rank} → {r.same_size_rank}" for r in fell.itertuples())}. For
  the same number of bedrooms they price {', '.join(plain_pct(v) for v in fell['same_size_vs_market_pct'])} the market.
- **Up the ranking:** {', '.join(f"{r.lga} {r.raw_rank} → {r.same_size_rank}" for r in rose.itertuples())}. Their
  homes are smaller ({' and '.join(f"{v:.1f}%" for v in rose['studio_or_1bed_pct'])} studios or 1-bedrooms, against
  {h['small_pct']:.1f}% market-wide), which hides that size for size they price
  {', '.join(plain_pct(v) for v in rose['same_size_vs_market_pct'])} the market.
- **Top and bottom, size for size:** {top['lga']} ({plain_pct(top['same_size_vs_market_pct'])}; the Yarra Valley and the
  Dandenongs) and {bottom['lga']} ({plain_pct(bottom['same_size_vs_market_pct'])}). {len(above_market)} of the
  {n_councils} councils price above the market for their size.

"Same size" is the median, across a council's homes, of price ÷ the market median for the same bedrooms. The
2-bedroom median is a check that needs no adjustment: across the {len(two_bed)} councils with {TWO_BED_CHECK_MIN} or
more 2-bedroom homes, it ranks councils much as the same-size figure does (rank correlation {rho_same:.2f}) and
quite unlike the raw median ({rho_raw:.2f}).

{md_table(council_tab, 'lrrrrrrrr')}

**So what:** a council's median nightly rate says more about its housing stock than about what guests will pay.
An investor comparing suburbs, or a council comparing itself with its neighbours, should compare like with like:
the peer price guide below, or the same-size column.

### A price guide by council and size

`results/peer_price_guide.csv` gives the 25th percentile, median and 75th percentile quote for each of the
{n(len(guide))} council × size groups with {PR.MIN_PEERS} or more active entire homes. For the three inner councils:

{md_table(inner, 'l' + 'r' * (inner.shape[1] - 1))}

Median quote, $ a night; a blank means fewer than {PR.MIN_PEERS} active entire homes of that size.

A 2-bedroom home in the City of Melbourne quotes {money(mel2['price_median'])} at the median, and the middle half
of them quote {money(mel2['price_p25'])} to {money(mel2['price_p75'])}.

## Timing: long stays are cheaper a night, big weekends dearer

![Long stays and Grand Final weekend](charts/07_price_by_stay.png)

{md_table(stay_tab, 'lrrr')}

Against their peers, homes quoting a 1-night stay price {signed(st.loc[1, 'vs_peers_pct'])} and 2-6 nights close to
the median, but week-plus quotes are {plain_pct(st.loc[4, 'vs_peers_pct'])} and stays of 28 nights or more
{plain_pct(st.loc[5, 'vs_peers_pct'])}, in line with the weekly and monthly discounts hosts can set. Those are
{n(st.loc[5, 'listings'])} listings, so a small part of the market, but they are the most like a long-term rental
and come up again in Part 4.

**Weekends and Grand Final weekend.** For short quoted stays (1-3 nights) starting in the 60 days after the scrape
({n(h['short_stays'])} homes):

{md_table(dates_tab, 'lrrr')}

Stays covering a Friday or Saturday night quote {signed(dt.loc[2, 'vs_peers_pct'])} against peers, and Sunday to
Thursday stays {signed(dt.loc[3, 'vs_peers_pct'])}. Stays covering the night of Friday 25 or Saturday 26 September 2026
quote {signed(dt.loc[1, 'vs_peers_pct'])}. That was the AFL Grand Final weekend: the match was at the MCG on
Saturday 26 September, and Friday 25 September was Victoria's Grand Final eve public holiday
([City of Melbourne](https://whatson.melbourne.vic.gov.au/footy-in-the-city);
[Premier of Victoria](https://www.premier.vic.gov.au/footy-festival-starts-countdown-historic-grand-final)).

The calendar shows how much of that weekend was already gone a week before:

{md_table(wk_tab, 'lrr')}

Only {gf['open_pct']:.1f}% of scored homes still had the Friday or the Saturday open, against {before['open_pct']:.1f}%
for the weekend the scrape finished on (Friday 18 September) and {after['open_pct']:.1f}% the weekend after the Grand Final;
from late October about {late['open_pct']:.0f}% are still open. The calendar cannot separate a booked night from a
blocked one, so this is "not available", not "booked".

Two cautions on the {signed(dt.loc[1, 'vs_peers_pct'])}. It compares different listings: each home has one quote,
and the {n(dt.loc[1, 'listings'])} homes whose next stay fell on that weekend are those still open then, not the
same homes priced on another date. And their peers are measured on whatever dates their own quotes fell. It is
consistent with event pricing, not a measure of it.

**How far ahead the stay starts makes little difference.** Grouped by days from the scrape to the quoted check-in,
the median against peers stays between {signed(lead_lo)} and {signed(lead_hi)}, with no steady last-minute discount
or early-booking premium:

{md_table(lead_tab, 'lrrr')}

**So what:** for a property manager the clear levers are length of stay (monthly guests take a large discount) and
peak events, where most homes are taken well ahead: a host whose home was still open for Grand Final weekend a
week before had few competing homes left on the calendar.

## Listings priced well above or below their peers

![Price against peers and demand](charts/08_price_vs_demand.png)

{md_table(peers_tab, 'lrrrrrrrrr')}

Bands are symmetric on a ratio scale ("within 10%" is 0.9 to 1.11 times the peer median; "50% or more above" is
1.5 times or more and "a third or more below" is 1 ÷ 1.5 or less). {hi_share:.1f}% of scored homes price 50% or
more above their peers and {lo_share:.1f}% a third or more below.

- **Homes priced well above their peers get fewer reviews.** The median for homes 50% or more above is
  {pe.loc[5, 'reviews_ltm_median']:g} reviews in the year against {pe.loc[3, 'reviews_ltm_median']:g} for homes within
  10% ({rev_ratio:.0%} as many), and they have {pe.loc[5, 'open_30_median']:g} of the next 30 nights open against
  {pe.loc[3, 'open_30_median']:g}. A review needs a completed stay, so fewer reviews means fewer stays, unless
  guests of dearer homes review less often, which this data cannot show.
- **It is not just bigger homes.** Peers already share a council and bedroom count, and the median guest limit is
  {pe.loc[5, 'median_guests']:g} in every band.
- **They are rated a little higher** ({pe.loc[5, 'rating_median']:.2f} against {pe.loc[3, 'rating_median']:.2f} at the
  median), so part of the gap is likely quality the bedroom count does not capture: views, fit-out, location within
  the council.
- **Cheap homes are only a little busier.** Homes a third or more below their peers have about the same median
  reviews as those near the median ({pe.loc[1, 'reviews_ltm_median']:g} against {pe.loc[3, 'reviews_ltm_median']:g})
  and slightly fewer open nights ({pe.loc[1, 'open_30_median']:g} of the next 30 against
  {pe.loc[3, 'open_30_median']:g}). Pricing far below peers goes with only a small gain on either measure.

**So what:** of the {n(big_far)} homes in the two outer bands, the dear ones show fewer stays and more open nights, and
the cheap ones only slightly the reverse. For a property manager taking on a new home, the peer median is the starting price, and a
quote 50% above it needs the quality to back it. Whether the dearer homes still earn more over the year (a higher
price on fewer nights) is Part 4's question, which estimates earnings.

## Limits

- One quote per listing, for its next open stay, so price differences by date are differences between listings.
- Peers share a council and bedroom count, not a street, view or fit-out; a council is a large area.
- Reviews stand in for stays, and open calendar nights mix unbooked with blocked nights.
- The Grand Final dates come from the City of Melbourne and the Premier's office, cited above; the scrape was about a
  week before, so the calendar shows bookings as of then, not the final take-up.
"""
    (results / "PRICING.md").write_text(md)
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", type=Path, default=source.RESULTS, help="folder to write to (default results/)")
    args = ap.parse_args()
    results: Path = args.results
    (results / "charts").mkdir(parents=True, exist_ok=True)
    con = P.connect()
    PR.prepare(con)
    out = PR.run_all(con)
    h = PR.headline(con)
    for name, df in out.items():
        df.to_csv(results / f"{name}.csv", index=False)
    chart_councils(out["price_by_council"], results / "charts" / "05_council_prices_same_size.png")
    chart_size(out["price_by_size"], out["price_by_guests"], results / "charts" / "06_price_by_size.png")
    chart_timing(out["price_by_stay_length"], out["weekend_open"], results / "charts" / "07_price_by_stay.png")
    chart_peers(out["price_vs_peers"], results / "charts" / "08_price_vs_demand.png")
    write_report(out, h, results)
    print(f"wrote {results / 'PRICING.md'}, {len(out)} CSVs and 4 charts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
