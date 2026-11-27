"""Download the Inside Airbnb Melbourne snapshot once, and check it against the pinned hashes.

    python scripts/download_data.py            # download any missing file, then check all four
    python scripts/download_data.py --check    # check only; never touches the network

A file that is already in data/raw/ with the pinned hash is never downloaded
again (Inside Airbnb asks users to download the data once, not on every run).
The snapshot URL is dated, so the same files should come back on a later day;
if Inside Airbnb ever replaces or removes them, the check fails rather than
silently analysing different data.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from str_market import source  # noqa: E402

USER_AGENT = "Mozilla/5.0 (compatible; portfolio data analysis; one-off download)"


def download(url: str, dest: Path, timeout: int = 300) -> dict:
    """Stream url to dest via a .part file; return the HTTP metadata."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(part, "wb") as out:
        meta = {"last_modified": resp.headers.get("Last-Modified"),
                "content_length": int(resp.headers.get("Content-Length") or 0)}
        shutil.copyfileobj(resp, out, length=1 << 20)
    size = part.stat().st_size
    if meta["content_length"] and size != meta["content_length"]:
        part.unlink()
        raise OSError(f"download incomplete: {size:,} of {meta['content_length']:,} bytes")
    part.replace(dest)
    return meta


def head_last_modified(url: str) -> str | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.headers.get("Last-Modified")


def check() -> bool:
    ok = True
    for name, spec in source.FILES.items():
        path = source.raw_path(name)
        if not path.exists():
            print(f"MISSING   {name} (run without --check to download it)", file=sys.stderr)
            ok = False
            continue
        digest = source.sha256_file(path)
        if digest != spec["sha256"]:
            print(f"MISMATCH  {name}: pinned {spec['sha256'][:12]}…, file {digest[:12]}…", file=sys.stderr)
            ok = False
        else:
            print(f"ok  {name}  {path.stat().st_size:,} bytes")
    return ok


def fetch_missing() -> None:
    manifest = json.loads(source.MANIFEST_PATH.read_text()) if source.MANIFEST_PATH.exists() else {}
    files = manifest.setdefault("files", {})
    for name, spec in source.FILES.items():
        path = source.raw_path(name)
        if path.exists() and source.sha256_file(path) == spec["sha256"]:
            if name not in files:   # fetched by hand earlier: record it, with a HEAD request for the date
                files[name] = {"url": spec["url"], "bytes": path.stat().st_size, "sha256": spec["sha256"],
                               "last_modified": head_last_modified(spec["url"]),
                               "downloaded_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                               .strftime("%Y-%m-%dT%H:%M:%SZ")}
            continue
        print(f"downloading {spec['url']} …")
        meta = download(spec["url"], path)
        files[name] = {"url": spec["url"], "bytes": path.stat().st_size, "sha256": source.sha256_file(path),
                       "last_modified": meta["last_modified"],
                       "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    out = {"source": "Inside Airbnb, Melbourne, Victoria, Australia", "snapshot": source.SNAPSHOT_DATE,
           "licence": source.LICENCE, "citation": source.CITATION,
           "files": {k: files[k] for k in source.FILES if k in files}}
    source.MANIFEST_PATH.write_text(json.dumps(out, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="only check the files already in data/raw/")
    args = ap.parse_args()
    if not args.check:
        fetch_missing()
    return 0 if check() else 1


if __name__ == "__main__":
    sys.exit(main())
