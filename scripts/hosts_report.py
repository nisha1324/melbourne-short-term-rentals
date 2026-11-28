"""Part 3: write results/HOSTS.md, its CSVs and charts 09-11 from the local database.

    python scripts/profile_report.py    # Part 1; also builds data/str_melbourne.duckdb
    python scripts/hosts_report.py      # Part 3, reading the same database

Every figure in the report is read from the query results; none is typed in.
No host is named and no per-host row is written: only aggregates.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.profile_report import (BLUE, GRID, INK, INK_2, MUTED, SAVE, SURFACE,  # noqa: E402
                                    _clean_axes, _titles, md_table, money, n)
from str_market import hosts as H, profile as P, source  # noqa: E402

# Ordinal blue ramp (steps 250 / 400 / 600 of the reference palette); passes the dataviz
# validator in --ordinal mode: monotone lightness, single hue, light end 2.06:1 on the surface.
RAMP = {"1 listing": "#84b9f3", "2-9 listings": "#338ced", "10+ listings": "#1757ac"}
INNER3 = ("Melbourne", "Port Phillip", "Yarra")


def ordinal(k: int) -> str:
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def signed(x: float, nd: int = 1) -> str:
    if round(x, nd) == 0:
        return f"{0:.{nd}f}%"
    return f"{x:+.{nd}f}%".replace("-", "−")


def place(lga: str) -> str:
    return "the City of Melbourne" if lga == "Melbourne" else lga


# ---------------------------------------------------------------- charts

def chart_curve(curve: pd.DataFrame, summary: pd.DataFrame, largest: pd.DataFrame, path: Path) -> None:
    allm = summary.iloc[0]
    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.plot([0, 100], [0, 100], color=MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    ax.text(62, 57, "if every host ran the same number", color=INK_2, fontsize=8.8, rotation=0, ha="left")
    ax.plot(curve["share_of_hosts_pct"], curve["share_of_listings_pct"], color=BLUE, linewidth=2, zorder=2)
    c = curve.set_index("share_of_hosts_pct")
    ops_x = 100 * allm["operators"] / allm["hosts"]
    points = [
        (1, c.loc[1, "share_of_listings_pct"], f"largest 1% of hosts ({n(c.loc[1, 'hosts'])})\n"
                                              f"run {c.loc[1, 'share_of_listings_pct']:.1f}%", (9, 14)),
        (ops_x, allm["operator_share_pct"], f"{n(allm['operators'])} operators (10+ listings,\n"
                                            f"{ops_x:.1f}% of hosts) run {allm['operator_share_pct']:.1f}%", (13, 31)),
        (allm["hosts_for_half_pct"], 50.0, f"{n(allm['hosts_for_half'])} hosts ({allm['hosts_for_half_pct']:.1f}%)\n"
                                         "run half", (19, 44)),
    ]
    for x, y, label, (tx, ty) in points:
        ax.scatter([x], [y], s=64, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.annotate(label, (x, y), xytext=(tx, ty), fontsize=8.8, color=INK, va="center",
                    arrowprops={"arrowstyle": "-", "color": INK_2, "linewidth": 0.8, "shrinkA": 2, "shrinkB": 4})
    half = 50
    ax.scatter([half], [c.loc[half, "share_of_listings_pct"]], s=64, color=BLUE, edgecolor=SURFACE, linewidth=2,
               zorder=3)
    ax.annotate(f"the largest half of hosts\nrun {c.loc[half, 'share_of_listings_pct']:.1f}%",
                (half, c.loc[half, "share_of_listings_pct"]), xytext=(55, 88), fontsize=8.8, color=INK,
                va="center", arrowprops={"arrowstyle": "-", "color": INK_2, "linewidth": 0.8, "shrinkA": 2,
                                         "shrinkB": 4})
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    ax.set_xlabel("Share of hosts, largest first", color=INK_2, fontsize=9)
    ax.set_ylabel("Share of active listings they run", color=INK_2, fontsize=9)
    _clean_axes(ax, "both")
    top1 = largest.iloc[0]
    _titles(fig, "No host dominates, but a small tier of operators runs nearly a third of the market",
            f"{n(allm['listings'])} active listings, {n(allm['hosts'])} hosts. The largest single host runs "
            f"{top1['share_of_listings_pct']:.1f}%.", 0.935)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_councils(c: pd.DataFrame, path: Path) -> None:
    d = c.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 8.8))
    y = range(len(d))
    left = [0.0] * len(d)
    for label, col in (("10+ listings", "operator_pct"), ("2-9 listings", "two_to_nine_pct"),
                       ("1 listing", "single_host_pct")):
        ax.barh(list(y), d[col], left=left, height=0.72, color=RAMP[label], edgecolor=SURFACE, linewidth=1.2,
                label=f"Host has {label}")
        left = [a + b for a, b in zip(left, d[col])]
    for i, v in enumerate(d["operator_pct"]):
        ax.text(101.5, i, f"{v:.1f}%", va="center", ha="left", fontsize=8.6, color=INK)
    ax.text(101.5, len(d) - 0.1, "by 10+", va="bottom", ha="left", fontsize=8.6, color=INK_2)
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{lga}  ({n(k)})" for lga, k in zip(d["lga"], d["active_listings"])])
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, len(d) - 0.4)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    _clean_axes(ax, "x")
    ax.tick_params(axis="y", labelcolor=INK, labelsize=9)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.035), ncol=3, frameon=False, fontsize=9)
    mel, yr = (c.set_index("lga").loc[k, "operator_pct"] for k in ("Melbourne", "Yarra Ranges"))
    _titles(fig, f"Operators run {mel:.0f}% of the City of Melbourne's listings but {yr:.0f}% of Yarra Ranges'",
            "Share of each council's active listings, by how many active listings the host runs across all 30 "
            "councils. Active listings in brackets.", 0.952)
    fig.tight_layout(rect=(0, 0, 0.97, 0.94))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_profile(p: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3))
    x = list(range(len(p)))
    labels = [s.replace(" listings", "").replace(" listing", "") for s in p["host_size"]]
    a1, a2, a3 = axes
    a1.bar(x, p["vs_peers_pct"], color=BLUE, width=0.62)
    for i, v in enumerate(p["vs_peers_pct"]):
        a1.text(i, v + (0.25 if v >= 0 else -0.25), signed(v), ha="center", va="bottom" if v >= 0 else "top",
                fontsize=8.8, color=INK)
    a1.axhline(0, color=INK_2, linewidth=0.9)
    lim = max(abs(p["vs_peers_pct"]).max() * 1.45, 1)
    a1.set_ylim(-lim, lim)
    a1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:+.0f}%".replace("-", "−") if v else "0"))
    a1.set_title("Entire-home price against peers (median)", loc="left", fontsize=10)
    _clean_axes(a1, "y")
    a2.scatter(x, p["rating_median"], s=70, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
    for i, v in enumerate(p["rating_median"]):
        a2.text(i, v + 0.012, f"{v:.2f}", ha="center", va="bottom", fontsize=8.8, color=INK)
    lo = min(p["rating_median"].min() - 0.06, 4.7)
    a2.set_ylim(lo, 5.0)
    a2.set_title("Median guest rating (out of 5)", loc="left", fontsize=10)
    _clean_axes(a2, "y")
    a3.bar(x, p["superhost_pct"], color=BLUE, width=0.62)
    for i, v in enumerate(p["superhost_pct"]):
        a3.text(i, v + 1.2, f"{v:.0f}%", ha="center", fontsize=8.8, color=INK)
    a3.set_ylim(0, p["superhost_pct"].max() * 1.18)
    a3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    a3.set_title("Hosts who are Superhosts", loc="left", fontsize=10)
    _clean_axes(a3, "y")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_xlabel("Active listings the host runs", color=INK_2, fontsize=9)
    _titles(fig, "Host size makes little difference to price, but ratings fall a little with size",
            "Peers = active entire homes in the same council with the same bedrooms (Part 2). Ratings are per "
            "listing; Superhost status is per host.", 0.915)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, **SAVE)
    plt.close(fig)


# ---------------------------------------------------------------- report

def write_report(out: dict[str, pd.DataFrame], results: Path) -> str:
    summary, largest, curve = out["concentration_summary"], out["largest_hosts"], out["host_curve"]
    council, prof, spread = out["council_hosts"], out["host_size_profile"], out["operator_spread"]
    typical, check = out["typical_operator"], out["host_count_check"]
    allm, ent = summary.iloc[0], summary.iloc[1]
    lg = largest.set_index("largest_hosts")
    cv = curve.set_index("share_of_hosts_pct")
    cs = council.set_index("lga")
    pr = prof.set_index("band")
    ty = typical.set_index("row_no")
    ck = check.set_index("band")
    sp = spread.set_index("band")
    mel, yr = cs.loc["Melbourne"], cs.loc["Yarra Ranges"]
    yr_rank = int(council["active_listings"].rank(ascending=False, method="min")[council["lga"] == "Yarra Ranges"].iloc[0])
    top_c, bottom_c = council.iloc[0], council.iloc[-1]
    n_councils = len(council)
    over_quarter = council[council["operator_pct"] >= 25]
    owner_pool = int(council["single_host_entire_homes"].sum())
    pool = council.sort_values(["single_host_entire_homes", "lga"], ascending=[False, True]).head(5)
    pool_top5 = int(pool["single_host_entire_homes"].sum())
    max_hhi = council.loc[council["hhi"].idxmax()]
    ops_all = ty.loc[3]
    single, big = pr.loc[1], pr.loc[5]
    snap_ops = int(ck.loc[[4, 5], "hosts_by_all_listings"].sum())
    act_ops = int(ck.loc[[4, 5], "hosts_by_active_listings"].sum())
    hosts_all = int(check["hosts_by_all_listings"].sum())
    rating_steps = ", falling with every step in size" if prof["rating_median"].is_monotonic_decreasing \
        and prof["rating_median"].is_unique else ""

    check_tab = check[["host_size", "hosts_by_active_listings", "hosts_by_all_listings"]].rename(columns={
        "host_size": "Host has", "hosts_by_active_listings": "Hosts, counting active listings (used here)",
        "hosts_by_all_listings": "Hosts, counting all listings in the snapshot"})
    largest_tab = largest.rename(columns={
        "largest_hosts": "Largest hosts", "share_of_hosts_pct": "Share of hosts %",
        "active_listings": "Active listings they run", "share_of_listings_pct": "Share of active listings %",
        "share_of_entire_homes_pct": "Share of active entire homes % (ranked by entire homes)"})
    summary_tab = summary[["market", "hosts", "listings", "listings_per_host", "hhi", "equivalent_hosts",
                           "hosts_for_half", "hosts_for_half_pct", "operator_share_pct",
                           "single_listing_share_pct"]].rename(columns={
        "market": "Market", "hosts": "Hosts", "listings": "Listings", "listings_per_host": "Per host",
        "hhi": "HHI (0-10,000)", "equivalent_hosts": "Equal-sized hosts it equals", "hosts_for_half": "Hosts running half",
        "hosts_for_half_pct": "As % of hosts", "operator_share_pct": "Run by operators %",
        "single_listing_share_pct": "Run by one-listing hosts %"})
    council_tab = council[["lga", "active_listings", "hosts", "single_host_pct", "two_to_nine_pct", "operator_pct",
                           "operators_present", "operator_entire_pct", "single_host_entire_homes", "hosts_for_half",
                           "top10_share_pct", "hhi"]].rename(columns={
        "lga": "Council", "active_listings": "Active listings", "hosts": "Hosts", "single_host_pct": "1 listing %",
        "two_to_nine_pct": "2-9 %", "operator_pct": "10+ %", "operators_present": "Operators present",
        "operator_entire_pct": "Entire homes run by 10+ %", "single_host_entire_homes": "One-listing hosts' entire homes",
        "hosts_for_half": "Hosts running half", "top10_share_pct": "Top 10 hosts %", "hhi": "HHI"})
    prof_tab = prof[["host_size", "hosts", "active_listings", "share_of_listings_pct", "entire_pct",
                     "entire_price_median", "vs_peers_pct", "far_above_pct", "reviews_ltm_median", "open_30_median",
                     "rating_median", "superhost_pct", "min_28_pct", "median_councils"]].rename(columns={
        "host_size": "Host has", "hosts": "Hosts", "active_listings": "Active listings",
        "share_of_listings_pct": "Share %", "entire_pct": "Entire homes %", "entire_price_median": "Entire-home median $",
        "vs_peers_pct": "Against peers %", "far_above_pct": "50%+ above peers %",
        "reviews_ltm_median": "Reviews, 12 m", "open_30_median": "Open of next 30",
        "rating_median": "Rating", "superhost_pct": "Superhosts %", "min_28_pct": "Min. stay 28+ %",
        "median_councils": "Councils per host"})
    prof_tab["Rating"] = prof_tab["Rating"].map(lambda v: f"{v:.2f}")
    typical_tab = typical[["operators", "hosts", "median_listings", "median_councils", "only_entire_pct",
                           "one_council_mostly_pct", "any_inner3_pct", "vs_peers_pct", "superhost_pct"]].rename(columns={
        "operators": "Operators with", "hosts": "Hosts", "median_listings": "Median listings",
        "median_councils": "Median councils", "only_entire_pct": "Only entire homes %",
        "one_council_mostly_pct": "75%+ in one council %", "any_inner3_pct": "Any in the inner three %",
        "vs_peers_pct": "Price against peers %", "superhost_pct": "Superhosts %"})
    spread_tab = spread[["councils", "operators", "active_listings", "median_listings", "entire_pct",
                         "median_main_council_pct", "inner3_pct"]].rename(columns={
        "councils": "Listings spread over", "operators": "Operators", "active_listings": "Active listings",
        "median_listings": "Median listings", "entire_pct": "Entire homes %",
        "median_main_council_pct": "Median share in main council %", "inner3_pct": "In the inner three %"})

    md = f"""# Part 3: who runs the market

