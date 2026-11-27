"""Load the raw Inside Airbnb files into a local DuckDB database (data/str_melbourne.duckdb, gitignored).

Only the columns the analysis uses are kept. Host names, profile text,
listing descriptions, photos and URLs are dropped at load: nothing in this
project needs them, and no result names a host.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from str_market import source

LISTING_COLUMNS = """
    CAST(id AS BIGINT)                                   AS listing_id,
    CAST(host_id AS BIGINT)                              AS host_id,
    COALESCE(NULLIF(source, ''), 'city scrape')          AS scrape_source,
    CAST(last_scraped AS DATE)                           AS last_scraped,
    neighbourhood_cleansed                               AS lga,
    CAST(latitude AS DOUBLE)                             AS latitude,
    CAST(longitude AS DOUBLE)                            AS longitude,
    property_type,
    room_type,
    CAST(accommodates AS INTEGER)                        AS accommodates,
    CAST(bedrooms AS INTEGER)                            AS bedrooms,
    CAST(beds AS INTEGER)                                AS beds,
    bathrooms_text,
    CAST(price AS VARCHAR)                               AS price_text,
    TRY_CAST(replace(replace(CAST(price AS VARCHAR), '$', ''), ',', '') AS DOUBLE) AS price,
    CAST(price_quote_checkin_date AS DATE)               AS quote_checkin,
    CAST(price_quote_checkout_date AS DATE)              AS quote_checkout,
    CAST(price_quote_total_price AS DOUBLE)              AS quote_total,
    CAST(price_quote_price_per_night AS DOUBLE)          AS quote_per_night,
    CAST(minimum_nights AS INTEGER)                      AS minimum_nights,
    CAST(maximum_nights AS INTEGER)                      AS maximum_nights,
    CAST(has_availability AS BOOLEAN)                    AS has_availability,
    CAST(availability_30 AS INTEGER)                     AS availability_30,
    CAST(availability_90 AS INTEGER)                     AS availability_90,
    CAST(availability_365 AS INTEGER)                    AS availability_365,
    CAST(number_of_reviews AS INTEGER)                   AS number_of_reviews,
    CAST(number_of_reviews_ltm AS INTEGER)               AS number_of_reviews_ltm,
    CAST(first_review AS DATE)                           AS first_review,
    CAST(last_review AS DATE)                            AS last_review,
    CAST(review_scores_rating AS DOUBLE)                 AS review_scores_rating,
    CAST(estimated_occupancy_l365d AS INTEGER)           AS estimated_occupancy_l365d,
    CAST(estimated_revenue_l365d AS DOUBLE)              AS estimated_revenue_l365d,
    CAST(calculated_host_listings_count AS INTEGER)      AS host_listings_in_snapshot,
    CAST(host_since AS DATE)                             AS host_since,
    CAST(host_is_superhost AS BOOLEAN)                   AS host_is_superhost,
    CAST(instant_bookable AS VARCHAR) = 't'              AS instant_bookable,
    CAST(license AS VARCHAR)                             AS licence
"""


def lga_names(geojson_path: Path) -> list[str]:
    features = json.loads(geojson_path.read_text())["features"]
    return sorted({f["properties"]["neighbourhood"] for f in features})


def build(raw_dir: Path = source.RAW_DIR, db_path: Path = source.DB_PATH) -> dict:
    """(Re)build the database from the raw files; return the row counts."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        con.execute(f"""
            CREATE TABLE listings AS
            SELECT {LISTING_COLUMNS}
            FROM read_csv('{raw_dir / 'listings.csv.gz'}', header = true, all_varchar = true)
        """)
        con.execute(f"""
            CREATE TABLE calendar AS
            SELECT CAST(listing_id AS BIGINT) AS listing_id, CAST(date AS DATE) AS date,
                   CAST(available AS VARCHAR) = 't' AS available,
                   CAST(minimum_nights AS INTEGER) AS minimum_nights,
                   CAST(maximum_nights AS INTEGER) AS maximum_nights
            FROM read_csv('{raw_dir / 'calendar.csv.gz'}', header = true, all_varchar = true)
        """)
        con.execute(f"""
            CREATE TABLE reviews AS
            SELECT CAST(listing_id AS BIGINT) AS listing_id, CAST(date AS DATE) AS date
            FROM read_csv('{raw_dir / 'reviews.csv'}', header = true, all_varchar = true)
        """)
        con.execute("CREATE TABLE lgas (lga VARCHAR)")
        con.executemany("INSERT INTO lgas VALUES (?)", [[n] for n in lga_names(raw_dir / "neighbourhoods.geojson")])
        return {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("listings", "calendar", "reviews", "lgas")}
    finally:
        con.close()
