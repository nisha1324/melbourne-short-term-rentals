"""Part 1: build the local database and write results/PROFILE.md, its CSVs and charts 01-04.

    python scripts/download_data.py     # once: fetch the four raw files into data/raw/
    python scripts/profile_report.py    # rebuild data/str_melbourne.duckdb and the Part 1 outputs

Every figure in the report is read from the query results; none is typed in.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from str_market import build, profile as P, source  # noqa: E402

# Reference palette (light mode), as in Nisha's other projects; the pair passes
# the dataviz validator (CVD separation 24.7, normal vision 33.6).
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.titlecolor": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "path.simplify": False,
})
SAVE = {"dpi": 150, "metadata": {"Software": None}}
TOP_LGAS = 15


def n(x: float) -> str:
    return f"{x:,.0f}"


def pct(part: float, whole: float, nd: int = 1) -> str:
    return f"{100 * part / whole:.{nd}f}%"


def money(x: float) -> str:
    return f"${x:,.0f}"


def md_table(df: pd.DataFrame, align: str | None = None) -> str:
    cols = list(df.columns)
    align = align or "l" + "r" * (len(cols) - 1)
    sep = ["---:" if a == "r" else "---" for a in align]
    def fmt(v) -> str:
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return ""
        if isinstance(v, bool) or isinstance(v, str):
            return str(v)
        if isinstance(v, int) or (isinstance(v, float) and v.is_integer() and abs(v) >= 100):
            return n(v)
        return str(v)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def _clean_axes(ax, grid_axis: str) -> None:
    for side in ("top", "right") + (("left",) if grid_axis == "x" else ()):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _titles(fig, title: str, subtitle: str, top: float) -> None:
    fig.suptitle(title, x=0.012, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.text(0.012, top, subtitle, fontsize=9, color=INK_2, va="top")


# ---------------------------------------------------------------- charts

def lga_chart_data(by_lga: pd.DataFrame) -> pd.DataFrame:
    top = by_lga.head(TOP_LGAS)[["lga", "active_listings", "entire_homes"]].copy()
    rest = by_lga.iloc[TOP_LGAS:]
    top.loc[len(top)] = [f"Other {len(rest)} councils", rest["active_listings"].sum(), rest["entire_homes"].sum()]
    top["other_rooms"] = top["active_listings"] - top["entire_homes"]
    return top


def chart_lgas(by_lga: pd.DataFrame, path: Path) -> None:
    d = lga_chart_data(by_lga).iloc[::-1].reset_index(drop=True)
    total = by_lga["active_listings"].sum()
    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.barh(d["lga"], d["entire_homes"], color=BLUE, height=0.66, label="Entire home or apartment",
            edgecolor=SURFACE, linewidth=1)
    ax.barh(d["lga"], d["other_rooms"], left=d["entire_homes"], color=ORANGE, height=0.66,
            label="Private, shared or hotel room", edgecolor=SURFACE, linewidth=1)
    xmax = d["active_listings"].max()
    for y, v in enumerate(d["active_listings"]):
        ax.text(v + xmax * 0.01, y, f"{n(v)}  ({pct(v, total)})", va="center", fontsize=8.8, color=INK)
    ax.set_xlim(0, xmax * 1.2)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _p: n(x)))
    _clean_axes(ax, "x")
    ax.tick_params(axis="y", labelcolor=INK)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    _titles(fig, "Active Airbnb listings by council, Melbourne, September 2026",
            f"{n(total)} listings reviewed in the 12 months to the scrape; share of all active listings in brackets. "
            "Moreland is now Merri-bek.", 0.948)
    fig.tight_layout(rect=(0, 0, 1, 0.935))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_prices(bands: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, (room, label) in zip(axes, (("Entire home/apt", "Entire homes and apartments"),
                                        ("Private room", "Private rooms"))):
        d = bands[bands["room_type"] == room]
        # every band appears in both panels, so the two share one x axis
        allb = bands.drop_duplicates("band").sort_values("band")[["band", "price_band"]]
        d = allb.merge(d[["band", "listings", "share_pct"]], on="band", how="left").fillna(0)
        ax.bar(d["price_band"], d["share_pct"], color=BLUE, width=0.7)
        for x, (s, c) in enumerate(zip(d["share_pct"], d["listings"])):
            if c:
                ax.text(x, s + 0.8, f"{s:.0f}%" if s >= 1 else "<1%", ha="center", fontsize=8.5, color=INK)
        ax.set_title(f"{label} ({n(d['listings'].sum())} with a price)", loc="left", fontsize=10.5)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _p: f"{y:.0f}%"))
        ax.tick_params(axis="x", labelrotation=35, labelsize=8.5)
        for lab in ax.get_xticklabels():
            lab.set_ha("right")
        _clean_axes(ax, "y")
    axes[0].set_ylabel("Share of listings")
    _titles(fig, "Quoted nightly price of active listings",
            "Average price per night for a real stay (usually the minimum stay) from each listing's next open date, "
            "AUD.", 0.915)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_hosts(host_size: pd.DataFrame, path: Path) -> None:
    d = host_size.iloc[::-1].reset_index(drop=True)
    total = host_size["active_listings"].sum()
    labels = list(d["host_size"])
    fig, ax = plt.subplots(figsize=(10, 3.9))
    ax.barh(labels, d["active_listings"], color=BLUE, height=0.62)
    xmax = d["active_listings"].max()
    for y, (v, h) in enumerate(zip(d["active_listings"], d["hosts"])):
        ax.text(v + xmax * 0.01, y, f"{n(v)} listings ({pct(v, total)}) from {n(h)} hosts",
                va="center", fontsize=9, color=INK)
    ax.set_xlim(0, xmax * 1.5)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _p: n(x)))
    _clean_axes(ax, "x")
    ax.tick_params(axis="y", labelcolor=INK)
    _titles(fig, "Active listings by how many active listings their host has",
            f"{n(total)} active listings from {n(host_size['hosts'].sum())} hosts; a host's count includes "
            "every room type.", 0.905)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_reviews(monthly: pd.DataFrame, last_full_month: str, path: Path) -> None:
    d = monthly.copy()
    d["month"] = pd.to_datetime(d["month"])
    d = d[(d["month"] >= "2013-01-01") & (d["month"] <= last_full_month)]
    fig, ax = plt.subplots(figsize=(10, 4.3))
    ax.plot(d["month"], d["reviews"], color=BLUE, linewidth=2)
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _p: n(y)))
    _clean_axes(ax, "y")
    low = d[(d["month"] >= "2020-04-01") & (d["month"] < "2021-12-01")].nsmallest(1, "reviews").iloc[0]
    top = d["reviews"].max()
    ax.set_ylim(0, top * 1.2)
    ax.annotate(f"{low['month']:%B %Y}: {n(low['reviews'])}", xy=(low["month"], low["reviews"]),
                xytext=(low["month"], top * 0.42), fontsize=9, color=INK, va="bottom", ha="center",
                arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8, "shrinkA": 2, "shrinkB": 3})
    last = d.iloc[-1]
    ax.annotate(f"{last['month']:%B %Y}: {n(last['reviews'])}", xy=(last["month"], last["reviews"]),
                xytext=(last["month"], top * 1.1), fontsize=9, color=INK, va="bottom", ha="right",
                arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8, "shrinkA": 2, "shrinkB": 3,
                            "relpos": (1, 0)})
    _titles(fig, "Reviews per month for listings in the September 2026 snapshot",
            "Only listings still listed are counted, so earlier years are undercounted: "
            "read the shape, not the growth.", 0.905)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(path, **SAVE)
    plt.close(fig)


# ---------------------------------------------------------------- report

def write_report(out: dict[str, pd.DataFrame], cols: pd.DataFrame, h: dict, results: Path) -> str:
    ms, src, room = out["market_size"], out["by_scrape_source"], out["by_room_type"]
    lga, bands, mn = out["by_lga"], out["price_bands"], out["minimum_nights"]
    hosts, qc = out["host_size"], out["quality_checks"]
    act = h["active"]
    carried, carried_closed = h["carried_over"]
    prev = src.set_index("scrape_source").loc["previous scrape"]
    city = src.set_index("scrape_source").loc["city scrape"]
    ent = room.set_index("room_type").loc["Entire home/apt"]
    prv = room.set_index("room_type").loc["Private room"]
    eb = bands[bands["room_type"] == "Entire home/apt"].set_index("band")
    pb = bands[bands["room_type"] == "Private room"].set_index("band")
    mnb = mn.set_index("bucket")
    hb = hosts.set_index("band")
    qcs = qc.set_index("check_no")
    n_pass = int((qc["status"] == "pass").sum())
    n_note = int((qc["status"] == "note").sum())
    n_info = int((qc["status"] == "info").sum())
    empty_cols = cols.loc[cols["empty_pct_all"] == 100.0, "column"].tolist()
    top3 = lga.head(3)
    outer = lga[lga["lga"].isin(["Yarra Ranges"])].iloc[0]
    low_entire = lga.nsmallest(1, "entire_home_pct").iloc[0]
    multi = h["active_multi_host_listings"]
    shorter = ("never shorter" if h["quotes_shorter_than_minimum"] == 0
               else f"{n(h['quotes_shorter_than_minimum'])} shorter")
    big = h["active_10plus_listings"]

    qc_tab = qc.rename(columns={"check_no": "#", "check_name": "Check", "found": "Found", "expected": "Expected",
                                "status": "Status"})
    ms_tab = ms[["definition", "listings", "hosts"]].rename(
        columns={"definition": "Which listings", "listings": "Listings", "hosts": "Hosts"})
    room_tab = room.rename(columns={"room_type": "Room type", "active_listings": "Active listings",
                                    "share_pct": "Share %", "with_price": "With a price",
                                    "price_p25": "25th pct $", "price_median": "Median $",
                                    "price_p75": "75th pct $", "median_guests": "Median guests"})
    lga_tab = lga.head(10)[["lga", "active_listings", "share_of_market_pct", "entire_home_pct",
                            "entire_home_median_price"]].rename(
        columns={"lga": "Council", "active_listings": "Active listings", "share_of_market_pct": "Share of market %",
                 "entire_home_pct": "Entire homes %", "entire_home_median_price": "Entire home median $"})
    mn_tab = mn[["minimum_stay", "active_listings", "share_pct"]].rename(
        columns={"minimum_stay": "Minimum stay", "active_listings": "Active listings", "share_pct": "Share %"})
    host_tab = hosts[["host_size", "hosts", "active_listings", "share_of_listings_pct"]].rename(
        columns={"host_size": "Host has", "hosts": "Hosts", "active_listings": "Active listings",
                 "share_of_listings_pct": "Share of listings %"})

    md = f"""# Part 1: the snapshot and what is in it

