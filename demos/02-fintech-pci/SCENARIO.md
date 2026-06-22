# Demo 02 — Payment facilitator on the road to PCI DSS 4.0

**Where the data came from.** A payment facilitator preparing for its annual
PCI DSS 4.0 assessment. A QSA-led gap workshop scored the themes. Their estate
is strong on access control, logging (Req 10), incident response, and risk —
but the migration to PCI 4.0's stronger cryptography (Req 3–4) is mid-flight,
secure-SDLC change control (Req 6) has coverage gaps in two services, and
third-party/TPSP oversight (Req 12) is incomplete.

**What to expect.** No `missing` themes — but three `partial` (medium) findings
against **Crypto / data protection (Req 3-4)**, **Change management (Req 6)**,
and **Vendor / supply chain (Req 12)**. Coverage ~79%.

**Run it.**

```bash
python -m atlas assess demos/02-fintech-pci/posture.json --framework pci-dss --format markdown
```

**How to act.** Crypto is the schedule risk: finish the keyed-hash/strong-crypto
migration ahead of the assessment date. Close the Req 6 SDLC gaps in the two
lagging services, and complete the TPSP responsibility matrix for Req 12.8.
Export to Markdown to paste straight into the readiness deck for leadership.
