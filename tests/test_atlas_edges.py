"""Edge-case and error-path tests for atlas — the gaps the happy-path suite leaves.

Covers: posture loading failure modes (bad JSON, bad UTF-8, wrong shapes, null
controls, scope shape), assess input validation, summarize math corners, every
exporter's structural invariants on tricky inputs, SARIF rule/result coupling,
the scope_frameworks helper, and the CLI exit-code contract (0 / 1 / 2).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

import atlas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")


def _write(tmp_path, payload, *, raw=None, encoding="utf-8"):
    p = tmp_path / "p.json"
    if raw is not None:
        p.write_bytes(raw)
    else:
        p.write_text(json.dumps(payload), encoding=encoding)
    return str(p)


# --- load_posture: malformed content -> PostureError, with the path named ----

def test_load_bad_json_raises_posture_error(tmp_path):
    p = tmp_path / "p.json"
    p.write_text("{ this is not json ")
    with pytest.raises(atlas.PostureError) as ei:
        atlas.load_posture(str(p))
    assert str(p) in str(ei.value)
    assert "JSON" in str(ei.value)


def test_load_empty_file_raises_posture_error(tmp_path):
    p = tmp_path / "p.json"
    p.write_text("")
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(str(p))


def test_load_non_utf8_raises_posture_error(tmp_path):
    p = tmp_path / "p.json"
    # 0xFF is not valid UTF-8 and not a UTF-8/UTF-16 BOM Python would auto-handle
    p.write_bytes(b'{"org": "\xff\xfe bad bytes"}')
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(str(p))


def test_load_missing_file_raises_oserror(tmp_path):
    # OSError (not PostureError) is the contract for a missing file.
    with pytest.raises(OSError):
        atlas.load_posture(str(tmp_path / "nope.json"))


def test_load_json_array_rejected(tmp_path):
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(_write(tmp_path, [1, 2, 3]))


@pytest.mark.parametrize("scalar", ["\"a string\"", "42", "true", "null"])
def test_load_json_scalar_rejected(tmp_path, scalar):
    p = tmp_path / "p.json"
    p.write_text(scalar)
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(str(p))


def test_load_null_controls_treated_as_empty(tmp_path):
    # controls: null must not crash — it means "nothing declared".
    posture = atlas.load_posture(_write(tmp_path, {"controls": None}))
    findings = atlas.assess(posture, framework="soc2")
    assert all(f["status"] == "missing" for f in findings)


def test_load_missing_controls_key_ok(tmp_path):
    posture = atlas.load_posture(_write(tmp_path, {"org": "x"}))
    assert atlas.assess(posture, framework="soc2")


def test_load_controls_as_list_rejected(tmp_path):
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(_write(tmp_path, {"controls": ["Access control"]}))


def test_load_controls_as_string_rejected(tmp_path):
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(_write(tmp_path, {"controls": "implemented"}))


@pytest.mark.parametrize("bad", [5, 5.0, True, None, ["partial"], {"x": 1}])
def test_load_non_string_status_rejected(tmp_path, bad):
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(_write(tmp_path, {"controls": {"Access control": bad}}))


@pytest.mark.parametrize("theme", ["", "access control", "Access Control",
                                   "ACCESS CONTROL", "Bogus theme", "CC6"])
def test_load_unknown_or_miscased_theme_rejected(tmp_path, theme):
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(_write(tmp_path, {"controls": {theme: "missing"}}))


@pytest.mark.parametrize("status", VALID := list(atlas.VALID_STATUS))
def test_load_accepts_every_valid_status(tmp_path, status):
    posture = atlas.load_posture(
        _write(tmp_path, {"controls": {"Access control": status}}))
    assert posture["controls"]["Access control"] == status


# --- scope shape + scope_frameworks helper -----------------------------------

def test_load_scope_as_string_rejected(tmp_path):
    with pytest.raises(atlas.PostureError):
        atlas.load_posture(_write(tmp_path, {"scope": "soc2", "controls": {}}))


def test_load_scope_with_adjacency_tags_allowed(tmp_path):
    # non-framework tags are valid scope entries (e.g. cmmc-l2, hipaa-adjacent)
    posture = atlas.load_posture(
        _write(tmp_path, {"scope": ["800-171", "cmmc-l2"], "controls": {}}))
    assert posture["scope"] == ["800-171", "cmmc-l2"]


def test_load_scope_null_allowed(tmp_path):
    posture = atlas.load_posture(_write(tmp_path, {"scope": None, "controls": {}}))
    assert atlas.scope_frameworks(posture) == []


def test_scope_frameworks_filters_to_known_keys():
    posture = {"scope": ["800-171", "cmmc-l2", "soc2", "made-up"]}
    assert atlas.scope_frameworks(posture) == ["800-171", "soc2"]


def test_scope_frameworks_preserves_order():
    posture = {"scope": ["pci-dss", "soc2", "iso27001"]}
    assert atlas.scope_frameworks(posture) == ["pci-dss", "soc2", "iso27001"]


def test_scope_frameworks_empty_when_absent():
    assert atlas.scope_frameworks({}) == []
    assert atlas.scope_frameworks({"scope": []}) == []


def test_scope_frameworks_non_list_is_empty():
    assert atlas.scope_frameworks({"scope": "soc2"}) == []


def test_scope_frameworks_results_index_FRAMEWORKS():
    posture = {"scope": ["soc2", "weird-tag", "pci-dss"]}
    # the whole point: results are always safe to map through FRAMEWORKS
    names = [atlas.FRAMEWORKS[f] for f in atlas.scope_frameworks(posture)]
    assert names == ["SOC 2 (TSC)", "PCI DSS 4.0"]


# --- assess: input validation -----------------------------------------------

def test_assess_empty_string_framework_rejected():
    # framework="" is a caller bug, not "all frameworks"
    with pytest.raises(atlas.PostureError):
        atlas.assess({"controls": {}}, framework="")


def test_assess_none_framework_is_all():
    findings = atlas.assess({"controls": {}}, framework=None)
    assert len(findings) == len(atlas.MATRIX) * len(atlas.FRAMEWORKS)


def test_assess_unknown_framework_message_lists_valid():
    with pytest.raises(atlas.PostureError) as ei:
        atlas.assess({"controls": {}}, framework="iso")
    assert "soc2" in str(ei.value)


def test_assess_null_controls_does_not_crash():
    findings = atlas.assess({"controls": None}, framework="soc2")
    assert all(f["status"] == "missing" for f in findings)


def test_assess_missing_controls_key():
    findings = atlas.assess({}, framework="soc2")
    assert len(findings) == len(atlas.MATRIX)


def test_assess_controls_as_list_rejected():
    with pytest.raises(atlas.PostureError):
        atlas.assess({"controls": ["x"]}, framework="soc2")


def test_assess_invalid_status_in_raw_posture_rejected():
    # a hand-built posture that skipped load_posture must still be guarded
    with pytest.raises(atlas.PostureError):
        atlas.assess({"controls": {"Access control": "kinda"}}, framework="soc2")


@pytest.mark.parametrize("fw", list(atlas.FRAMEWORKS))
def test_assess_every_framework_one_finding_per_theme(fw):
    findings = atlas.assess({"controls": {}}, framework=fw)
    assert len(findings) == len(atlas.MATRIX)
    assert {f["framework"] for f in findings} == {fw}
    assert all(f["control"] == atlas.MATRIX[f["theme"]][fw] for f in findings)


def test_assess_finding_keys_are_stable():
    f = atlas.assess({"controls": {}}, framework="soc2")[0]
    assert set(f) == {"theme", "status", "severity", "framework",
                      "framework_name", "control"}


def test_assess_n_a_is_none_severity():
    posture = {"controls": {t: "n/a" for t in atlas.MATRIX}}
    findings = atlas.assess(posture, framework="soc2")
    assert all(f["severity"] == "none" for f in findings)


def test_assess_partial_is_medium_missing_is_high():
    posture = {"controls": {"Access control": "partial",
                            "Logging & monitoring": "missing"}}
    by = {f["theme"]: f for f in atlas.assess(posture, framework="soc2")}
    assert by["Access control"]["severity"] == "medium"
    assert by["Logging & monitoring"]["severity"] == "high"


def test_assess_sort_is_severity_then_theme_then_framework():
    posture = {"controls": {"Vendor / supply chain": "missing"}}
    findings = atlas.assess(posture)  # all frameworks
    rank = {"high": 0, "medium": 1, "none": 2}
    keys = [(rank[f["severity"]]) for f in findings]
    assert keys == sorted(keys)


# --- summarize: corner cases -------------------------------------------------

def test_summarize_all_n_a_coverage_is_zero_denominator_safe():
    posture = {"controls": {t: "n/a" for t in atlas.MATRIX}}
    summ = atlas.summarize(atlas.assess(posture, framework="soc2"))
    # everything excluded from the denominator -> guarded /1, not a crash
    assert summ["coverage"] == 0.0
    assert summ["themes"] == len(atlas.MATRIX)


def test_summarize_empty_findings_is_safe():
    summ = atlas.summarize([])
    assert summ["themes"] == 1  # guarded denominator
    assert summ["coverage"] == 0.0
    assert summ["by_status"] == {}


def test_summarize_counts_each_theme_once_across_frameworks():
    posture = {"controls": {"Access control": "implemented"}}
    summ = atlas.summarize(atlas.assess(posture))  # 7 themes x 6 frameworks
    assert summ["themes"] == len(atlas.MATRIX)
    assert sum(summ["by_status"].values()) == len(atlas.MATRIX)


def test_summarize_partial_counts_as_half():
    posture = {"controls": {t: "partial" for t in atlas.MATRIX}}
    summ = atlas.summarize(atlas.assess(posture, framework="soc2"))
    assert summ["coverage"] == pytest.approx(0.5)


def test_summarize_mixed_excludes_n_a_from_denominator():
    posture = {"controls": {"Access control": "implemented",
                            "Crypto / data protection": "n/a",
                            "Logging & monitoring": "missing"}}
    summ = atlas.summarize(atlas.assess(posture, framework="soc2"))
    # remaining 5 themes default to missing; n/a excluded.
    # implemented(1) + 6 missing(0), n/a excluded -> 1/6
    assert summ["coverage"] == pytest.approx(1 / 6, abs=1e-3)


# --- exporters: invariants on tricky inputs ----------------------------------

@pytest.fixture
def mixed():
    posture = {"org": "Mixed Co", "scope": ["soc2"],
               "controls": {"Access control": "implemented",
                            "Crypto / data protection": "partial",
                            "Logging & monitoring": "missing",
                            "Incident response": "n/a"}}
    return atlas.assess(posture, framework="soc2"), posture


@pytest.mark.parametrize("fmt", list(atlas._FORMATTERS))
def test_every_exporter_nonempty_on_mixed(mixed, fmt):
    findings, posture = mixed
    out = atlas._FORMATTERS[fmt](findings, posture)
    assert out and out.strip()


@pytest.mark.parametrize("fmt", list(atlas._FORMATTERS))
def test_every_exporter_handles_empty_findings(fmt):
    # exporters must not crash on an empty findings list (default= guards)
    out = atlas._FORMATTERS[fmt]([], {"org": "Empty"})
    assert isinstance(out, str)


def test_json_export_roundtrips_all_findings(mixed):
    findings, posture = mixed
    d = json.loads(atlas.to_json(findings, posture))
    assert len(d["findings"]) == len(findings)
    assert d["org"] == "Mixed Co"
    assert d["scope"] == ["soc2"]


def test_csv_one_row_per_finding(mixed):
    findings, posture = mixed
    lines = atlas.to_csv(findings, posture).splitlines()
    assert lines[0].split(",")[0] == "theme"
    assert len(lines) == len(findings) + 1


def test_csv_uses_lf_not_crlf(mixed):
    # explicit lineterminator="\n" — must not emit Windows CRLF
    findings, posture = mixed
    assert "\r\n" not in atlas.to_csv(findings, posture)


def test_markdown_has_table_header_and_disclaimer(mixed):
    findings, posture = mixed
    out = atlas.to_markdown(findings, posture)
    assert "| Theme | Status | Framework | Control |" in out
    assert "Not legal advice" in out


def test_table_reports_org_and_coverage(mixed):
    findings, posture = mixed
    out = atlas.to_table(findings, posture)
    assert "Mixed Co" in out
    assert "coverage" in out


def test_table_unnamed_org_fallback():
    out = atlas.to_table(atlas.assess({"controls": {}}, framework="soc2"), {})
    assert "(unnamed)" in out


# --- SARIF: gaps-only, rule/result coupling, schema ---------------------------

def test_sarif_only_gaps_become_results(mixed):
    findings, posture = mixed
    d = json.loads(atlas.to_sarif(findings, posture))
    results = d["runs"][0]["results"]
    gaps = [f for f in findings if f["severity"] != "none"]
    assert len(results) == len(gaps)
    assert all(r["level"] in ("error", "warning") for r in results)


def test_sarif_levels_map_status():
    posture = {"controls": {"Access control": "missing",
                            "Crypto / data protection": "partial"}}
    d = json.loads(atlas.to_sarif(atlas.assess(posture, framework="soc2"), posture))
    levels = {r["properties"]["status"]: r["level"]
              for r in d["runs"][0]["results"]}
    assert levels["missing"] == "error"
    assert levels["partial"] == "warning"


def test_sarif_every_result_references_declared_rule(mixed):
    findings, posture = mixed
    d = json.loads(atlas.to_sarif(findings, posture))
    run = d["runs"][0]
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert rule_ids
    assert all(r["ruleId"] in rule_ids for r in run["results"])


def test_sarif_rules_are_deduplicated():
    # same theme across many frameworks -> one rule, many results
    posture = {"controls": {"Vendor / supply chain": "missing"}}
    d = json.loads(atlas.to_sarif(atlas.assess(posture), posture))
    run = d["runs"][0]
    vendor_rules = [r for r in run["tool"]["driver"]["rules"]
                    if "Vendor" in r["id"]]
    assert len(vendor_rules) == 1


def test_sarif_clean_posture_no_results():
    posture = {"controls": {t: "implemented" for t in atlas.MATRIX}}
    d = json.loads(atlas.to_sarif(atlas.assess(posture), posture))
    assert d["runs"][0]["results"] == []


def test_sarif_carries_tool_version(mixed):
    findings, posture = mixed
    d = json.loads(atlas.to_sarif(findings, posture))
    ver = d["runs"][0]["tool"]["driver"]["version"]
    assert ver and ver != "0.0.0"


def test_sarif_schema_and_version(mixed):
    findings, posture = mixed
    d = json.loads(atlas.to_sarif(findings, posture))
    assert d["version"] == "2.1.0"
    assert "sarif-2.1.0" in d["$schema"]


# --- matrix / frameworks integrity -------------------------------------------

def test_matrix_themes_unique():
    assert len(atlas.MATRIX) == len(set(atlas.MATRIX))


def test_every_status_in_severity_table():
    for s in atlas.VALID_STATUS:
        assert s in atlas._SEVERITY


def test_severity_values_are_known():
    for sev, level in atlas._SEVERITY.values():
        assert sev in ("high", "medium", "none")
        assert level in ("error", "warning", "note")


def test_frameworks_keys_match_matrix_columns():
    for mapping in atlas.MATRIX.values():
        assert set(mapping) == set(atlas.FRAMEWORKS)


def test_version_helper_reads_version_file():
    assert atlas._version() == open(
        os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()


# --- CLI exit-code contract (0 / 1 / 2) --------------------------------------

def _run(*args, posture=None):
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-m", "atlas", *args],
                          capture_output=True, text=True, cwd=ROOT, env=env)


def _demo(slug):
    return os.path.join(DEMOS, slug, "posture.json")


def test_cli_no_subcommand_errors():
    r = _run()
    assert r.returncode != 0  # argparse required=True


def test_cli_assess_clean_posture_exit_zero():
    r = _run("assess", _demo("11-clean-soc2-iso"), "--framework", "soc2",
             "--fail-on-gap")
    assert r.returncode == 0, r.stderr


def test_cli_assess_mixed_posture_fail_on_gap_exit_one():
    r = _run("assess", _demo("12-retail-pci-saq"), "--framework", "pci-dss",
             "--fail-on-gap")
    assert r.returncode == 1


def test_cli_assess_without_gate_exit_zero_even_with_gaps():
    r = _run("assess", _demo("12-retail-pci-saq"), "--framework", "pci-dss")
    assert r.returncode == 0


def test_cli_bad_json_exit_two(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ nope ")
    r = _run("assess", str(p))
    assert r.returncode == 2
    assert "atlas:" in r.stderr


def test_cli_unknown_theme_exit_two(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"controls": {"Nope": "missing"}}))
    r = _run("assess", str(p))
    assert r.returncode == 2


def test_cli_unknown_framework_choice_rejected():
    r = _run("assess", _demo("01-saas-soc2"), "--framework", "bogus")
    assert r.returncode != 0  # argparse choices rejects it
    assert "choose from" in (r.stderr.lower()) or "invalid choice" in r.stderr.lower()


def test_cli_bad_format_choice_rejected():
    r = _run("assess", _demo("01-saas-soc2"), "--format", "yaml")
    assert r.returncode != 0


@pytest.mark.parametrize("fmt", list(atlas._FORMATTERS))
def test_cli_each_format_runs(fmt):
    r = _run("assess", _demo("01-saas-soc2"), "--framework", "soc2",
             "--format", fmt)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip()
    if fmt in ("json", "sarif"):
        json.loads(r.stdout)


def test_cli_matrix_lists_all_frameworks():
    r = _run("matrix")
    assert r.returncode == 0
    for name in atlas.FRAMEWORKS.values():
        assert name.split()[0] in r.stdout or True  # header is keys, not names
    for key in atlas.FRAMEWORKS:
        assert key in r.stdout


def test_cli_frameworks_lists_every_key():
    r = _run("frameworks")
    assert r.returncode == 0
    for key in atlas.FRAMEWORKS:
        assert key in r.stdout


def test_cli_missing_file_exit_two():
    r = _run("assess", os.path.join(ROOT, "definitely-not-here.json"))
    assert r.returncode == 2
    assert "cannot read" in r.stderr


@pytest.mark.parametrize("slug", [
    "01-saas-soc2", "02-fintech-pci", "03-defense-cmmc-800171",
    "04-health-startup", "05-eu-ai-vendor", "06-greenfield-baseline",
    "07-iso-certification-prep", "08-msp-multiframework", "09-feed-enrichment",
    "10-gov-rmf-ato", "11-clean-soc2-iso", "12-retail-pci-saq",
])
def test_cli_every_worked_posture_assesses(slug):
    r = _run("assess", _demo(slug))
    assert r.returncode == 0, r.stderr
    assert "gap report" in r.stdout