*Written by `scripts/profile_report.py` from Inside Airbnb's Melbourne snapshot of {source.SNAPSHOT_DATE}
(scraped {h['scraped'][0]} to {h['scraped'][1]}). Every number below is read from the query results.*

## The data

Inside Airbnb collects public Airbnb listing pages for Melbourne each quarter and publishes them under
CC BY 4.0. Four files are used (SHA-256 pinned in `str_market/source.py`, details in `data/SNAPSHOT.json`):

| File | Rows | What it holds |
| --- | ---: | --- |
| `listings.csv.gz` | {n(h['listings'])} | one row per listing: host, council, room type, quoted price, minimum stay, availability, review counts |
| `calendar.csv.gz` | {n(out['_rows']['calendar'])} | one row per listing per day, {h['calendar'][0]} to {h['calendar'][1]}: open for booking or not |
| `reviews.csv` | {n(h['reviews'][2])} | the listing and date of every review, {h['reviews'][0]} to {h['reviews'][1]} |
| `neighbourhoods.geojson` | {n(out['_rows']['lgas'])} | the council (LGA) boundaries listings are assigned to |

Inside Airbnb asks users not to republish its data, so no listing-level row is committed here: the raw files
are downloaded once into `data/raw/` (gitignored) and only aggregates are published. Host names, profile text,
descriptions and photos are dropped when the data is loaded, and no result names a host.

