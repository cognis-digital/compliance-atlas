"""Edge-case + error-path tests for the feed-enrichment layer (atlas_feeds).

All offline against the committed fixture cache — no network, ever. Complements
test_feeds.py with the failure modes: foreign feeds rejected at every entry,
empty/garbage catalog data handled, enrich on a framework-filtered posture,
CLI feeds error paths and exit codes, and snapshot round-trip corners.
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
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", FIXTURE_CACHE)
    yield


# --- domain restriction is enforced everywhere -------------------------------

@pytest.mark.parametrize("foreign", ["cisa-kev", "epss", "made-up-feed", ""])
def test_get_rejects_any_foreign_feed(foreign):
    with pytest.raises(KeyError):
        atlas_feeds._get(foreign, offline=True)


def test_relevant_catalog_hides_other_feeds():
    cat = atlas_feeds._relevant_catalog()
    ids = {f["id"] for f in cat["feeds"]}
    assert ids == set(atlas_feeds.RELEVANT_FEEDS)


def test_relevant_feeds_count_is_two():
    assert len(atlas_feeds.relevant_feeds()) == 2


# --- OSCAL family index parsing corners --------------------------------------

def test_oscal_family_index_empty_catalog():
    assert atlas_feeds.oscal_family_index({}) == {}
    assert atlas_feeds.oscal_family_index({"catalog": {}}) == {}
    assert atlas_feeds.oscal_family_index({"catalog": {"groups": []}}) == {}


def test_oscal_family_index_skips_groups_without_id():
    cat = {"catalog": {"groups": [
        {"title": "No Id Group", "controls": []},
        {"id": "AC", "title": "Access Control", "controls": [{"id": "ac-1"}]},
    ]}}
    idx = atlas_feeds.oscal_family_index(cat)
    assert "ac" in idx
    assert idx["ac"]["title"] == "Access Control"
    assert idx["ac"]["controls"] == ["ac-1"]
    # the id-less group is silently dropped, not crashed on
    assert len(idx) == 1


def test_oscal_family_index_lowercases_ids():
    cat = {"catalog": {"groups": [{"id": "SC", "title": "x", "controls": []}]}}
    assert "sc" in atlas_feeds.oscal_family_index(cat)


# --- ATT&CK coverage parsing corners -----------------------------------------

def test_attack_coverage_empty_mappings():
    assert atlas_feeds.attack_coverage_by_family({}) == {}
    assert atlas_feeds.attack_coverage_by_family({"mapping_objects": []}) == {}


def test_attack_coverage_skips_incomplete_and_blank():
    mappings = {"mapping_objects": [
        {"status": "complete", "capability_id": "AC-2", "attack_object_id": "T1"},
        {"status": "complete", "capability_id": "AC-3", "attack_object_id": "T1"},  # dup tech
        {"status": "complete", "capability_id": "AC-6", "attack_object_id": "T2"},
        {"status": "non_mappable", "capability_id": "AC-1", "attack_object_id": "T9"},
        {"status": "complete", "capability_id": "", "attack_object_id": "T3"},  # no cap
        {"status": "complete", "capability_id": "AU-2", "attack_object_id": None},  # no tech
    ]}
    cov = atlas_feeds.attack_coverage_by_family(mappings)
    assert cov["ac"] == 2  # T1 (deduped) + T2
    assert "au" not in cov  # the AU row had no technique


def test_attack_coverage_counts_are_nonneg_ints():
    mappings = atlas_feeds._get("attack-nist-mappings", offline=True)
    cov = atlas_feeds.attack_coverage_by_family(mappings)
    assert all(isinstance(v, int) and v >= 0 for v in cov.values())


# --- enrich_matrix corners ---------------------------------------------------

def test_enrich_matrix_every_theme_present():
    rows = atlas_feeds.enrich_matrix(atlas.MATRIX, offline=True)
    assert {r["theme"] for r in rows} == set(atlas.MATRIX)


def test_enrich_matrix_unknown_family_degrades_gracefully():
    # a theme whose 800-53 code is not in the catalog -> "(not in catalog)", 0s
    fake = {"Weird theme": {"800-53": "ZZ", "soc2": "CC1", "iso27001": "A",
                            "nist-csf": "X", "800-171": "9.9", "pci-dss": "Req 1"}}
    rows = atlas_feeds.enrich_matrix(fake, offline=True)
    assert rows[0]["family_title"] == "(not in catalog)"
    assert rows[0]["control_count"] == 0
    assert rows[0]["attack_techniques"] == 0


# --- enrich_findings corners -------------------------------------------------

def test_enrich_findings_returns_same_list_object():
    findings = atlas.assess({"controls": {}})
    out = atlas_feeds.enrich_findings(findings, offline=True)
    assert out is findings  # documented: annotates in place


def test_enrich_findings_only_touches_800_53():
    findings = atlas.assess({"controls": {}})
    atlas_feeds.enrich_findings(findings, offline=True)
    for f in findings:
        if f["framework"] == "800-53":
            assert "family_title" in f
            assert "attack_techniques" in f
        else:
            assert "family_title" not in f
            assert "attack_techniques" not in f


def test_enrich_findings_on_non_800_53_framework_is_noop():
    findings = atlas.assess({"controls": {}}, framework="soc2")
    atlas_feeds.enrich_findings(findings, offline=True)
    assert all("family_title" not in f for f in findings)


def test_enrich_findings_empty_list_safe():
    assert atlas_feeds.enrich_findings([], offline=True) == []


# --- offline really means offline --------------------------------------------

def test_enrich_findings_raises_with_empty_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", str(tmp_path))
    findings = atlas.assess({"controls": {}}, framework="800-53")
    with pytest.raises(FileNotFoundError):
        atlas_feeds.enrich_findings(findings, offline=True)


def test_enrich_matrix_raises_with_empty_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        atlas_feeds.enrich_matrix(atlas.MATRIX, offline=True)


# --- render_enrichment -------------------------------------------------------

def test_render_enrichment_is_aligned_text():
    rows = atlas_feeds.enrich_matrix(atlas.MATRIX, offline=True)
    out = atlas_feeds.render_enrichment(rows)
    assert "Access Control" in out
    assert "ATT&CK" in out
    # one body line per theme + header lines
    body = [ln for ln in out.splitlines() if "Access Control" in ln]
    assert body


# --- snapshot round-trip corners ---------------------------------------------

def test_snapshot_export_returns_feed_count(tmp_path):
    snap = tmp_path / "s.tar.gz"
    n = datafeeds.snapshot_export(str(snap))
    assert n >= len(atlas_feeds.RELEVANT_FEEDS)
    assert snap.exists() and snap.stat().st_size > 0


def test_snapshot_roundtrip_into_fresh_enclave(tmp_path, monkeypatch):
    snap = tmp_path / "s.tar.gz"
    datafeeds.snapshot_export(str(snap))
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", str(tmp_path / "enclave"))
    datafeeds.snapshot_import(str(snap))
    # both relevant feeds must be readable offline after import
    for fid in atlas_feeds.RELEVANT_FEEDS:
        assert atlas_feeds._get(fid, offline=True)


# --- CLI feeds subcommands ---------------------------------------------------

def _run(*args):
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1",
               COGNIS_FEEDS_CACHE=FIXTURE_CACHE)
    return subprocess.run([sys.executable, "-m", "atlas", *args],
                          capture_output=True, text=True, cwd=ROOT, env=env)


def test_cli_feeds_requires_subcommand():
    r = _run("feeds")
    assert r.returncode != 0


def test_cli_feeds_list_only_this_domain():
    r = _run("feeds", "list")
    assert r.returncode == 0
    assert "oscal-800-53-rev5-catalog" in r.stdout
    assert "attack-nist-mappings" in r.stdout
    assert "cisa-kev" not in r.stdout
    assert "epss" not in r.stdout


def test_cli_feeds_get_foreign_exit_one():
    r = _run("feeds", "get", "cisa-kev", "--offline")
    assert r.returncode == 1
    assert "compliance-atlas feed" in r.stderr


def test_cli_feeds_get_known_offline():
    r = _run("feeds", "get", "attack-nist-mappings", "--offline")
    assert r.returncode == 0, r.stderr
    assert "mapping_objects" in r.stdout


def test_cli_feeds_enrich_offline_lists_titles():
    r = _run("feeds", "enrich", "--offline")
    assert r.returncode == 0, r.stderr
    assert "Access Control" in r.stdout
    assert "Audit and Accountability" in r.stdout


def test_cli_feeds_get_missing_in_empty_cache_exit_one(tmp_path):
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1",
               COGNIS_FEEDS_CACHE=str(tmp_path))
    r = subprocess.run(
        [sys.executable, "-m", "atlas", "feeds", "get",
         "oscal-800-53-rev5-catalog", "--offline"],
        capture_output=True, text=True, cwd=ROOT, env=env)
    assert r.returncode == 1


def test_cli_assess_enrich_offline_json_annotates():
    r = _run("assess", os.path.join("demos", "10-gov-rmf-ato", "posture.json"),
             "--framework", "800-53", "--format", "json", "--enrich", "--offline")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    for f in d["findings"]:
        assert "family_title" in f and f["family_title"]
        assert "attack_techniques" in f


def test_cli_assess_enrich_empty_cache_exit_two(tmp_path):
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1",
               COGNIS_FEEDS_CACHE=str(tmp_path))
    r = subprocess.run(
        [sys.executable, "-m", "atlas", "assess",
         os.path.join("demos", "10-gov-rmf-ato", "posture.json"),
         "--framework", "800-53", "--enrich", "--offline"],
        capture_output=True, text=True, cwd=ROOT, env=env)
    assert r.returncode == 2
    assert "feed enrichment unavailable" in r.stderr
