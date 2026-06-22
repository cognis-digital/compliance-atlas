"""Offline tests for the bundled data-feed enrichment layer (atlas_feeds).

These NEVER hit the network: ``COGNIS_FEEDS_CACHE`` is pointed at the trimmed
fixtures under ``tests/fixtures/cache`` and every feed read uses ``offline=True``,
so CI stays green on an air-gapped runner.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

import atlas
import atlas_feeds
import datafeeds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_CACHE = os.path.join(ROOT, "tests", "fixtures", "cache")


@pytest.fixture(autouse=True)
def _point_cache_at_fixtures(monkeypatch):
    """Force the feed cache to the committed fixtures so no network is touched."""
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", FIXTURE_CACHE)
    yield


# --- catalog wiring is restricted to this repo's domain ----------------------

def test_relevant_feeds_are_only_this_repos_domain():
    ids = {f["id"] for f in atlas_feeds.relevant_feeds()}
    assert ids == set(atlas_feeds.RELEVANT_FEEDS)
    assert ids == {"oscal-800-53-rev5-catalog", "attack-nist-mappings"}


def test_relevant_feeds_are_real_catalog_entries():
    """The wired feeds must come from the bundled catalog, not be invented."""
    catalog_ids = {f["id"] for f in datafeeds.load_catalog()["feeds"]}
    for fid in atlas_feeds.RELEVANT_FEEDS:
        assert fid in catalog_ids


def test_get_rejects_feeds_outside_this_repos_domain():
    with pytest.raises(KeyError):
        atlas_feeds._get("cisa-kev", offline=True)


# --- fixtures present + parse ------------------------------------------------

def test_fixture_cache_present():
    for fid in atlas_feeds.RELEVANT_FEEDS:
        assert os.path.exists(os.path.join(FIXTURE_CACHE, f"{fid}.data"))
        assert os.path.exists(os.path.join(FIXTURE_CACHE, f"{fid}.meta.json"))


def test_offline_get_parses_oscal():
    data = atlas_feeds._get("oscal-800-53-rev5-catalog", offline=True)
    assert "catalog" in data
    assert data["catalog"]["groups"]


def test_offline_get_parses_mappings():
    data = atlas_feeds._get("attack-nist-mappings", offline=True)
    assert data["mapping_objects"]


# --- OSCAL family index ------------------------------------------------------

def test_oscal_family_index_resolves_real_titles():
    oscal = atlas_feeds._get("oscal-800-53-rev5-catalog", offline=True)
    idx = atlas_feeds.oscal_family_index(oscal)
    # families the matrix references must resolve to their official NIST titles
    assert idx["ac"]["title"] == "Access Control"
    assert idx["au"]["title"] == "Audit and Accountability"
    assert idx["sc"]["title"] == "System and Communications Protection"
    assert idx["sr"]["title"] == "Supply Chain Risk Management"
    assert idx["ac"]["controls"]  # real control ids present


def test_every_matrix_800_53_code_resolves_in_catalog():
    oscal = atlas_feeds._get("oscal-800-53-rev5-catalog", offline=True)
    idx = atlas_feeds.oscal_family_index(oscal)
    for theme, fw in atlas.MATRIX.items():
        code = fw["800-53"].lower()
        assert code in idx, f"{theme}: 800-53 family {code!r} missing from OSCAL catalog"
        assert idx[code]["title"], code


# --- ATT&CK coverage ---------------------------------------------------------

def test_attack_coverage_counts_distinct_techniques():
    mappings = atlas_feeds._get("attack-nist-mappings", offline=True)
    cov = atlas_feeds.attack_coverage_by_family(mappings)
    # fixture seeds AC/SC/CM/RA/SR; counts are positive ints
    assert cov.get("ac", 0) > 0
    assert all(isinstance(v, int) and v >= 0 for v in cov.values())


# --- enrich_matrix -----------------------------------------------------------

def test_enrich_matrix_shape_and_realness():
    rows = atlas_feeds.enrich_matrix(atlas.MATRIX, offline=True)
    assert len(rows) == len(atlas.MATRIX)
    by_theme = {r["theme"]: r for r in rows}
    ac = by_theme["Access control"]
    assert ac["family_code"] == "AC"
    assert ac["family_title"] == "Access Control"
    assert ac["control_count"] > 0
    assert ac["attack_techniques"] > 0
    for r in rows:
        assert set(r) == {"theme", "family_code", "family_title",
                          "control_count", "attack_techniques"}


# --- enrich_findings ---------------------------------------------------------

def test_enrich_findings_annotates_only_800_53():
    findings = atlas.assess({"controls": {}})  # all frameworks
    atlas_feeds.enrich_findings(findings, offline=True)
    for f in findings:
        if f["framework"] == "800-53":
            assert "family_title" in f and f["family_title"]
            assert "attack_techniques" in f
        else:
            assert "family_title" not in f


# --- offline really means offline --------------------------------------------

def test_offline_raises_when_nothing_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", str(tmp_path))  # empty cache
    with pytest.raises(FileNotFoundError):
        atlas_feeds.enrich_matrix(atlas.MATRIX, offline=True)


# --- snapshot round-trip (air-gap sneakernet) --------------------------------

def test_snapshot_export_import_roundtrip(tmp_path, monkeypatch):
    snap = tmp_path / "feeds.tar.gz"
    # export from the fixture cache
    n = datafeeds.snapshot_export(str(snap))
    assert n >= len(atlas_feeds.RELEVANT_FEEDS)
    # import into a fresh empty cache, then read offline
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", str(tmp_path / "enclave"))
    datafeeds.snapshot_import(str(snap))
    data = atlas_feeds._get("oscal-800-53-rev5-catalog", offline=True)
    assert "catalog" in data


# --- CLI (subprocess) keeps the cache env, stays offline ---------------------

def _run_cli(*args):
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1",
               COGNIS_FEEDS_CACHE=FIXTURE_CACHE)
    return subprocess.run([sys.executable, "-m", "atlas", *args],
                          capture_output=True, text=True, cwd=ROOT, env=env)


def test_cli_feeds_list():
    r = _run_cli("feeds", "list")
    assert r.returncode == 0
    assert "oscal-800-53-rev5-catalog" in r.stdout
    assert "attack-nist-mappings" in r.stdout
    # must NOT leak other catalog feeds
    assert "cisa-kev" not in r.stdout


def test_cli_feeds_enrich_offline():
    r = _run_cli("feeds", "enrich", "--offline")
    assert r.returncode == 0, r.stderr
    assert "Access Control" in r.stdout
    assert "Supply Chain Risk Management" in r.stdout


def test_cli_feeds_get_offline():
    r = _run_cli("feeds", "get", "oscal-800-53-rev5-catalog", "--offline")
    assert r.returncode == 0, r.stderr
    assert "catalog" in r.stdout


def test_cli_feeds_get_rejects_foreign_feed():
    r = _run_cli("feeds", "get", "cisa-kev", "--offline")
    assert r.returncode == 1
    assert "compliance-atlas feed" in r.stderr


def test_cli_assess_enrich_offline_json():
    r = _run_cli("assess", os.path.join("demos", "03-defense-cmmc-800171", "posture.json"),
                 "--framework", "800-53", "--format", "json", "--enrich", "--offline")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    for f in d["findings"]:
        assert "family_title" in f and f["family_title"]
        assert "attack_techniques" in f