*Written by `scripts/hosts_report.py` from Inside Airbnb's Melbourne snapshot of {source.SNAPSHOT_DATE}. Every
number below is read from the query results. No host is named and no per-host row is published.*

## What is counted

- **A host is one Airbnb account.** A management company may run several accounts, and one account may manage
  homes for many owners, so this measures who *runs* listings, not who owns the homes.
- **A host's size is its number of active listings** (reviewed in the 12 months to the scrape; Part 1) across all
  {n_councils} councils, counted from `host_id`. **Operators** are hosts with 10 or more; a host with 12 listings
  spread across Melbourne counts as an operator in every council it is in.
- **Why the numbers differ from Inside Airbnb's own.** Its `calculated_host_listings_count` counts every listing in
  the snapshot, dormant ones included. Counted that way there are {n(snap_ops)} hosts with 10 or more listings, not
  {n(act_ops)}, and {n(hosts_all)} hosts in all, not {n(allm['hosts'])}:

{md_table(check_tab, 'lrr')}

## Across Melbourne: no dominant host, but a tier of operators

![Concentration curve](charts/09_host_concentration_curve.png)

{md_table(summary_tab, 'lrrrrrrrrr')}

{md_table(largest_tab, 'rrrrr')}

- **No single host is big.** The largest runs {n(lg.loc[1, 'active_listings'])} active listings
  ({lg.loc[1, 'share_of_listings_pct']:.1f}% of the market) and the largest 10 run {lg.loc[10, 'share_of_listings_pct']:.1f}%. The
  Herfindahl-Hirschman index (HHI, the sum of squared market shares) is {allm['hhi']:.1f} out of 10,000: as
  concentrated as a market of {n(allm['equivalent_hosts'])} equal-sized hosts.
