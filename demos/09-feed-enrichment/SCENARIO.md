# Demo 09 — Feed enrichment (real NIST 800-53 + ATT&CK), edge / air-gap

The static theme matrix only knows a NIST 800-53 **family code** per theme
(`AC`, `SC`, `AU`, ...). This demo layers in two **real, authoritative public
feeds**, fetched keyless over HTTPS, cached to disk, and re-served offline:

- **`oscal-800-53-rev5-catalog`** — NIST's official SP 800-53 rev5 catalog in
  OSCAL JSON (`usnistgov/oscal-content`). Resolves each family code to its
  official **title** and the real controls under it.
- **`attack-nist-mappings`** — the Center for Threat-Informed Defense crosswalk
  of MITRE ATT&CK techniques to 800-53 controls. Counts how many distinct
  adversary **techniques** each family is documented to *mitigate*.

So a gap report stops being "AC is missing" and becomes "**Access Control**
(AC) is missing — and that family mitigates *N* ATT&CK techniques you are
currently exposed to."

## Run it (online — fetches + caches both feeds)

```bash
python -m atlas feeds update
python -m atlas feeds enrich
```

## Run it OFFLINE / air-gapped (serve from cache, no network)

```bash
# point at a pre-seeded cache (e.g. a snapshot copied onto the air-gapped host)
export COGNIS_FEEDS_CACHE=/path/to/cache
python -m atlas feeds enrich --offline
python -m atlas assess posture.json --framework 800-53 --format json --enrich --offline
```

This very demo runs against the trimmed feed cache committed under
`tests/fixtures/cache/`, so it works with zero network:

```bash
COGNIS_FEEDS_CACHE=tests/fixtures/cache \
  python -m atlas feeds enrich --offline
```

## Sneakernet to an enclave

```bash
python -m datafeeds snapshot-export feeds.tar.gz   # on a connected host
# ... carry feeds.tar.gz across the air gap ...
COGNIS_FEEDS_CACHE=/srv/cache python -m datafeeds snapshot-import feeds.tar.gz
```

Defensive / authorized-use intelligence only. Planning aid, not legal advice.