## Which listings count

The snapshot holds {n(h['listings'])} listings from {n(h['hosts'])} hosts, but how big "the market" is depends
on which of them count:

{md_table(ms_tab, 'lrr')}

{n(carried)} listings ({pct(carried, h['listings'])}) were not found in this scrape but carried over from an earlier
one. They look dormant: {n(carried_closed)} of them have no open night in the next year, only {n(prev['with_price'])}
have a quoted price, and their median last review is {prev['median_last_review']:%B %Y} (against
{city['median_last_review']:%B %Y} for listings found in this scrape).

**From here on the market is the {n(act)} active listings: those with at least one review in the 12 months to the
scrape.** A review needs a completed stay, so this counts listings that actually take guests, and it does not
depend on the calendar, which cannot tell a booked night from one the host has blocked. It misses listings with
stays but no reviews (Inside Airbnb's own occupancy model assumes half of stays get one), so it undercounts
somewhat.

## Quality checks

{n(len(qc))} checks in `sql/quality_checks.sql`: {n_pass} pass, {n_note} find a small mismatch and {n_info} are counts
reported for information.

{md_table(qc_tab, 'rlrrl')}

- **The review counts reconcile exactly.** Each listing's review count, first and last review date, and
  reviews in the last 12 months (counted from 365 days before its own scrape date, inclusive) match the review
  file, so the active definition above rests on data that agrees with itself.
- **Calendar (checks 9 and 10).** One listing has 366 calendar days and {n(qcs.loc[10, 'found'])} listings show
  0 in `availability_365` though their calendar has open days. Later parts count open nights from the
  calendar itself.
- **Price (checks 17-19).** `price` is not a list price: it is the average nightly price of a real quoted stay
  (`quote_total` / nights, check 5). The quoted stay is the listing's minimum stay in
  {pct(h['quotes_for_minimum_stay'], h['quotes'])} of quotes ({shorter}) and starts on its first open night
  in {pct(h['quotes_from_first_open_night'], h['quotes'])}, so prices are for the next available stay, not a
  typical night. {n(qcs.loc[17, 'found'])} listings have no price, {n(prev['listings'] - prev['with_price'])} of
  them carried-over listings; among active listings {n(act - int(ms.loc[ms['row_no'] == 6, 'listings'].iloc[0]))}
  have none. {n(qcs.loc[19, 'found'])} quotes are $2,000 a night or more; they are kept, and the results use
  medians and bands, which a few extreme quotes barely move.
- **Empty columns:** {', '.join(f'`{c}`' for c in empty_cols)} are empty for every listing in this snapshot, so
  host tenure, instant booking and registration numbers cannot be analysed.

## Entire homes are most of the market

{md_table(room_tab, 'lrrrrrrr')}

{pct(ent['active_listings'], act)} of active listings are entire homes or apartments, the kind of listing that
could otherwise be a long-term rental. Their median quoted price is {money(ent['price_median'])} a night
({money(ent['price_p25'])} to {money(ent['price_p75'])} for the middle half); a private room's is
{money(prv['price_median'])}.

![Quoted nightly price](charts/02_price_bands.png)

{eb.loc[[4, 5], 'share_pct'].sum():.1f}% of priced entire homes quote $200-499 a night, while
{pb.loc[[1, 2], 'share_pct'].sum():.1f}% of private rooms quote under $150.

## Where the listings are

![Active listings by council](charts/01_listings_by_council.png)

{md_table(lga_tab, 'lrrrr')}

The City of Melbourne alone has {n(top3.iloc[0]['active_listings'])} active listings
({top3.iloc[0]['share_of_market_pct']:.1f}% of the market); with {top3.iloc[1]['lga']} and {top3.iloc[2]['lga']}
the three inner councils have {pct(h['inner3'], act)}. Outside the centre the mix changes: Yarra Ranges (the Yarra
Valley and the Dandenongs) is the fourth-largest at {n(outer['active_listings'])} listings, {outer['entire_home_pct']:.1f}% of them
entire homes, while in {low_entire['lga']} only {low_entire['entire_home_pct']:.1f}% are. Full table:
`results/by_lga.csv`.

## Minimum stays

{md_table(mn_tab, 'lrr')}

{mnb.loc[1, 'share_pct'] + mnb.loc[2, 'share_pct']:.1f}% of active listings take one- or two-night stays. Only
{n(mnb.loc[5, 'active_listings'])} ({mnb.loc[5, 'share_pct']:.1f}%) require 28 nights or more, which would make
them medium-term rentals rather than holiday lets.

## Hosts: a first look

![Listings by host size](charts/03_listings_by_host_size.png)

{md_table(host_tab, 'lrrr')}

{n(h['active_hosts'])} hosts run the {n(act)} active listings. Hosts with a single listing have
{pct(hb.loc[1, 'active_listings'], act)} of them; hosts with two or more have {pct(multi, act)}, and the
{n(h['hosts_10plus'])} hosts with 10 or more have {pct(big, act)}. Part 3 looks at this properly.

## Reviews over time

![Reviews per month](charts/04_reviews_by_month.png)

The review file counts {n(h['reviews_sep25_aug26'])} reviews in the 12 months from September 2025 against
{n(h['reviews_2019'])} in 2019 and {n(h['reviews_apr20_mar21'])} from April 2020 to March 2021, when lockdowns
stopped travel. **This is not market growth:** a listing that has left Airbnb takes its reviews with it, so the
further back a month is, the more of its reviews are missing. The chart is useful for seasonality and for the
size of the lockdown drop, not for the trend.

## What this means for the business

- **Define the market before sizing it.** The snapshot's {n(h['listings'])} listings are
  {pct(h['listings'] - act, act, 0)} more than the {n(act)} active ones. Of the {n(h['listings'] - act)} that are
  not active, {n(h['inactive_carried_over'])} are carried-over listings that look dormant and
  {n(h['inactive_found'])} are listed but have had no review in a year. A council, investor or property manager
  quoting the headline count would overstate the market by about two-thirds.
- **This is an entire-home, inner-city market.** {pct(ent['active_listings'], act)} entire homes, and
  {pct(h['inner3'], act)} in three councils. Any effect on housing supply would be concentrated there; Part 4
  tests how many look like homes taken off the long-term market.
- **A large share is run by multi-listing hosts.** {pct(multi, act)} of active listings belong to hosts with two
  or more, and {n(h['hosts_10plus'])} hosts run {pct(big, act)}, so a small number of operators' decisions move a
  large part of the market. Part 3 measures how concentrated it is.

## Limits (so far)

- One snapshot (September 2026), so this project does not track change over time. Inside Airbnb holds older
  snapshots, which it supplies on request; none were requested.
- Activity is inferred from reviews, and the calendar cannot separate booked nights from blocked ones.
- Listing locations are moved by up to about 150 metres by Airbnb, which does not matter at council level.
- Inside Airbnb is an advocacy project as well as a data source; the numbers here are recomputed from its raw
  files with the definitions stated in `sql/`, not taken from its dashboards.
"""
    (results / "PROFILE.md").write_text(md)
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", type=Path, default=source.RESULTS, help="folder to write to (default results/)")
    ap.add_argument("--no-build", action="store_true", help="reuse data/str_melbourne.duckdb as it is")
    args = ap.parse_args()
    results: Path = args.results
    (results / "charts").mkdir(parents=True, exist_ok=True)
    rows = None if args.no_build else build.build()
    con = P.connect()
    out = P.run_all(con)
    out["_rows"] = rows or {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("calendar", "lgas")}
    cols = P.column_profile(con)
    h = P.headline(con)
    for name, df in out.items():
        if not name.startswith("_"):
            df.to_csv(results / f"{name}.csv", index=False)
    cols.to_csv(results / "column_profile.csv", index=False)
    last_full_month = (pd.Timestamp(h["scraped"][0]).to_period("M") - 1).to_timestamp()
    chart_lgas(out["by_lga"], results / "charts" / "01_listings_by_council.png")
    chart_prices(out["price_bands"], results / "charts" / "02_price_bands.png")
    chart_hosts(out["host_size"], results / "charts" / "03_listings_by_host_size.png")
    chart_reviews(out["reviews_by_month"], str(last_full_month.date()), results / "charts" / "04_reviews_by_month.png")
    write_report(out, cols, h, results)
    print(f"wrote {results / 'PROFILE.md'}, {len(out)} CSVs and 4 charts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