- **But the market is not just households letting a spare home.** The largest 1% of hosts
  ({n(cv.loc[1, 'hosts'])}) run {cv.loc[1, 'share_of_listings_pct']:.1f}% of active listings, the {n(allm['operators'])}
  operators run {allm['operator_share_pct']:.1f}% (and {ent['operator_share_pct']:.1f}% of entire homes), and
  {n(allm['hosts_for_half'])} hosts ({allm['hosts_for_half_pct']:.1f}% of them) run half. The other half is spread
  over {n(allm['hosts'] - allm['hosts_for_half'])} hosts, {n(pr.loc[1, 'hosts'])} of whom have a single listing.

**So what:** anyone who needs to reach short-stay hosts (a council enforcing local rules, a platform, a cleaning or
linen supplier selling to them) can cover nearly a third of the market through {n(allm['operators'])}
accounts, but no single operator sets prices or supply. The other two-thirds can only be reached one host at a time.

## Council by council

![Host mix by council](charts/10_council_host_mix.png)

The mix differs far more between councils than the market-wide figures suggest:

- **{place(top_c['lga'])[0].upper() + place(top_c['lga'])[1:]}** has the highest operator share: operators run {top_c['operator_pct']:.1f}% of its
  {n(top_c['active_listings'])} active listings ({top_c['operator_entire_pct']:.1f}% of its entire homes), and
  {n(top_c['operators_present'])} of the {n(allm['operators'])} operators have a listing there. {n(top_c['hosts_for_half'])}
  hosts run half of its listings. Only {top_c['single_host_pct']:.1f}% belong to a host with no other listing.
