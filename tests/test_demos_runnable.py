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
    """run_all.py must run all five scenarios end to end and exit 0, offline."""
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1",
               COGNIS_FEEDS_CACHE=FIXTURE_CACHE)
    r = subprocess.run([sys.executable, os.path.join(DEMOS, "run_all.py")],
                       capture_output=True, text=True, cwd=ROOT, env=env)
    assert r.returncode == 0, r.stderr
    assert "All demo scenarios completed." in r.stdout
