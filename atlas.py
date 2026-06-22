"""atlas — turn the compliance-atlas crosswalks into an actionable gap report.

The repo ships a *master matrix* (``crosswalks/master-matrix.md``) that aligns
seven control **themes** across the frameworks teams actually get asked about
(SOC 2, ISO 27001, NIST CSF 2.0, 800-53 r5, 800-171, PCI DSS 4.0). This module
turns that static reference into something you can run in CI:

  1. You describe your control posture per theme in a small JSON file (a
     "posture" file) — see ``demos/`` for real, worked examples.
  2. ``atlas`` cross-walks your posture against the matrix and reports, **per
     framework**, which control groups are covered / partial / missing — so you
     "implement once, satisfy many".

It invents no requirements: every framework reference below is lifted verbatim
from ``crosswalks/master-matrix.md`` in this repo. It is a planning aid, not an
audit, and explicitly not legal advice.

Posture file (JSON)::

    {
      "org": "Acme Health, Inc.",
      "scope": ["soc2", "hipaa-adjacent"],
      "controls": {
        "Access control":            "implemented",
        "Crypto / data protection":  "partial",
        "Logging & monitoring":      "missing"
      }
    }

Status values: ``implemented`` | ``partial`` | ``missing`` | ``n/a``.
Any theme you omit is treated as ``missing`` (assess-by-default — silence is a gap).

CLI::

    python -m atlas assess demos/01-saas-soc2/posture.json
    python -m atlas assess posture.json --framework iso27001 --format markdown
    python -m atlas assess posture.json --format sarif > atlas.sarif
    python -m atlas matrix            # print the embedded theme matrix
    python -m atlas frameworks        # list known framework keys
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys

# --- The matrix, transcribed verbatim from crosswalks/master-matrix.md -------
# theme -> {framework_key: "control reference string"}
MATRIX: dict[str, dict[str, str]] = {
    "Access control": {
        "soc2": "CC6", "iso27001": "A.5/A.8", "nist-csf": "PR.AA",
        "800-53": "AC", "800-171": "3.1", "pci-dss": "Req 7-8",
    },
    "Crypto / data protection": {
        "soc2": "CC6", "iso27001": "A.8", "nist-csf": "PR.DS",
        "800-53": "SC", "800-171": "3.13", "pci-dss": "Req 3-4",
    },
    "Logging & monitoring": {
        "soc2": "CC7", "iso27001": "A.8", "nist-csf": "DE.CM",
        "800-53": "AU", "800-171": "3.3", "pci-dss": "Req 10",
    },
    "Incident response": {
        "soc2": "CC7", "iso27001": "A.5", "nist-csf": "RS",
        "800-53": "IR", "800-171": "3.6", "pci-dss": "Req 12",
    },
    "Change management": {
        "soc2": "CC8", "iso27001": "A.8", "nist-csf": "PR.PS",
        "800-53": "CM", "800-171": "3.4", "pci-dss": "Req 6",
    },
    "Risk management": {
        "soc2": "CC3", "iso27001": "Cl.6", "nist-csf": "ID.RA / GV.RM",
        "800-53": "RA", "800-171": "3.11", "pci-dss": "Req 12",
    },
    "Vendor / supply chain": {
        "soc2": "CC9", "iso27001": "A.5", "nist-csf": "GV.SC",
        "800-53": "SR", "800-171": "3.12", "pci-dss": "Req 12",
    },
}

FRAMEWORKS: dict[str, str] = {
    "soc2": "SOC 2 (TSC)",
    "iso27001": "ISO/IEC 27001:2022",
    "nist-csf": "NIST CSF 2.0",
    "800-53": "NIST 800-53 r5",
    "800-171": "NIST 800-171 (CUI)",
    "pci-dss": "PCI DSS 4.0",
}

VALID_STATUS = ("implemented", "partial", "missing", "n/a")

# status -> (severity for findings, SARIF level)
_SEVERITY = {
    "missing": ("high", "error"),
    "partial": ("medium", "warning"),
    "n/a": ("none", "note"),
    "implemented": ("none", "note"),
}


class PostureError(ValueError):
    """Raised when a posture file is malformed."""


def load_posture(path: str) -> dict:
    """Load and validate a posture JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise PostureError("posture file must be a JSON object")
    controls = data.get("controls", {})
    if not isinstance(controls, dict):
        raise PostureError("'controls' must be an object of theme -> status")
    for theme, status in controls.items():
        if theme not in MATRIX:
            raise PostureError(
                f"unknown theme {theme!r}; valid themes: {', '.join(MATRIX)}"
            )
        if status not in VALID_STATUS:
            raise PostureError(
                f"theme {theme!r} has invalid status {status!r}; "
                f"valid: {', '.join(VALID_STATUS)}"
            )
    return data


