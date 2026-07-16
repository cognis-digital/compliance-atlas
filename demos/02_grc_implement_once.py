"""Scenario 2 - GRC / compliance leads running one program for many frameworks.

Audience: an MSP (or any multi-tenant shop) that must answer to SOC 2, ISO 27001,
NIST CSF, 800-53, 800-171 AND PCI DSS off a single shared control baseline. The
whole point of compliance-atlas is "implement once, satisfy many": one control
theme maps to a control group in every framework at once. This demo proves it —
one posture, assessed against all six frameworks, with the cross-framework blast
radius of each remaining gap made explicit.

Real API: atlas.assess(posture) over every framework, atlas.MATRIX for the
crosswalk, atlas.summarize for coverage. Posture: demos/08-msp-multiframework.
"""
from _common import load, print_summary, rule

import atlas


def main() -> None:
    rule("GRC LEAD -> IMPLEMENT ONCE, SATISFY MANY  -  one posture, six frameworks")

    posture = load("08-msp-multiframework")
    print(f"\nOrg: {posture['org']}")
    print(f"Scope: {', '.join(atlas.FRAMEWORKS[f] for f in posture['scope'])}")

    findings = atlas.assess(posture)  # no framework => all six

    # Roll the per-(theme,framework) findings up to one row per theme, showing
    # the control reference in every framework it lights up at once.
    print("\nShared baseline — each theme, the same control across all frameworks:\n")
    seen: set[str] = set()
    for f in findings:
        theme = f["theme"]
        if theme in seen:
            continue
        seen.add(theme)
        refs = atlas.MATRIX[theme]
        crosswalk = "  ".join(f"{k}:{v}" for k, v in refs.items())
        flag = "" if f["status"] == "implemented" else f"   <-- {f['status'].upper()}"
        print(f"   {theme:<26} {crosswalk}{flag}")

    print_summary(findings, posture)

    # The leverage: every gap is a gap in MANY frameworks simultaneously.
    gaps = sorted({f["theme"] for f in findings if f["severity"] != "none"})
    print("\nWhy this saves audits:")
    for theme in gaps:
        n = len(atlas.MATRIX[theme])
        print(f"   Fixing '{theme}' closes a finding in all {n} frameworks at once.")
    if not gaps:
        print("   No gaps — the shared baseline satisfies all six frameworks.")


if __name__ == "__main__":
    main()
