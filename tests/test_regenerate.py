"""The committed outputs of every part regenerate byte for byte from the real snapshot.

Needs the raw files and the local database (python scripts/download_data.py,
then python scripts/profile_report.py), so it is skipped in CI, where the
data is never downloaded (Inside Airbnb asks for one download, not one per run).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from str_market import source

pytestmark = pytest.mark.skipif(not source.DB_PATH.exists(), reason="needs the local database built from data/raw/")

REPORTS = {"profile": ["scripts/profile_report.py", "--no-build"], "pricing": ["scripts/pricing_report.py"],
           "hosts": ["scripts/hosts_report.py"]}


@pytest.fixture(scope="module")
def made(tmp_path_factory) -> dict[str, tuple[Path, list[Path]]]:
    out = {}
    for name, cmd in REPORTS.items():
        d = tmp_path_factory.mktemp(name)
        subprocess.run([sys.executable, *cmd, "--results", str(d)], cwd=source.ROOT, check=True, capture_output=True)
        out[name] = (d, sorted(p.relative_to(d) for p in d.rglob("*") if p.is_file()))
    return out


@pytest.mark.parametrize("name", REPORTS)
def test_report_regenerates_unchanged(made, name):
    d, files = made[name]
    assert files, "nothing was written"
    for rel in files:
        committed = source.RESULTS / rel
        assert committed.exists(), f"{rel} is not committed"
        assert (d / rel).read_bytes() == committed.read_bytes(), f"{rel} differs"


def test_every_results_file_is_written_by_exactly_one_report(made):
    owners: dict[Path, list[str]] = {}
    for name, (_d, files) in made.items():
        for rel in files:
            owners.setdefault(rel, []).append(name)
    committed = sorted(p.relative_to(source.RESULTS) for p in source.RESULTS.rglob("*") if p.is_file())
    wrong = {str(rel): owners.get(rel, []) for rel in committed if len(owners.get(rel, [])) != 1}
    assert not wrong, f"results files not written by exactly one report: {wrong}"
