"""Where the data comes from, and the pinned hashes of the files the analysis uses.

Inside Airbnb (https://insideairbnb.com/get-the-data/) publishes a quarterly
snapshot of Airbnb listings for Melbourne under CC BY 4.0. Its community
guidelines (https://insideairbnb.com/data-policies/) ask users to take only
the data they need, to download it once rather than on every run, and not to
republish it. So this repo commits no listing-level data: the four raw files
are downloaded once into data/raw/ (gitignored) and only aggregated results
are committed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "str_melbourne.duckdb"
MANIFEST_PATH = ROOT / "data" / "SNAPSHOT.json"
RESULTS = ROOT / "results"

SNAPSHOT_DATE = "2026-09-16"          # the date Inside Airbnb gives this Melbourne snapshot
BASE_URL = f"https://data.insideairbnb.com/australia/vic/melbourne/{SNAPSHOT_DATE}"
LICENCE = "CC BY 4.0 (Inside Airbnb, https://insideairbnb.com/get-the-data/)"
CITATION = (f"Inside Airbnb. (2026). Melbourne Airbnb listings data, September 2026 "
            f"(snapshot {SNAPSHOT_DATE}) [Data set]. https://insideairbnb.com/get-the-data/")

# Only the files the analysis needs. The 103 MB detailed reviews file (review
# text and reviewer names) is not taken: the 26 MB summary file has the
# listing id and date of every review, which is all that is used.
FILES = {
    "listings.csv.gz": {
        "url": f"{BASE_URL}/data/listings.csv.gz",
        "bytes": 15_409_076,
        "sha256": "7d09b7124bfc26bdb5c8a2a66efe0b9a48e4e1d7cc2e11242e9d52ee3f17985b",
        "what": "one row per listing: host, location, room type, price, minimum nights, availability, review counts",
    },
    "calendar.csv.gz": {
        "url": f"{BASE_URL}/data/calendar.csv.gz",
        "bytes": 22_480_256,
        "sha256": "381b22a8ca006682290428faa5ebcd4320bb767effcd30eb91670a372b177f86",
        "what": "one row per listing per day for the next 365 days: available or not, minimum and maximum nights",
    },
    "reviews.csv": {
        "url": f"{BASE_URL}/visualisations/reviews.csv",
        "bytes": 25_561_868,
        "sha256": "5f4af269fb60185294fc8378a676e0378a3e6303f8a167360427a2ca9fef649c",
        "what": "one row per review: listing id and date only",
    },
    "neighbourhoods.geojson": {
        "url": f"{BASE_URL}/visualisations/neighbourhoods.geojson",
        "bytes": 3_013_242,
        "sha256": "60651f3d4de4a573a2b3402706d6da31aeecb8befe9d008a27cfbf6e63df23cf",
        "what": "boundaries of the 30 councils (LGAs) Inside Airbnb assigns listings to",
    },
}


def raw_path(name: str) -> Path:
    return RAW_DIR / name


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
