"""Scenario 6 - retail: a mixed posture across every severity band.

Audience: a retailer doing a PCI DSS 4.0 self-assessment while also answering
SOC 2 questionnaires from B2B partners. Unlike the all-clean or all-missing
demos, this posture is deliberately heterogeneous (implemented / partial /
missing), so it exercises every severity band the report can emit and shows the
cross-framework blast radius of each gap.

Real API: atlas.load_posture -> atlas.assess (no framework => all six) ->
findings grouped by severity, atlas.MATRIX for the per-framework crosswalk,
atlas.summarize. Posture: demos/12-retail-pci-saq.
"""
from _common import load, rule, print_summary, status_glyph
import atlas


def main() -> None:
    rule("RETAIL -> mixed posture: every severity band in one PCI + SOC 2 report")

    posture = load("12-retail-pci-saq")
    fws = atlas.scope_frameworks(posture)  # ["pci-dss", "soc2"] — known keys only
    print(f"\nOrg: {posture['org']}")
    print(f"Scope (known frameworks): {', '.join(atlas.FRAMEWORKS[f] for f in fws)}")

    # All frameworks, then roll up to one row per theme.
    findings = atlas.assess(posture)
    by_theme: dict[str, dict] = {}
    for f in findings:
        by_theme.setdefault(f["theme"], f)

    # Group by severity so the high gaps are unmistakable.
    bands = {"high": [], "medium": [], "none": []}
    for theme, f in by_theme.items():
        bands[f["severity"]].append((theme, f["status"]))

    labels = {"high": "HIGH  (missing)", "medium": "MEDIUM (partial)",
              "none": "OK    (implemented / n/a)"}
    print("\nFindings by severity band:\n")
    for sev in ("high", "medium", "none"):
        print(f"   {labels[sev]}")
        for theme, status in bands[sev]:
            print(f"      {status_glyph(status)} {theme}")
        if not bands[sev]:
            print("      (none)")

    print_summary(findings, posture)

    # Cross-framework blast radius of the worst gaps.
    print("\nBlast radius of the HIGH gaps (one fix clears every framework):")
    for theme, _ in bands["high"]:
        refs = atlas.MATRIX[theme]
        print(f"   {theme:<26} -> " + "  ".join(f"{k}:{v}" for k, v in refs.items()))


if __name__ == "__main__":
    main()
