"""Scenario 1 - founders / startups chasing their first SOC 2.

Audience: a Series-B SaaS where enterprise deals stall in procurement without a
SOC 2 report. The founder/eng-lead has a rough sense of what is mature and what
is half-built. This demo turns that gut feel into a concrete, prioritized punch
list: which control themes are missing (stand up a *program*) vs partial (it's
an *evidence* problem), and what coverage number to quote the board.

Real API: atlas.load_posture -> atlas.assess(framework="soc2") -> findings,
plus atlas.summarize for the coverage score. Posture: demos/01-saas-soc2.
"""
from _common import load, rule, print_summary, status_glyph
import atlas


def main() -> None:
    rule("STARTUP -> FIRST SOC 2  -  turn a readiness gut-check into a punch list")

    posture = load("01-saas-soc2")
    print(f"\nOrg: {posture['org']}   target: SOC 2 (TSC)")

    findings = atlas.assess(posture, framework="soc2")

    print("\nGap report vs SOC 2 (most severe first):\n")
    for f in findings:
        print(f"   {status_glyph(f['status'])} {f['theme']:<26} "
              f"{f['status']:<12} SOC 2 {f['control']}")

    summ = print_summary(findings, posture)

    missing = [f["theme"] for f in findings if f["status"] == "missing"]
    partial = [f["theme"] for f in findings if f["status"] == "partial"]
    print("\nWhat the founder does Monday morning:")
    if missing:
        print(f"   1) STAND UP (net-new programs): {', '.join(missing)}")
    if partial:
        print(f"   2) PROVE (evidence/runbooks exist, make them samplable): "
              f"{', '.join(partial)}")
    print(f"   3) Quote the board: {summ['coverage']:.0%} of SOC 2 themes covered "
          f"today; close the gaps before the observation window opens.")


if __name__ == "__main__":
    main()
