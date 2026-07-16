"""Run every runnable demo scenario end to end.

    python demos/run_all.py

Each scenario drives the real compliance-atlas API against a worked posture file
and is fully self-contained and offline (feed enrichment reads the committed
fixture cache), so they can be run in any order or on their own.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCENARIOS = [
    "01_startup_first_soc2",
    "02_grc_implement_once",
    "03_auditor_ci_gate",
    "04_security_engineer_threat_coverage",
    "05_greenfield_assess_by_default",
    "06_track_drift_and_plan",
]


def main() -> int:
    for name in SCENARIOS:
        mod = importlib.import_module(name)
        mod.main()
    print("\n" + "=" * 72)
    print("  All demo scenarios completed.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