def assess(posture: dict, framework: str | None = None) -> list[dict]:
    """Cross-walk a posture against the matrix into a sorted list of findings.

    Each finding::

        {"theme","status","severity","framework","framework_name","control"}

    Themes absent from the posture are assessed as ``missing`` (silence == gap).
    Findings are ordered most-severe first, then by a stable theme/framework
    order so output is deterministic across runs.
    """
    controls = posture.get("controls", {})
    targets = [framework] if framework else list(FRAMEWORKS)
    for fw in targets:
        if fw not in FRAMEWORKS:
            raise PostureError(
                f"unknown framework {fw!r}; valid: {', '.join(FRAMEWORKS)}"
            )

    # deterministic ordering: severity rank, then theme order, then fw order
    sev_rank = {"high": 0, "medium": 1, "none": 2}
    theme_order = {t: i for i, t in enumerate(MATRIX)}
    fw_order = {f: i for i, f in enumerate(FRAMEWORKS)}

    findings: list[dict] = []
    for theme, mapping in MATRIX.items():
        status = controls.get(theme, "missing")
        severity, _ = _SEVERITY[status]
        for fw in targets:
            findings.append({
                "theme": theme,
                "status": status,
                "severity": severity,
                "framework": fw,
                "framework_name": FRAMEWORKS[fw],
                "control": mapping[fw],
            })
    findings.sort(key=lambda f: (
        sev_rank[f["severity"]], theme_order[f["theme"]], fw_order[f["framework"]]
    ))
    return findings


def summarize(findings: list[dict]) -> dict:
    """Roll findings up into counts by status and an overall coverage score."""
    by_status: dict[str, int] = {}
    themes_seen: dict[str, str] = {}
    for f in findings:
        themes_seen[f["theme"]] = f["status"]
    for status in themes_seen.values():
        by_status[status] = by_status.get(status, 0) + 1
    total = len(themes_seen) or 1
    # implemented = 1.0, partial = 0.5, n/a excluded from denominator
    scored = {t: s for t, s in themes_seen.items() if s != "n/a"}
    denom = len(scored) or 1
    score = sum(1.0 if s == "implemented" else 0.5 if s == "partial" else 0.0
                for s in scored.values()) / denom
    return {
        "themes": total,
        "by_status": by_status,
        "coverage": round(score, 3),
    }


# --- exporters ---------------------------------------------------------------

def to_table(findings: list[dict], posture: dict) -> str:
    summ = summarize(findings)
    org = posture.get("org", "(unnamed)")
    lines = [f"# compliance-atlas gap report — {org}",
             f"# coverage {summ['coverage']:.0%}  "
             f"({', '.join(f'{k}:{v}' for k, v in sorted(summ['by_status'].items()))})",
             ""]
    w_theme = max((len(f["theme"]) for f in findings), default=5)
    w_fw = max((len(f["framework"]) for f in findings), default=9)
    header = f"{'THEME':<{w_theme}}  {'STATUS':<11}  {'FRAMEWORK':<{w_fw}}  CONTROL"
    lines.append(header)
    lines.append("-" * len(header))
    for f in findings:
        lines.append(
            f"{f['theme']:<{w_theme}}  {f['status']:<11}  "
            f"{f['framework']:<{w_fw}}  {f['control']}"
        )
    return "\n".join(lines)


def to_json(findings: list[dict], posture: dict) -> str:
    return json.dumps({
        "tool": "compliance-atlas",
        "org": posture.get("org", ""),
        "scope": posture.get("scope", []),
        "summary": summarize(findings),
        "findings": findings,
    }, indent=2)


def to_csv(findings: list[dict], posture: dict) -> str:
    buf = io.StringIO()
    cols = ["theme", "status", "severity", "framework", "framework_name", "control"]
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for f in findings:
        w.writerow(f)
    return buf.getvalue()


def to_markdown(findings: list[dict], posture: dict) -> str:
    summ = summarize(findings)
    org = posture.get("org", "(unnamed)")
    out = [f"# Compliance-atlas gap report — {org}", "",
           f"**Coverage:** {summ['coverage']:.0%} · "
           + " · ".join(f"{k}: {v}" for k, v in sorted(summ['by_status'].items())),
           "", "| Theme | Status | Framework | Control |",
           "|---|---|---|---|"]
    for f in findings:
        out.append(f"| {f['theme']} | {f['status']} | {f['framework_name']} | `{f['control']}` |")
    out.append("")
    out.append("> Planning aid generated from `crosswalks/master-matrix.md`. Not legal advice.")
    return "\n".join(out)


