"""Shared helpers for the runnable demo scenarios.

Every scenario in this folder drives the *real* compliance-atlas API — the same
``atlas.assess`` / ``atlas.summarize`` / exporter functions the CLI uses, and the
same offline ``atlas_feeds`` enrichment the tests use. Nothing here fabricates
controls, findings, or output: each demo loads one of the worked ``posture.json``
files under ``demos/<NN-name>/`` and cross-walks it against ``atlas.MATRIX``
(transcribed verbatim from ``crosswalks/master-matrix.md``).

Feed enrichment (demo 05) is served from the committed offline fixture cache, so
the whole suite runs with **zero network**.
"""
from __future__ import annotations

import os
import sys

# allow `python demos/NN_name.py` from anywhere
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import atlas  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS_DIR = os.path.join(REPO_ROOT, "demos")

# The committed, trimmed feed cache the tests use — lets demo 05 enrich fully
# offline (NIST 800-53 OSCAL titles + ATT&CK technique coverage). No network.
FIXTURE_CACHE = os.path.join(REPO_ROOT, "tests", "fixtures", "cache")


def posture_path(slug: str) -> str:
    """Absolute path to a worked posture file, e.g. ``"01-saas-soc2"``."""
    return os.path.join(DEMOS_DIR, slug, "posture.json")


def load(slug: str) -> dict:
    """Load + validate one of the worked posture files via the real loader."""
    return atlas.load_posture(posture_path(slug))


def rule(title: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {title}")
    print("=" * 72)


def coverage_bar(score: float, width: int = 24) -> str:
    """A tiny ASCII coverage meter, e.g. ``[#############-----------] 57%``."""
    filled = int(round(score * width))
    return f"[{'#' * filled}{'-' * (width - filled)}] {score:.0%}"


def status_glyph(status: str) -> str:
    return {"implemented": "OK ", "partial": "~~ ",
            "missing": "XX ", "n/a": "-- "}.get(status, "?? ")


def print_summary(findings: list[dict], posture: dict) -> dict:
    """Print the real ``atlas.summarize`` rollup as a coverage line."""
    summ = atlas.summarize(findings)
    counts = ", ".join(f"{k}:{v}" for k, v in sorted(summ["by_status"].items()))
    print(f"\n   coverage {coverage_bar(summ['coverage'])}   ({counts})")
    return summ
