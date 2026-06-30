"""Scenario 7 - tooling: one posture, every export format, machine-checked.

Audience: a platform/DevEx engineer wiring compliance-atlas into a pipeline who
needs to know each exporter is real and parseable: the JSON and SARIF outputs
must round-trip through a parser, the CSV must have one data row per finding plus
a header, and markdown/table must be non-empty. This demo runs all five
exporters over a single worked posture and asserts their structural invariants —
the same guarantees the tests pin, shown as a runnable walkthrough.

Real API: atlas.assess + every exporter in atlas._FORMATTERS, plus
atlas.summarize. Posture: demos/04-health-startup.
"""
import csv
import io
import json

from _common import load, rule
import atlas


def main() -> None:
    rule("TOOLING -> one posture, five exporters, each machine-checked")

    posture = load("04-health-startup")
    findings = atlas.assess(posture, framework="soc2")
    summ = atlas.summarize(findings)
    print(f"\nOrg: {posture['org']}   coverage: {summ['coverage']:.0%}   "
          f"findings: {len(findings)}")

    # table / markdown — human formats, must be non-empty multi-line text.
    for fmt in ("table", "markdown"):
        out = atlas._FORMATTERS[fmt](findings, posture)
        assert out.strip() and "\n" in out
        print(f"\n   [{fmt:<8}] {len(out.splitlines())} lines, "
              f"{len(out)} chars  OK")

    # csv — header + exactly one row per finding.
    csv_out = atlas.to_csv(findings, posture)
    rows = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(rows) == len(findings)
    assert set(rows[0]) >= {"theme", "status", "severity", "framework", "control"}
    print(f"\n   [csv     ] {len(rows)} data rows (1 per finding) + header  OK")

    # json — parses; summary + findings present; finding count matches.
    jd = json.loads(atlas.to_json(findings, posture))
    assert jd["tool"] == "compliance-atlas"
    assert len(jd["findings"]) == len(findings)
    assert jd["summary"]["coverage"] == summ["coverage"]
    print(f"   [json    ] parsed; {len(jd['findings'])} findings, "
          f"coverage {jd['summary']['coverage']:.0%}  OK")

    # sarif — parses; version 2.1.0; results == count of real gaps.
    sd = json.loads(atlas.to_sarif(findings, posture))
    run = sd["runs"][0]
    gaps = sum(1 for f in findings if f["severity"] != "none")
    assert sd["version"] == "2.1.0"
    assert len(run["results"]) == gaps
    print(f"   [sarif   ] v{sd['version']}; {len(run['results'])} results "
          f"= {gaps} gaps, {len(run['tool']['driver']['rules'])} rules  OK")

    print("\n   All five exporters produced valid, structurally-checked output.")


if __name__ == "__main__":
    main()