- **{len(over_quarter)} of the {n_councils} councils** have a quarter or more of their listings run by operators.
- **Yarra Ranges**, the {ordinal(yr_rank)} largest council by listings, is the opposite: operators run {yr['operator_pct']:.1f}%,
  and hosts with fewer than 10 listings {yr['single_host_pct'] + yr['two_to_nine_pct']:.1f}%. The lowest operator share is in
  {place(bottom_c['lga'])} ({bottom_c['operator_pct']:.1f}% of {n(bottom_c['active_listings'])} listings).
- **No council has a dominant host either.** The highest council HHI is {max_hhi['hhi']:.0f} out of 10,000
  ({max_hhi['lga']}, {n(max_hhi['active_listings'])} listings). In small councils the top 10 hosts naturally hold a
  bigger share, so the top-10 column is best compared between councils of similar size.

{md_table(council_tab, 'lrrrrrrrrrrr')}

Sorted by the 10+ column. Host size is counted across all {n_councils} councils.

**So what:** in the City of Melbourne, short-stay supply is largely a professional business, so rules on
registration, building by-laws or caps would mostly land on a few hundred operators. In outer and hills councils
supply is mostly hosts with one or a few listings, where the same rules reach many more people per listing.
A council housing team should read its own row, not the Melbourne-wide average.

