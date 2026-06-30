"""Tests for the runnable Python demo scenarios under demos/.

These import each demo module and call its main(), asserting it completes
without error (and, for the feed-enrichment demo, fully offline). They guard
against the demos drifting away from the real atlas / atlas_feeds API.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")
FIXTURE_CACHE = os.path.join(ROOT, "tests", "fixtures", "cache")

SCENARIOS = [
    "01_startup_first_soc2",
    "02_grc_implement_once",
    "03_auditor_ci_gate",
    "04_security_engineer_threat_coverage",
    "05_greenfield_assess_by_default",
    "06_pci_mixed_severity",
    "07_export_formats_pipeline",
    "08_airgap_snapshot_roundtrip",
    "09_ato_partial_remediation",
]


@pytest.fixture(autouse=True)
def _demos_on_path(monkeypatch):
    monkeypatch.syspath_prepend(DEMOS)
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", FIXTURE_CACHE)
    yield


def test_run_all_module_present():
    assert os.path.exists(os.path.join(DEMOS, "run_all.py"))
    assert os.path.exists(os.path.join(DEMOS, "_common.py"))


@pytest.mark.parametrize("name", SCENARIOS)
def test_each_demo_main_runs(name, capsys):
    mod = importlib.import_module(name)
    mod.main()  # must not raise
    out = capsys.readouterr().out
    assert out.strip(), f"{name} produced no output"


def test_common_helpers_use_real_api():
    common = importlib.import_module("_common")
    # load() must round-trip a real worked posture through the real loader
    posture = common.load("01-saas-soc2")
    assert posture["org"]
    assert common.coverage_bar(0.5).endswith("50%")


def test_run_all_subprocess_exit_zero():
    """run_all.py must run all scenarios end to end and exit 0, offline."""
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1",
               COGNIS_FEEDS_CACHE=FIXTURE_CACHE)
    r = subprocess.run([sys.executable, os.path.join(DEMOS, "run_all.py")],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    assert r.returncode == 0, r.stderr
    assert "All demo scenarios completed." in r.stdout


# --- the scenario list is the single source of truth ------------------------

def test_run_all_scenarios_match_test_list():
    """run_all.SCENARIOS and this test module's SCENARIOS must not drift."""
    run_all = importlib.import_module("run_all")
    assert run_all.SCENARIOS == SCENARIOS


def test_at_least_nine_runnable_scenarios():
    assert len(SCENARIOS) >= 9


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_scenario_module_file_exists(name):
    assert os.path.exists(os.path.join(DEMOS, name + ".py")), name


@pytest.mark.parametrize("name", SCENARIOS)
def test_each_scenario_has_module_docstring(name):
    mod = importlib.import_module(name)
    assert mod.__doc__ and mod.__doc__.strip(), f"{name} lacks a docstring"


@pytest.mark.parametrize("name", SCENARIOS)
def test_each_scenario_exposes_main_callable(name):
    mod = importlib.import_module(name)
    assert callable(getattr(mod, "main", None)), f"{name} has no main()"


# Scenarios whose output legitimately varies run-to-run (e.g. a fresh temp dir
# for the air-gap snapshot). They are still required to run twice without error.
_NONDETERMINISTIC = {"08_airgap_snapshot_roundtrip"}


@pytest.mark.parametrize("name", SCENARIOS)
def test_each_scenario_main_is_repeatable(name, capsys):
    """Running a scenario twice must not raise; deterministic ones match exactly."""
    mod = importlib.import_module(name)
    mod.main()
    first = capsys.readouterr().out
    mod.main()
    second = capsys.readouterr().out
    assert first.strip() and second.strip()
    if name not in _NONDETERMINISTIC:
        assert first == second, f"{name} is not idempotent"


def test_run_all_main_returns_zero_in_process(monkeypatch):
    monkeypatch.setenv("COGNIS_FEEDS_CACHE", FIXTURE_CACHE)
    run_all = importlib.import_module("run_all")
    assert run_all.main() == 0


def test_export_formats_demo_runs_offline(capsys):
    mod = importlib.import_module("07_export_formats_pipeline")
    mod.main()
    out = capsys.readouterr().out
    assert "[sarif" in out and "[csv" in out and "[json" in out


def test_airgap_demo_does_roundtrip(capsys):
    mod = importlib.import_module("08_airgap_snapshot_roundtrip")
    mod.main()
    out = capsys.readouterr().out
    assert "exported" in out and "imported" in out
    assert "Air-gap round-trip complete" in out
