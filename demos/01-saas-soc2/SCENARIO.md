# Demo 01 — Series-B SaaS heading into its first SOC 2 Type II

**Where the data came from.** A 40-person B2B SaaS vendor whose enterprise
deals now stall in procurement without a SOC 2 report. An internal readiness
review (engineering lead + a fractional vCISO) scored each control theme. Their
honest self-assessment: identity, encryption, and CI/CD change control are
mature; logging and incident response are half-built; there is **no** formal
risk register or vendor-management program yet.

**What to expect.** Against SOC 2 the report flags **Risk management (CC3)** and
**Vendor / supply chain (CC9)** as `missing` (high), and **Logging &
monitoring (CC7)** + **Incident response (CC7)** as `partial` (medium). Coverage
lands at 57%.

**Run it.**

```bash
python -m atlas assess demos/01-saas-soc2/posture.json --framework soc2
```

**How to act.** CC3 and CC9 are the two net-new programs to stand up before the
observation window opens — a documented risk assessment and a vendor inventory
with security reviews. The two `partial` items are about *evidence*: turn on
centralized log retention and write/test the IR runbook so the auditor can
sample them. Gate this in CI with `--fail-on-gap` once you expect zero gaps.