### The one-listing owner market

For a property manager, the entire homes run by a host with no other active listing are the obvious clients:
there are {n(owner_pool)} across the {n_councils} councils, and {n(pool_top5)} of them are in five councils:
{', '.join(f"{r.lga} ({n(r.single_host_entire_homes)})" for r in pool.itertuples())}.
Relative to size, the pool is much bigger outside the City of Melbourne: one-listing hosts run
{100 * yr['single_host_entire_homes'] / yr['entire_homes']:.1f}% of Yarra Ranges' entire homes against
{100 * mel['single_host_entire_homes'] / mel['entire_homes']:.1f}% of the City of Melbourne's, where operators
already run {mel['operator_entire_pct']:.1f}%.

## Operators against everyone else

![Host size profile](charts/11_host_size_profile.png)

{md_table(prof_tab, 'lrrrrrrrrrrrrr')}

Price against peers uses Part 2's comparison (priced active entire homes against the median for the same council
and bedrooms); "Open of next 30" is for the same homes.

- **Operators run entire homes:** {pr.loc[4, 'entire_pct']:.1f}% of listings for hosts with 10-49 and
  {big['entire_pct']:.1f}% for 50+, against {single['entire_pct']:.1f}% for one-listing hosts.
- **Size makes little difference to price.** Size for size, every group's median is within
  {math.ceil(abs(prof['vs_peers_pct']).max())}% of its peers: one-listing hosts quote {signed(single['vs_peers_pct'])} and hosts
  with 50+ listings {signed(big['vs_peers_pct'])}. About one home in ten sits 50% or more
  above its peers in every group ({prof['far_above_pct'].min():.1f}% to {prof['far_above_pct'].max():.1f}%).
