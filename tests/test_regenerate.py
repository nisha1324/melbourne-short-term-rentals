"""The committed Part 1 outputs regenerate byte for byte from the real snapshot.

Needs the raw files and the local database (python scripts/download_data.py,
then python scripts/profile_report.py), so it is skipped in CI, where the
data is never downloaded (Inside Airbnb asks for one download, not one per run).
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from str_market import source

pytestmark = pytest.mark.skipif(not source.DB_PATH.exists(), reason="needs the local database built from data/raw/")


def test_profile_report_regenerates_unchanged(tmp_path):
    subprocess.run([sys.executable, "scripts/profile_report.py", "--no-build", "--results", str(tmp_path)],
                   cwd=source.ROOT, check=True, capture_output=True)
    made = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert made, "nothing was written"
    for rel in made:
        committed = source.RESULTS / rel
        assert committed.exists(), f"{rel} is not committed"
        assert (tmp_path / rel).read_bytes() == committed.read_bytes(), f"{rel} differs"
