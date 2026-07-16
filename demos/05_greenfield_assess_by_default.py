"""Scenario 5 - pre-seed / greenfield: assess-by-default (silence is a gap).

Audience: a founder at day zero with *no* controls written down yet, picking a
target framework to anchor a roadmap. compliance-atlas treats an omitted theme
as `missing` on purpose — silence is a gap, so an empty posture honestly returns
a 0%-coverage roadmap rather than a misleading blank.

This demo runs the empty greenfield posture against NIST CSF 2.0, then shows how
the same matrix gives you a starting blueprint: the control reference to read
first for each theme, in every framework, so the roadmap is portable if the
target later changes.

Real API: atlas.assess on an empty posture, atlas.MATRIX, atlas.to_markdown for
a roadmap artifact. Posture: demos/06-greenfield-baseline.
"""
from _common import load, print_summary, rule

import atlas


def main() -> None:
    rule("GREENFIELD -> assess-by-default  -  an empty posture is a 0% roadmap")

    posture = load("06-greenfield-baseline")
    print(f"\nOrg: {posture['org']}   controls declared: {len(posture['controls'])}")
    print("Every theme is unstated -> assessed as 'missing' (silence == gap).")

    framework = posture["scope"][0]  # "nist-csf"
    findings = atlas.assess(posture, framework=framework)

    print(f"\nDay-zero roadmap vs {atlas.FRAMEWORKS[framework]} "
          f"(read these control groups first):\n")
    for f in findings:
        print(f"   [ ] {f['theme']:<26} -> {atlas.FRAMEWORKS[framework]} {f['control']}")

    summ = print_summary(findings, posture)
    assert summ["coverage"] == 0.0  # honest: nothing implemented yet

    # The roadmap is portable: the same theme anchors a control in every
    # framework, so picking a different target later reuses the work.
    print("\nPortable across frameworks — pick any target, the themes don't change:")
    sample = next(iter(atlas.MATRIX))
    refs = atlas.MATRIX[sample]
    print(f"   e.g. '{sample}' starts at: "
          + ", ".join(f"{atlas.FRAMEWORKS[k]} {v}" for k, v in refs.items()))

    # Emit a real Markdown artifact a founder can paste into a planning doc.
    md = atlas.to_markdown(findings, posture)
    print(f"\n   (atlas.to_markdown produced a {len(md.splitlines())}-line "
          f"roadmap artifact ready to paste into a planning doc.)")


if __name__ == "__main__":
    main()
