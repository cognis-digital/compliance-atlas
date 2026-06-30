"""Scenario 4 - security engineers: turn a gap into real threat coverage.

Audience: a security engineer who is unmoved by "AC is missing". They want to
know *what adversary behavior* a missing control family leaves you exposed to.
This demo enriches the gap report with two REAL, authoritative public feeds,
served fully offline from the committed fixture cache (air-gap safe):

  * NIST SP 800-53 rev5 OSCAL catalog -> the official family TITLE + control count
  * CTID ATT&CK <-> 800-53 crosswalk   -> how many ATT&CK techniques each family
                                          is documented to MITIGATE

So "Logging & monitoring is missing" becomes "the AU family (Audit and
Accountability) you are not covering mitigates N ATT&CK techniques."

Real API: atlas_feeds.enrich_matrix / enrich_findings, offline=True against
tests/fixtures/cache. Posture: demos/09-feed-enrichment (air-gapped enclave).
"""
import os

import _common
from _common import load, rule, status_glyph
import atlas
import atlas_feeds


def main() -> None:
    rule("SECURITY ENGINEER -> 800-53 gaps as ATT&CK threat coverage (offline)")

    # Point the feed cache at the committed offline fixtures -> zero network.
    os.environ["COGNIS_FEEDS_CACHE"] = _common.FIXTURE_CACHE
    print(f"\nFeed cache (offline): {_common.FIXTURE_CACHE}")

    # 1) Whole-matrix enrichment: real NIST family titles + ATT&CK coverage.
    rows = atlas_feeds.enrich_matrix(atlas.MATRIX, offline=True)
    print("\nNIST 800-53 family coverage (real OSCAL titles + CTID ATT&CK crosswalk):\n")
    print(f"   {'THEME':<26} {'800-53':<7} {'FAMILY TITLE':<38} {'CTRLS':>5} {'ATT&CK':>7}")
    print("   " + "-" * 86)
    for r in rows:
        print(f"   {r['theme']:<26} {r['family_code']:<7} "
              f"{r['family_title']:<38} {r['control_count']:>5} {r['attack_techniques']:>7}")

    # 2) Fold it into THIS enclave's gap report — annotate the 800-53 findings.
    posture = load("09-feed-enrichment")
    findings = atlas.assess(posture, framework="800-53")
    atlas_feeds.enrich_findings(findings, offline=True)

    print(f"\nGap report for '{posture['org']}' — exposure on the gaps:\n")
    exposed = 0
    for f in findings:
        techs = f.get("attack_techniques", 0)
        note = ""
        if f["severity"] != "none":
            note = f"   <-- exposed to ~{techs} ATT&CK technique(s)"
            exposed += techs
        print(f"   {status_glyph(f['status'])} {f['theme']:<26} "
              f"{f['control']:<4} {f.get('family_title','')}{note}")

    print(f"\n   Prioritize by threat, not alphabet: the open 800-53 families above "
          f"leave ~{exposed} ATT&CK techniques unmitigated.")


if __name__ == "__main__":
    main()
