"""Scenario 3 - auditors & CI: prove a clean run, and gate on regressions.

Audience: an auditor (or the audit-prep engineer) who needs two things to be
*mechanical*, not subjective: (1) show that a posture is clean against the target
framework, and (2) wire the same check into CI as a SARIF feed + a fail-on-gap
gate so a regression that re-opens a control can never be merged silently.

This demo contrasts two real worked postures: a clean ISO 27001 stage-2 run
(07-iso-certification-prep) and a not-yet-ready posture (01-saas-soc2). It shows
the exact exit codes `--fail-on-gap` would return, and emits real SARIF 2.1.0
that a code-scanning dashboard can ingest.

Real API: atlas.assess, atlas.to_sarif, atlas.summarize. No fabricated results.
"""
import json

from _common import load, rule
import atlas


def _gate(slug: str, framework: str) -> None:
    posture = load(slug)
    findings = atlas.assess(posture, framework=framework)
    gaps = [f for f in findings if f["severity"] != "none"]
    exit_code = 1 if gaps else 0  # exactly what --fail-on-gap returns
    summ = atlas.summarize(findings)
    verdict = "BLOCK MERGE" if gaps else "PASS"
    print(f"\n   {posture['org']}")
    print(f"     framework      : {atlas.FRAMEWORKS[framework]}")
    print(f"     coverage       : {summ['coverage']:.0%}")
    print(f"     open gaps      : {len(gaps)}")
    print(f"     --fail-on-gap  : exit {exit_code}  ({verdict})")


def main() -> None:
    rule("AUDITOR / CI -> clean-run proof + SARIF gate on regressions")

    print("\nGate two postures against their target framework (CI semantics):")
    _gate("07-iso-certification-prep", "iso27001")  # clean -> exit 0
    _gate("01-saas-soc2", "soc2")                    # gaps  -> exit 1

    # Emit real SARIF for the not-ready posture — the artifact a code-scanning /
    # GRC dashboard ingests. Only gaps become results; "none" findings drop out.
    posture = load("01-saas-soc2")
    findings = atlas.assess(posture, framework="soc2")
    sarif = json.loads(atlas.to_sarif(findings, posture))
    run = sarif["runs"][0]
    print(f"\nSARIF 2.1.0 artifact ({run['tool']['driver']['name']} "
          f"v{run['tool']['driver']['version']}): "
          f"{len(run['results'])} result(s), "
          f"{len(run['tool']['driver']['rules'])} rule(s)")
    for r in run["results"][:4]:
        print(f"   [{r['level']:<7}] {r['ruleId']:<28} {r['message']['text']}")
    print("\n   Upload atlas.sarif in CI; an auditor reviews the exact same "
          "deterministic findings, not a screenshot.")


if __name__ == "__main__":
    main()
