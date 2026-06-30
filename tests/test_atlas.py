"""Tests for the atlas gap-assessment CLI and exporters."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

import atlas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")


# --- matrix integrity --------------------------------------------------------

def test_matrix_matches_master_matrix_doc():
    """Every theme in the doc's master matrix is represented in the module."""
    with open(os.path.join(ROOT, "crosswalks", "master-matrix.md"), encoding="utf-8") as fh:
        doc = fh.read()
    for theme in atlas.MATRIX:
        assert theme in doc, f"{theme!r} not found in master-matrix.md"


def test_every_theme_maps_every_framework():
    for theme, mapping in atlas.MATRIX.items():
        assert set(mapping) == set(atlas.FRAMEWORKS), theme
        for v in mapping.values():
            assert v and isinstance(v, str)


# --- posture loading & validation -------------------------------------------

def test_load_rejects_unknown_theme(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"controls": {"Bogus": "missing"}}))
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(str(p))


def test_load_rejects_bad_status(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"controls": {"Access control": "maybe"}}))
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(str(p))


def test_load_rejects_non_object(tmp_path):
    p = tmp_path / "p.json"
    p.write_text("[1,2,3]")
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(str(p))


# --- assess core -------------------------------------------------------------

def test_missing_by_default():
    """Omitted themes are assessed as missing (silence == gap)."""
    findings = atlas.assess({"controls": {}}, framework="soc2")
    assert len(findings) == len(atlas.MATRIX)
    assert all(f["status"] == "missing" for f in findings)
    assert all(f["severity"] == "high" for f in findings)


def test_assess_all_frameworks_count():
    findings = atlas.assess({"controls": {}})
    assert len(findings) == len(atlas.MATRIX) * len(atlas.FRAMEWORKS)


def test_assess_unknown_framework_raises():
    with pytest.raises(atlas.PostureError):
        atlas.assess({"controls": {}}, framework="nope")


def test_findings_deterministic_and_severity_sorted():
    posture = {"controls": {"Access control": "implemented",
                            "Logging & monitoring": "missing",
                            "Incident response": "partial"}}
    a = atlas.assess(posture, framework="soc2")
    b = atlas.assess(posture, framework="soc2")
    assert a == b  # deterministic
    sev = [f["severity"] for f in a]
    rank = {"high": 0, "medium": 1, "none": 2}
    assert sev == sorted(sev, key=lambda s: rank[s])  # most severe first


def test_status_severity_mapping():
    posture = {"controls": {"Access control": "implemented",
                            "Crypto / data protection": "partial",
                            "Logging & monitoring": "missing",
                            "Incident response": "n/a"}}
    by_theme = {f["theme"]: f for f in atlas.assess(posture, framework="soc2")}
    assert by_theme["Access control"]["severity"] == "none"
    assert by_theme["Crypto / data protection"]["severity"] == "medium"
    assert by_theme["Logging & monitoring"]["severity"] == "high"
    assert by_theme["Incident response"]["severity"] == "none"


# --- summarize ---------------------------------------------------------------

def test_summary_coverage_math():
    posture = {"controls": {"Access control": "implemented",       # 1.0
                            "Crypto / data protection": "partial",  # 0.5
                            "Logging & monitoring": "missing",       # 0.0
                            "Incident response": "n/a",              # excluded
                            "Change management": "implemented",      # 1.0
                            "Risk management": "missing",            # 0.0
                            "Vendor / supply chain": "missing"}}     # 0.0
    findings = atlas.assess(posture, framework="soc2")
    summ = atlas.summarize(findings)
    # scored denom excludes n/a -> 6 themes; (1+0.5+0+1+0+0)/6 = 0.417
    assert summ["coverage"] == pytest.approx(0.417, abs=0.001)
    assert summ["themes"] == 7


def test_full_coverage_is_one():
    posture = {"controls": {t: "implemented" for t in atlas.MATRIX}}
    summ = atlas.summarize(atlas.assess(posture, framework="soc2"))
    assert summ["coverage"] == 1.0


# --- exporters ---------------------------------------------------------------

@pytest.fixture
def sample_findings():
    posture = {"org": "T", "controls": {"Logging & monitoring": "missing",
                                        "Risk management": "partial"}}
    return atlas.assess(posture, framework="soc2"), posture