def to_sarif(findings: list[dict], posture: dict) -> str:
    """SARIF 2.1.0 — surface gaps as static-analysis results in code scanners."""
    rules: dict[str, dict] = {}
    results = []
    for f in findings:
        if f["severity"] == "none":
            continue  # only gaps are results
        rule_id = f"theme/{f['theme']}".replace(" ", "_")
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": f["theme"].replace(" ", "").replace("/", ""),
                "shortDescription": {"text": f"Control theme: {f['theme']}"},
                "helpUri": "https://github.com/cognis-digital/compliance-atlas",
            }
        _, level = _SEVERITY[f["status"]]
        results.append({
            "ruleId": rule_id,
            "level": level,
            "message": {"text": (
                f"{f['theme']} is {f['status']} — affects "
                f"{f['framework_name']} control {f['control']}"
            )},
            "properties": {
                "framework": f["framework"],
                "control": f["control"],
                "status": f["status"],
            },
        })
    return json.dumps({
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "compliance-atlas",
                "informationUri": "https://github.com/cognis-digital/compliance-atlas",
                "version": _version(),
                "rules": list(rules.values()),
            }},
            "results": results,
        }],
    }, indent=2)


_FORMATTERS = {
    "table": to_table,
    "json": to_json,
    "csv": to_csv,
    "markdown": to_markdown,
    "sarif": to_sarif,
}


def _version() -> str:
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(here, "VERSION"), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "0.0.0"


# --- CLI ---------------------------------------------------------------------

def _cmd_assess(a: argparse.Namespace) -> int:
    try:
        posture = load_posture(a.posture)
        findings = assess(posture, framework=a.framework)
    except (PostureError, json.JSONDecodeError) as e:
        print(f"atlas: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"atlas: cannot read {a.posture}: {e}", file=sys.stderr)
        return 2
    if getattr(a, "enrich", False):
        # Augment 800-53 findings with real NIST SP 800-53 rev5 OSCAL family
        # titles + the count of ATT&CK techniques each family is documented to
        # mitigate (CTID crosswalk). Surfaces in json/csv/sarif output.
        import atlas_feeds
        try:
            atlas_feeds.enrich_findings(findings, offline=a.offline)
        except (FileNotFoundError, ConnectionError) as e:
            print(f"atlas: feed enrichment unavailable ({e}); run "
                  f"'atlas feeds update' first, or pass --offline with a cache",
                  file=sys.stderr)
            return 2
    out = _FORMATTERS[a.format](findings, posture)
    print(out)
    if a.fail_on_gap:
        gaps = [f for f in findings if f["severity"] != "none"]
        if gaps:
            return 1
    return 0


def _cmd_matrix(_a: argparse.Namespace) -> int:
    cols = list(FRAMEWORKS)
    hdr = f"{'THEME':<28}  " + "  ".join(f"{c:<12}" for c in cols)
    print(hdr)
    print("-" * len(hdr))
    for theme, mp in MATRIX.items():
        print(f"{theme:<28}  " + "  ".join(f"{mp[c]:<12}" for c in cols))
    return 0


def _cmd_frameworks(_a: argparse.Namespace) -> int:
    for k, v in FRAMEWORKS.items():
        print(f"{k:<12}  {v}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="atlas",
        description="cross-walk your control posture against the compliance-atlas matrix",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("assess", help="assess a posture JSON file against frameworks")
    a.add_argument("posture", help="path to a posture JSON file")
    a.add_argument("--framework", choices=list(FRAMEWORKS),
                   help="limit the report to one framework")
    a.add_argument("--format", choices=list(_FORMATTERS), default="table")
    a.add_argument("--fail-on-gap", action="store_true",
                   help="exit non-zero if any partial/missing theme exists (CI gate)")
    a.set_defaults(func=_cmd_assess)

    m = sub.add_parser("matrix", help="print the embedded theme matrix")
    m.set_defaults(func=_cmd_matrix)

    f = sub.add_parser("frameworks", help="list known framework keys")
    f.set_defaults(func=_cmd_frameworks)

    # --- feeds: real, edge/air-gap-deployable data-feed ingestion ------------
    a.add_argument("--enrich", action="store_true",
                   help="annotate 800-53 findings with real NIST OSCAL family "
                        "titles + ATT&CK techniques mitigated (uses bundled feeds)")
    a.add_argument("--offline", action="store_true",
                   help="with --enrich, serve feed data from the on-disk cache "
                        "only (air-gap); never touch the network")

    fe = sub.add_parser(
        "feeds",
        help="real public data feeds (NIST 800-53 OSCAL + ATT&CK crosswalk), "
             "edge/air-gap deployable")
    fsub = fe.add_subparsers(dest="feeds_cmd", required=True)
    fsub.add_parser("list", help="list this repo's relevant feeds")
    fsub.add_parser("update", help="fetch + cache the feeds (online)")
    fg = fsub.add_parser("get", help="print a cached/fetched feed")
    fg.add_argument("feed")
    fg.add_argument("--offline", action="store_true",
                    help="serve from cache only (air-gap); never touch the network")
    fen = fsub.add_parser(
        "enrich",
        help="resolve 800-53 family titles + ATT&CK technique coverage per theme")
    fen.add_argument("--offline", action="store_true",
                     help="serve from cache only (air-gap); never touch the network")
    fe.set_defaults(func=_cmd_feeds)
    return p


def _cmd_feeds(a: argparse.Namespace) -> int:
    import atlas_feeds
    return atlas_feeds.cli(a)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