- **Demand looks much the same.** Median reviews in the year range from {prof['reviews_ltm_median'].min():g} to
  {prof['reviews_ltm_median'].max():g} across the five groups ({single['reviews_ltm_median']:g} for one-listing hosts,
  {big['reviews_ltm_median']:g} for 50+), and median open nights in the next 30 days from
  {prof['open_30_median'].min():g} to {prof['open_30_median'].max():g}.
- **Guests rate them a little lower.** The median rating falls from {single['rating_median']:.2f} for one-listing hosts
  to {big['rating_median']:.2f} for 50+{rating_steps}. {single['superhost_pct']:.1f}% of one-listing
  hosts are Superhosts against {big['superhost_pct']:.1f}% of hosts with 50+ listings; hosts with 2-4 listings are the most
  likely ({pr.loc[2, 'superhost_pct']:.1f}%).
- **Long-stay-only listings are rare in every group** ({prof['min_28_pct'].min():.1f}% to
  {prof['min_28_pct'].max():.1f}% need 28 nights or more), so minimum stays do not set operators apart.

**So what:** scale does not seem to buy pricing power or more bookings here, and it comes with slightly lower
guest ratings. A manager growing a portfolio should watch ratings, and an owner choosing a manager can ask to see
them.

## The typical operator

{md_table(typical_tab, 'lrrrrrrrr')}

{md_table(spread_tab, 'lrrrrrr')}

The median operator runs {ops_all['median_listings']:g} active listings across {ops_all['median_councils']:g} councils;
{ops_all['only_entire_pct']:.1f}% run nothing but entire homes, and {ops_all['any_inner3_pct']:.1f}% have at least one
listing in the City of Melbourne, Port Phillip or Yarra. {ops_all['one_council_mostly_pct']:.1f}% keep three-quarters or
more of their listings in one council. {n(sp.loc[1, 'operators'])} operators are in a single council
({sp.loc[1, 'inner3_pct']:.1f}% of their listings in the inner three), while {n(sp.loc[4, 'operators'])} spread over
10 or more councils, with a median {sp.loc[4, 'median_listings']:g} listings each. Across operators, the median of
their homes' price against peers is {signed(ops_all['vs_peers_pct'])}.

**So what:** the typical operator is an entire-home business of one or two dozen listings with a foot in the inner
city, often reaching into other councils. That is the competitor a new property manager meets there.

## Limits

- Accounts are not companies or owners: one business may use several accounts, and a manager's account mixes
  homes from many owners. Concentration by owner cannot be measured from this data.
- Host size counts active listings only. A host's dormant or unreviewed listings, and listings outside the 30
  councils in this snapshot, are not counted.
- `host_since` is empty in this snapshot (Part 1), so how long hosts have operated cannot be analysed.
- Ratings cluster near 5, so small differences in the median are real differences in the data but small ones.
- Price comparisons use one quoted stay per listing (Part 2's limits apply).
"""
    (results / "HOSTS.md").write_text(md)
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", type=Path, default=source.RESULTS, help="folder to write to (default results/)")
    args = ap.parse_args()
    results: Path = args.results
    (results / "charts").mkdir(parents=True, exist_ok=True)
    con = P.connect()
    H.prepare(con)
    out = H.run_all(con)
    for name, df in out.items():
        df.to_csv(results / f"{name}.csv", index=False)
    chart_curve(out["host_curve"], out["concentration_summary"], out["largest_hosts"],
                results / "charts" / "09_host_concentration_curve.png")
    chart_councils(out["council_hosts"], results / "charts" / "10_council_host_mix.png")
    chart_profile(out["host_size_profile"], results / "charts" / "11_host_size_profile.png")
    write_report(out, results)
    print(f"wrote {results / 'HOSTS.md'}, {len(out)} CSVs and 3 charts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
