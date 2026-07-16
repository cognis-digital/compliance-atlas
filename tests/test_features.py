"""Tests for the additive v0.2 capabilities: HTML export, posture drift (``diff``),
remediation ``plan``, posture ``template``, and the ``--min-coverage`` CI gate.

Every test asserts on real behaviour of the real :mod:`atlas` API and CLI — no
mocks, no placeholders. The suite runs with zero network.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest

import atlas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")


def _run_cli(*args):
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-m", "atlas", *args],
                          capture_output=True, text=True, cwd=ROOT, env=env)


# --- HTML exporter -----------------------------------------------------------

@pytest.fixture
def mixed_posture():
    return {"org": "T", "scope": ["soc2"],
            "controls": {"Access control": "implemented",
                         "Logging & monitoring": "missing",
                         "Risk management": "partial",
                         "Incident response": "n/a"}}


def test_html_is_registered_as_a_format():
    assert "html" in atlas._FORMATTERS
    assert atlas._FORMATTERS["html"] is atlas.to_html


def test_html_export_has_report_scaffold(mixed_posture):
    findings = atlas.assess(mixed_posture, framework="soc2")
    out = atlas.to_html(findings, mixed_posture)
    assert out.startswith("<div")
    assert out.rstrip().endswith("</div>")
    assert "compliance-atlas gap report" in out
    assert "<table" in out and "</table>" in out
    # one colour-coded body <tr> per finding (header row uses a different bg)
    body_rows = sum(out.count(f'<tr style="background:{c}')
                    for c in ("#fef2f2", "#fffbeb", "#f0fdf4"))
    assert body_rows == len(findings)
    # coverage percentage is rendered
    assert re.search(r"Coverage:\s*\d+%", out)


def test_html_escapes_untrusted_posture_values():
    """Org/scope from a posture file must be HTML-escaped (no markup injection)."""
    posture = {"org": "<script>alert(1)</script>",
               "scope": ["<b>x</b>"],
               "controls": {"Access control": "missing"}}
    out = atlas.to_html(atlas.assess(posture, framework="soc2"), posture)
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out
    assert "<b>x</b>" not in out


def test_html_severity_row_colors(mixed_posture):
    out = atlas.to_html(atlas.assess(mixed_posture, framework="soc2"), mixed_posture)
    # missing -> red-ish, partial -> amber-ish, clean -> green-ish backgrounds
    assert "#fef2f2" in out  # a high-severity (missing) row
    assert "#fffbeb" in out  # a medium-severity (partial) row


def test_cli_assess_html_format(mixed_posture, tmp_path):
    p = tmp_path / "posture.json"
    p.write_text(json.dumps(mixed_posture), encoding="utf-8")
    r = _run_cli("assess", str(p), "--framework", "soc2", "--format", "html")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().startswith("<div")
    assert "</table>" in r.stdout


# --- posture drift (diff) ----------------------------------------------------

def test_diff_detects_improvement_and_regression():
    old = {"controls": {"Access control": "missing",
                        "Logging & monitoring": "implemented"}}
    new = {"controls": {"Access control": "implemented",   # improved
                        "Logging & monitoring": "partial"}}  # regressed
    d = atlas.diff_postures(old, new)
    by_theme = {r["theme"]: r for r in d["themes"]}
    assert by_theme["Access control"]["change"] == "improved"
    assert by_theme["Logging & monitoring"]["change"] == "regressed"
    assert len(d["themes"]) == len(atlas.MATRIX)
    assert {r["theme"] for r in d["improved"]} == {"Access control"}
    assert {r["theme"] for r in d["regressed"]} == {"Logging & monitoring"}


def test_diff_coverage_delta_matches_summaries():
    old = {"controls": {t: "missing" for t in atlas.MATRIX}}
    new = {"controls": {t: "implemented" for t in atlas.MATRIX}}
    d = atlas.diff_postures(old, new)
    assert d["coverage_from"] == 0.0
    assert d["coverage_to"] == 1.0
    assert d["coverage_delta"] == 1.0


def test_diff_partitions_are_disjoint_and_complete():
    old = {"controls": {"Access control": "partial"}}
    new = {"controls": {"Access control": "implemented",
                        "Risk management": "partial"}}
    d = atlas.diff_postures(old, new)
    total = len(d["improved"]) + len(d["regressed"]) + len(d["unchanged"])
    assert total == len(atlas.MATRIX)


def test_diff_treats_na_rescoping_as_neutral():
    old = {"controls": {"Access control": "missing"}}
    new = {"controls": {"Access control": "n/a"}}
    d = atlas.diff_postures(old, new)
    ac = next(r for r in d["themes"] if r["theme"] == "Access control")
    assert ac["change"] == "unchanged"


def test_render_diff_is_readable():
    old = {"org": "Acme", "controls": {"Access control": "missing"}}
    new = {"org": "Acme", "controls": {"Access control": "implemented"}}
    text = atlas.render_diff(atlas.diff_postures(old, new))
    assert "posture drift" in text
    assert "Acme" in text
    assert "improved" in text


def test_cli_diff_table(tmp_path):
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(json.dumps({"controls": {"Access control": "missing"}}))
    new.write_text(json.dumps({"controls": {"Access control": "implemented"}}))
    r = _run_cli("diff", str(old), str(new))
    assert r.returncode == 0, r.stderr
    assert "posture drift" in r.stdout


def test_cli_diff_json_is_valid(tmp_path):
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(json.dumps({"controls": {"Access control": "partial"}}))
    new.write_text(json.dumps({"controls": {"Access control": "implemented"}}))
    r = _run_cli("diff", str(old), str(new), "--format", "json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["coverage_delta"] > 0
    assert "themes" in payload


def test_cli_diff_fail_on_regression(tmp_path):
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(json.dumps({"controls": {"Access control": "implemented"}}))
    new.write_text(json.dumps({"controls": {"Access control": "missing"}}))
    r = _run_cli("diff", str(old), str(new), "--fail-on-regression")
    assert r.returncode == 1


def test_cli_diff_no_regression_exit_zero(tmp_path):
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(json.dumps({"controls": {"Access control": "missing"}}))
    new.write_text(json.dumps({"controls": {"Access control": "implemented"}}))
    r = _run_cli("diff", str(old), str(new), "--fail-on-regression")
    assert r.returncode == 0


def test_cli_diff_bad_file_exit_two(tmp_path):
    good = tmp_path / "g.json"
    good.write_text(json.dumps({"controls": {}}))
    r = _run_cli("diff", str(good), os.path.join(ROOT, "nope.json"))
    assert r.returncode == 2


# --- remediation plan --------------------------------------------------------

def test_plan_orders_missing_before_partial():
    posture = {"controls": {"Access control": "partial",
                            "Logging & monitoring": "missing"}}
    plan = atlas.remediation_plan(posture)
    statuses = [it["status"] for it in plan["plan"]]
    # all missing themes come before any partial
    first_partial = statuses.index("partial") if "partial" in statuses else len(statuses)
    assert all(s == "missing" for s in statuses[:first_partial])
    assert plan["open_gaps"] == len(plan["plan"])


def test_plan_excludes_implemented_and_na():
    posture = {"controls": {t: "implemented" for t in atlas.MATRIX}}
    posture["controls"]["Access control"] = "n/a"
    plan = atlas.remediation_plan(posture)
    assert plan["plan"] == []
    assert plan["open_gaps"] == 0


def test_plan_coverage_gain_is_correct():
    # all seven themes scored; taking one missing theme to implemented -> +1/7
    posture = {"controls": {t: "missing" for t in atlas.MATRIX}}
    plan = atlas.remediation_plan(posture)
    for it in plan["plan"]:
        assert it["coverage_gain"] == pytest.approx(1 / 7, abs=0.001)
    # partial gains half as much
    posture2 = {"controls": {t: "partial" for t in atlas.MATRIX}}
    plan2 = atlas.remediation_plan(posture2)
    for it in plan2["plan"]:
        assert it["coverage_gain"] == pytest.approx(0.5 / 7, abs=0.001)


def test_plan_satisfies_every_framework():
    posture = {"controls": {"Access control": "missing"}}
    plan = atlas.remediation_plan(posture)
    ac = next(it for it in plan["plan"] if it["theme"] == "Access control")
    assert set(ac["satisfies"]) == set(atlas.FRAMEWORKS)
    assert ac["priority"] == "high"
    assert ac["step"] == 1


def test_plan_is_deterministic():
    posture = {"controls": {"Access control": "partial",
                            "Risk management": "missing"}}
    assert atlas.remediation_plan(posture) == atlas.remediation_plan(posture)


def test_render_plan_clean_posture():
    posture = {"controls": {t: "implemented" for t in atlas.MATRIX}}
    text = atlas.render_plan(atlas.remediation_plan(posture))
    assert "No open gaps" in text


def test_cli_plan_table():
    r = _run_cli("plan", os.path.join(DEMOS, "01-saas-soc2", "posture.json"))
    assert r.returncode == 0, r.stderr
    assert "remediation plan" in r.stdout
    assert "satisfies:" in r.stdout


def test_cli_plan_json():
    r = _run_cli("plan", os.path.join(DEMOS, "01-saas-soc2", "posture.json"),
                 "--format", "json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert "plan" in payload and isinstance(payload["plan"], list)


# --- posture template --------------------------------------------------------

def test_template_has_every_theme_and_valid_status():
    tmpl = atlas.new_posture_template(org="Acme", status="partial")
    assert set(tmpl["controls"]) == set(atlas.MATRIX)
    assert all(v == "partial" for v in tmpl["controls"].values())
    assert tmpl["org"] == "Acme"
    # a template must survive the real loader without error
    # (round-trip through validation like a user-authored file)
    assert set(tmpl["scope"]) == set(atlas.FRAMEWORKS)


def test_template_rejects_bad_status():
    with pytest.raises(atlas.PostureError):
        atlas.new_posture_template(status="bogus")


def test_template_output_loads_back(tmp_path):
    tmpl = atlas.new_posture_template()
    p = tmp_path / "posture.json"
    p.write_text(json.dumps(tmpl), encoding="utf-8")
    loaded = atlas.load_posture(str(p))   # must validate cleanly
    assert loaded["controls"] == tmpl["controls"]


def test_cli_template_default_is_valid_json():
    r = _run_cli("template", "--org", "Acme")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["org"] == "Acme"
    assert set(payload["controls"]) == set(atlas.MATRIX)


def test_cli_template_bad_status_exit_two():
    r = _run_cli("template", "--status", "definitely-not-valid")
    # argparse rejects the choice before our code runs -> usage error exit 2
    assert r.returncode == 2


# --- --min-coverage gate -----------------------------------------------------

def test_cli_min_coverage_fails_below_threshold():
    r = _run_cli("assess", os.path.join(DEMOS, "01-saas-soc2", "posture.json"),
                 "--framework", "soc2", "--min-coverage", "0.99")
    assert r.returncode == 1
    assert "below the required" in r.stderr


def test_cli_min_coverage_passes_at_threshold():
    r = _run_cli("assess", os.path.join(DEMOS, "07-iso-certification-prep", "posture.json"),
                 "--framework", "iso27001", "--min-coverage", "1.0")
    assert r.returncode == 0, r.stderr


def test_cli_min_coverage_still_prints_report():
    r = _run_cli("assess", os.path.join(DEMOS, "01-saas-soc2", "posture.json"),
                 "--framework", "soc2", "--min-coverage", "0.99")
    # gate failure must not suppress the report itself
    assert "gap report" in r.stdout
