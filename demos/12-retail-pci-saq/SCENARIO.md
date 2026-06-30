# Demo 12 — Retail e-commerce: a mixed posture across PCI DSS 4.0 + SOC 2

**Where the data came from.** A mid-size online retailer completing a PCI DSS 4.0
self-assessment (SAQ-A-EP) while also fielding SOC 2 questionnaires from B2B
partners. The posture is deliberately **mixed** — a bit of everything:
`implemented`, `partial`, and `missing` themes — to exercise every severity band
in one report.

**What to expect.** A heterogeneous gap report: **Crypto / data protection**,
**Incident response**, and **Risk management** are `missing` (high / SARIF
`error`); **Access control** and **Logging & monitoring** are `partial` (medium /
SARIF `warning`); **Change management** and **Vendor / supply chain** are clean.
Run with no `--framework` to see how each gap lights up PCI **and** SOC 2 at
once (e.g. missing crypto = PCI Req 3-4 *and* SOC 2 CC6).

**Run it.**

```bash
# both frameworks at once — see the blast radius of each gap
python -m atlas assess demos/12-retail-pci-saq/posture.json --format markdown

# PCI-only CI gate (will exit 1 — there are open gaps)
python -m atlas assess demos/12-retail-pci-saq/posture.json --framework pci-dss --fail-on-gap
```

**How to act.** Sequence the three `missing` themes first — encryption of stored
cardholder data (Req 3-4) and an incident-response plan (Req 12) are SAQ
blockers. The two `partial` themes are evidence work. Change management and
vendor management already pass in both frameworks; protect them with the gate.
