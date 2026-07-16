"""Scenario 6 - GRC lead tracking progress: scaffold, plan, and measure drift.

Audience: a GRC / compliance lead who has to *show movement* quarter over
quarter, not just a single snapshot. This demo drives three v0.2 capabilities,
all on the real API and real worked postures (nothing mocked, no network):

  * atlas.new_posture_template  -> scaffold a valid posture skeleton to hand a team
  * atlas.remediation_plan      -> rank the open gaps by coverage upside
  * atlas.diff_postures         -> measure drift between two point-in-time snapshots

"Before" is the greenfield baseline (everything missing); "after" is a Series-B
SaaS partway through its first SOC 2. The coverage delta is the story you tell
the board.
"""
import _common  # noqa: F401  (imported for its sys.path shim; used via load/rule below)
from _common import load, rule

import atlas


def main() -> None:
    rule("GRC LEAD -> scaffold a posture, plan the gaps, measure drift over time")

    # 1) Scaffold: hand a new team a valid, fully-populated posture to edit.
    tmpl = atlas.new_posture_template(org="Example Corp", status="missing")
    print(f"\nScaffolded a posture skeleton for '{tmpl['org']}' with "
          f"{len(tmpl['controls'])} themes (all 'missing' until filled in).")

    # 2) Plan: rank THIS quarter's real posture by remediation priority.
    current = load("01-saas-soc2")
    plan = atlas.remediation_plan(current)
    print(f"\nRemediation plan for '{plan['org']}' — coverage {plan['coverage']:.0%}, "
          f"{plan['open_gaps']} open gap(s), most impactful first:\n")
    for it in plan["plan"]:
        print(f"   {it['step']:>2}. [{it['priority']:<6}] {it['theme']} "
              f"({it['status']} -> implemented, +{it['coverage_gain']:.0%})")

    # 3) Drift: greenfield baseline -> this quarter. Show what moved.
    baseline = load("06-greenfield-baseline")
    d = atlas.diff_postures(baseline, current)
    sign = "+" if d["coverage_delta"] >= 0 else ""
    print(f"\nDrift, baseline -> current: coverage {d['coverage_from']:.0%} -> "
          f"{d['coverage_to']:.0%} ({sign}{d['coverage_delta']:.0%})  "
          f"[improved:{len(d['improved'])} regressed:{len(d['regressed'])} "
          f"unchanged:{len(d['unchanged'])}]")
    for r in d["improved"]:
        print(f"   ^ {r['theme']:<26} {r['from']} -> {r['to']}")
    if not d["regressed"]:
        print("\n   No regressions — every theme held or improved. Ship the board update.")


if __name__ == "__main__":
    main()
