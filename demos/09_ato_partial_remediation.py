"""Scenario 9 - gov ATO: prioritize partial 800-53 families by threat, not alphabet.

Audience: an SSP author assembling an RMF / ATO package at the 800-53 Moderate
baseline. The heavy families are already implemented; what remains are a few
*partial* families. This demo enriches just those open families with the real
NIST OSCAL titles and the count of ATT&CK techniques each one mitigates (offline,
from the committed fixture cache), so the assessor can sequence the remaining
work by adversary exposure rather than by control id.

Real API: atlas.assess(framework="800-53"), atlas_feeds.enrich_findings
(offline=True), atlas.summarize. Posture: demos/10-gov-rmf-ato.
"""
import os

import _common
from _common import load, rule, status_glyph
import atlas
import atlas_feeds


def main() -> None:
    rule("GOV ATO -> rank the remaining partial 800-53 families by ATT&CK exposure")

    os.environ["COGNIS_FEEDS_CACHE"] = _common.FIXTURE_CACHE
    posture = load("10-gov-rmf-ato")
    print(f"\nOrg: {posture['org']}")

    findings = atlas.assess(posture, framework="800-53")
    atlas_feeds.enrich_findings(findings, offline=True)
    summ = atlas.summarize(findings)
    print(f"Baseline coverage vs 800-53: {summ['coverage']:.0%} "
          f"(Moderate ATO target)\n")

    # Only the still-open families need work; sort them most-exposed first.
    open_families = [f for f in findings if f["severity"] != "none"]
    open_families.sort(key=lambda f: f.get("attack_techniques", 0), reverse=True)

    print("Remaining work, ranked by ATT&CK techniques each open family mitigates:\n")
    print(f"   {'THEME':<26} {'FAMILY':<6} {'TITLE':<38} {'ATT&CK':>7}")
    print("   " + "-" * 80)
    total_exposed = 0
    for f in open_families:
        techs = f.get("attack_techniques", 0)
        total_exposed += techs
        print(f"   {status_glyph(f['status'])}{f['theme']:<24} {f['control']:<6} "
              f"{f.get('family_title',''):<38} {techs:>7}")

    if open_families:
        worst = open_families[0]
        print(f"\n   Close '{worst['theme']}' ({worst['control']}) first: it "
              f"mitigates the most ATT&CK techniques ({worst.get('attack_techniques',0)}) "
              f"of any open family.")
        print(f"   {len(open_families)} open families leave ~{total_exposed} "
              f"techniques under-mitigated until the ATO package is complete.")
    else:
        print("\n   No open families — the 800-53 Moderate baseline is clean.")


if __name__ == "__main__":
    main()
