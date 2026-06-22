"""atlas_feeds — wire the bundled edge/air-gap data-feed layer into compliance-atlas.

compliance-atlas cross-walks a control posture against a hand-transcribed theme
matrix (``crosswalks/master-matrix.md``). The static matrix only knows the
*family code* for NIST 800-53 (e.g. ``AC``, ``SC``, ``AU``). This module pulls
**real, authoritative public feeds** to turn those codes into something richer:

  * ``oscal-800-53-rev5-catalog`` — NIST's official SP 800-53 rev5 catalog in
    OSCAL JSON. Resolves a family code -> the official family **title** and the
    real list of controls under it.
  * ``attack-nist-mappings`` — the Center for Threat-Informed Defense crosswalk
    of MITRE ATT&CK techniques to 800-53 controls. Lets us count how many
    distinct adversary **techniques** each 800-53 family is documented to
    *mitigate* — a real "threat coverage" signal layered onto the gap report.

It uses the bundled :mod:`datafeeds` module (stdlib-only, keyless fetch -> disk
cache -> offline re-serve -> air-gap snapshot). This repo only ever touches the
two feeds in :data:`RELEVANT_FEEDS`; the rest of the 17-feed catalog is hidden.

Edge / air-gap:
  * ``--offline`` serves from the on-disk cache and never touches the network.
  * ``COGNIS_FEEDS_CACHE`` points the cache anywhere (e.g. a pre-seeded snapshot
    on an air-gapped host). ``datafeeds snapshot-export/-import`` move the cache
    over sneakernet.

Defensive / authorized-use intelligence only. Not legal advice.

CLI (exposed through ``atlas`` as ``feeds``)::

    python -m atlas feeds list [--offline]
    python -m atlas feeds update                 # fetch + cache both feeds
    python -m atlas feeds get oscal-800-53-rev5-catalog [--offline]
    python -m atlas feeds enrich [--offline]     # 800-53 titles + ATT&CK coverage
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

import datafeeds

# This repo's domain: only the compliance feeds it actually consumes.
RELEVANT_FEEDS = ["oscal-800-53-rev5-catalog", "attack-nist-mappings"]


def _relevant_catalog() -> dict:
    """The bundled feed catalog filtered to just this repo's feeds."""
    full = datafeeds.load_catalog()
    feeds = [f for f in full.get("feeds", []) if f["id"] in RELEVANT_FEEDS]
    return {"feeds": feeds}


def relevant_feeds() -> list[dict]:
    return datafeeds.list_feeds(catalog=_relevant_catalog())


def _get(feed_id: str, *, offline: bool) -> Any:
    if feed_id not in RELEVANT_FEEDS:
        raise KeyError(f"{feed_id!r} is not a compliance-atlas feed; "
                       f"valid: {', '.join(RELEVANT_FEEDS)}")
    return datafeeds.get(feed_id, offline=offline, catalog=_relevant_catalog())


# --------------------------------------------------------------------------- #
# enrichment: 800-53 family titles (OSCAL) + ATT&CK technique coverage
# --------------------------------------------------------------------------- #
def oscal_family_index(catalog: dict) -> dict[str, dict]:
    """Index the OSCAL 800-53 catalog by family code (lowercased group id).

    Returns ``{ "ac": {"title": "Access Control", "controls": [...ids...] } }``.
    """
    out: dict[str, dict] = {}
    for group in catalog.get("catalog", {}).get("groups", []):
        gid = str(group.get("id", "")).lower()
        if not gid:
            continue
        controls = [c.get("id", "") for c in group.get("controls", [])]
        out[gid] = {"title": group.get("title", ""), "controls": controls}
    return out


def attack_coverage_by_family(mappings: dict) -> dict[str, int]:
    """Count distinct ATT&CK techniques each 800-53 family is mapped to mitigate.

    Keyed by lowercased family code (``ac``, ``sc``, ...).
    """
    by_family: dict[str, set] = {}
    for m in mappings.get("mapping_objects", []):
        if m.get("status") not in ("complete", "mappable"):
            continue
        cap = m.get("capability_id") or ""
        tech = m.get("attack_object_id")
        if not cap or not tech:
            continue
        fam = cap.split("-")[0].lower()
        by_family.setdefault(fam, set()).add(tech)
    return {fam: len(techs) for fam, techs in by_family.items()}


