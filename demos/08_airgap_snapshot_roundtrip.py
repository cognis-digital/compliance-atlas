"""Scenario 8 - air-gap: move the feed cache over sneakernet, then enrich offline.

Audience: an operator standing up compliance-atlas inside an air-gapped enclave.
They cannot reach NIST/CTID from inside, so they export the feed cache to a
single snapshot archive on a connected host, carry it across, import it into the
enclave's cache, and then run enrichment fully offline. This demo performs that
exact round-trip end to end (using the committed fixture cache as the "connected
host" source and a throwaway temp dir as the "enclave"), so it needs no network.

Real API: datafeeds.snapshot_export / snapshot_import, atlas_feeds.enrich_matrix
(offline=True). Posture: demos/09-feed-enrichment.
"""
import os
import tempfile

import _common
from _common import rule
import atlas
import atlas_feeds
import datafeeds


def main() -> None:
    rule("AIR-GAP -> snapshot the feed cache, import in the enclave, enrich offline")

    work = tempfile.mkdtemp(prefix="atlas-airgap-")
    snapshot = os.path.join(work, "feeds-snapshot.tar.gz")
    enclave_cache = os.path.join(work, "enclave-cache")

    # 1) On the connected host: export the cache to one portable archive.
    os.environ["COGNIS_FEEDS_CACHE"] = _common.FIXTURE_CACHE
    n = datafeeds.snapshot_export(snapshot)
    size = os.path.getsize(snapshot)
    print(f"\n1) exported {n} cached feed(s) -> {os.path.basename(snapshot)} "
          f"({size} bytes)")
    assert n >= len(atlas_feeds.RELEVANT_FEEDS)

    # 2) In the enclave: fresh empty cache, import the archive over 'sneakernet'.
    os.environ["COGNIS_FEEDS_CACHE"] = enclave_cache
    imported = datafeeds.snapshot_import(snapshot)
    print(f"2) imported {imported} feed(s) into the enclave cache "
          f"({enclave_cache})")

    # 3) Enrich the matrix offline from the freshly-imported enclave cache.
    rows = atlas_feeds.enrich_matrix(atlas.MATRIX, offline=True)
    print("\n3) offline enrichment from the imported cache (zero network):\n")
    print(f"   {'THEME':<26} {'800-53':<7} {'FAMILY TITLE':<38} {'ATT&CK':>7}")
    print("   " + "-" * 80)
    for r in rows:
        print(f"   {r['theme']:<26} {r['family_code']:<7} "
              f"{r['family_title']:<38} {r['attack_techniques']:>7}")

    assert len(rows) == len(atlas.MATRIX)
    assert all(r["family_title"] for r in rows), "every family must resolve offline"
    print("\n   Air-gap round-trip complete: cache moved as one file, enrichment "
          "served entirely from the enclave's copy.")


if __name__ == "__main__":
    main()