def test_json_export_is_valid(sample_findings):
    findings, posture = sample_findings
    d = json.loads(atlas.to_json(findings, posture))
    assert d["tool"] == "compliance-atlas"
    assert "summary" in d and "findings" in d


def test_csv_export_has_header(sample_findings):
    findings, posture = sample_findings
    out = atlas.to_csv(findings, posture)
    assert out.splitlines()[0].startswith("theme,status,severity")
    assert len(out.splitlines()) == len(findings) + 1


def test_markdown_export(sample_findings):
    findings, posture = sample_findings
    out = atlas.to_markdown(findings, posture)
    assert out.startswith("# Compliance-atlas gap report")
    assert "| Theme | Status | Framework | Control |" in out


def test_sarif_2_1_0_shape(sample_findings):
    findings, posture = sample_findings
    d = json.loads(atlas.to_sarif(findings, posture))
    assert d["version"] == "2.1.0"
    run = d["runs"][0]
    assert run["tool"]["driver"]["name"] == "compliance-atlas"
    # only gaps become results; "none"-severity findings are excluded
    assert len(run["results"]) == sum(1 for f in findings if f["severity"] != "none")
    for r in run["results"]:
        assert r["level"] in ("error", "warning")
        assert r["ruleId"]
        assert r["message"]["text"]
    # every result references a declared rule
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert all(r["ruleId"] in rule_ids for r in run["results"])


def test_sarif_clean_posture_has_no_results():
    posture = {"controls": {t: "implemented" for t in atlas.MATRIX}}
    d = json.loads(atlas.to_sarif(atlas.assess(posture, framework="soc2"), posture))
    assert d["runs"][0]["results"] == []


# --- demos -------------------------------------------------------------------

def _demo_dirs():
    # worked-scenario dirs are exactly those carrying a posture.json
    # (skips helper dirs like __pycache__ and the runnable demos/*.py modules)
    return sorted(
        os.path.join(DEMOS, d) for d in os.listdir(DEMOS)
        if os.path.isdir(os.path.join(DEMOS, d))
        and os.path.exists(os.path.join(DEMOS, d, "posture.json"))
    )


def test_demos_present():
    dirs = _demo_dirs()
    assert len(dirs) >= 5


@pytest.mark.parametrize("demo", _demo_dirs())
def test_each_demo_loads_and_assesses(demo):
    posture_path = os.path.join(demo, "posture.json")
    scenario_path = os.path.join(demo, "SCENARIO.md")
    assert os.path.exists(posture_path), demo
    assert os.path.exists(scenario_path), demo
    posture = atlas.load_posture(posture_path)
    # must produce findings in every export format without error
    for fmt, fn in atlas._FORMATTERS.items():
        findings = atlas.assess(posture)
        out = fn(findings, posture)
        assert out
        if fmt in ("json", "sarif"):
            json.loads(out)  # valid JSON


# --- CLI ---------------------------------------------------------------------

def _run_cli(*args):
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-m", "atlas", *args],
                          capture_output=True, text=True, cwd=ROOT, env=env)


def test_cli_matrix():
    r = _run_cli("matrix")
    assert r.returncode == 0
    assert "Access control" in r.stdout


def test_cli_frameworks():
    r = _run_cli("frameworks")
    assert r.returncode == 0
    assert "soc2" in r.stdout


def test_cli_assess_demo_exit_zero():
    r = _run_cli("assess", os.path.join(DEMOS, "02-fintech-pci", "posture.json"),
                 "--framework", "pci-dss")
    assert r.returncode == 0
    assert "gap report" in r.stdout


def test_cli_fail_on_gap_returns_one_when_gaps():
    r = _run_cli("assess", os.path.join(DEMOS, "06-greenfield-baseline", "posture.json"),
                 "--framework", "nist-csf", "--fail-on-gap")
    assert r.returncode == 1


def test_cli_fail_on_gap_returns_zero_when_clean():
    r = _run_cli("assess", os.path.join(DEMOS, "07-iso-certification-prep", "posture.json"),
                 "--framework", "iso27001", "--fail-on-gap")
    assert r.returncode == 0


def test_cli_bad_file_exit_two():
    r = _run_cli("assess", os.path.join(ROOT, "does-not-exist.json"))
    assert r.returncode == 2