def enrich_matrix(matrix: dict, *, offline: bool = False) -> list[dict]:
    """For every theme in ``matrix``, resolve its 800-53 family code against the
    real OSCAL catalog (official title + control count) and the CTID ATT&CK
    crosswalk (distinct techniques mitigated).

    Returns one row per theme::

        {"theme","family_code","family_title","control_count","attack_techniques"}
    """
    oscal = _get("oscal-800-53-rev5-catalog", offline=offline)
    mappings = _get("attack-nist-mappings", offline=offline)
    fam_index = oscal_family_index(oscal)
    coverage = attack_coverage_by_family(mappings)

    rows: list[dict] = []
    for theme, fw_map in matrix.items():
        code = str(fw_map.get("800-53", "")).strip()
        fam = code.lower()
        info = fam_index.get(fam, {})
        rows.append({
            "theme": theme,
            "family_code": code,
            "family_title": info.get("title", "(not in catalog)"),
            "control_count": len(info.get("controls", [])),
            "attack_techniques": coverage.get(fam, 0),
        })
    return rows


def enrich_findings(findings: list[dict], *, offline: bool = False) -> list[dict]:
    """Annotate ``atlas.assess`` findings in place with real 800-53 + ATT&CK data.

    Adds ``family_title`` and ``attack_techniques`` to every finding whose
    framework is ``800-53`` (others are passed through untouched).
    """
    oscal = _get("oscal-800-53-rev5-catalog", offline=offline)
    mappings = _get("attack-nist-mappings", offline=offline)
    fam_index = oscal_family_index(oscal)
    coverage = attack_coverage_by_family(mappings)
    for f in findings:
        if f.get("framework") != "800-53":
            continue
        fam = str(f.get("control", "")).split("(")[0].strip().lower()
        info = fam_index.get(fam, {})
        f["family_title"] = info.get("title", "")
        f["attack_techniques"] = coverage.get(fam, 0)
    return findings


def render_enrichment(rows: list[dict]) -> str:
    w_theme = max((len(r["theme"]) for r in rows), default=5)
    w_title = max((len(r["family_title"]) for r in rows), default=12)
    header = (f"{'THEME':<{w_theme}}  {'800-53':<7}  {'FAMILY TITLE':<{w_title}}  "
              f"{'CTRLS':>5}  {'ATT&CK TECHNIQUES MITIGATED':>27}")
    lines = ["# compliance-atlas feed enrichment "
             "(NIST SP 800-53 rev5 OSCAL + CTID ATT&CK crosswalk)",
             header, "-" * len(header)]
    for r in rows:
        lines.append(
            f"{r['theme']:<{w_theme}}  {r['family_code']:<7}  "
            f"{r['family_title']:<{w_title}}  {r['control_count']:>5}  "
            f"{r['attack_techniques']:>27}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI (invoked by atlas' `feeds` subcommand)
# --------------------------------------------------------------------------- #
def cli(args) -> int:
    import atlas  # local import to avoid a cycle at module import time

    sub = args.feeds_cmd
    if sub == "list":
        for f in relevant_feeds():
            age = datafeeds.cached_age_hours(f["id"])
            fresh = "uncached" if age is None else f"{age:.1f}h old"
            print(f"  {f['id']:30} {f.get('domain',''):11} [{fresh}]  {f['name']}")
        return 0
    if sub == "update":
        cat = _relevant_catalog()
        for fid in RELEVANT_FEEDS:
            try:
                p = datafeeds.update(fid, catalog=cat)
                print(f"  updated {fid} -> {p} ({p.stat().st_size} bytes)")
            except (KeyError, ConnectionError) as e:
                print(f"  {fid}: {e}", file=sys.stderr)
                return 1
        return 0
    if sub == "get":
        try:
            data = _get(args.feed, offline=args.offline)
        except (KeyError, FileNotFoundError, ConnectionError) as e:
            print(f"atlas feeds: {e}", file=sys.stderr)
            return 1
        print(json.dumps(data, indent=2)[:4000])
        return 0
    if sub == "enrich":
        try:
            rows = enrich_matrix(atlas.MATRIX, offline=args.offline)
        except (FileNotFoundError, ConnectionError) as e:
            print(f"atlas feeds: {e}", file=sys.stderr)
            return 1
        print(render_enrichment(rows))
        return 0
    return 1
