# Demo 10 — Gov cloud SaaS prepping an RMF / ATO package (800-53 Moderate)

**Where the data came from.** A cloud provider chasing an Authority to Operate
(ATO) under the NIST Risk Management Framework at the **Moderate** baseline. The
SSP author has stood up the heavy access/crypto/IR families but is still
collecting audit-log evidence and tightening change control; supply-chain (SR)
is mid-rollout. The posture is scoped to `800-53` and `nist-csf` with an
`rmf-moderate` adjacency tag (a non-framework tag the loader accepts and
`atlas.scope_frameworks` filters out).

**What to expect.** Assessed against `--framework 800-53`, three themes are
`partial` (medium) and the rest `implemented`. Enriched with the bundled OSCAL +
ATT&CK feeds (offline), the open **Logging & monitoring (AU)** and **Change
management (CM)** families resolve to their official NIST titles and the count
of ATT&CK techniques they mitigate — so the assessor prioritizes by threat, not
alphabetically. Coverage lands well above 0% but short of clean.

**Run it.**

```bash
# 800-53 view
python -m atlas assess demos/10-gov-rmf-ato/posture.json --framework 800-53

# enrich with real OSCAL family titles + ATT&CK coverage (offline cache)
COGNIS_FEEDS_CACHE=tests/fixtures/cache \
  python -m atlas assess demos/10-gov-rmf-ato/posture.json \
  --framework 800-53 --format json --enrich --offline
```

**How to act.** The three `partial` families are evidence/maturity gaps, not
net-new programs — finish AU log retention + CM ticket linkage + SR vendor
attestations to clear the ATO assessor's findings. Wire `--fail-on-gap` into the
ConMon pipeline so a re-opened control blocks the next package.
