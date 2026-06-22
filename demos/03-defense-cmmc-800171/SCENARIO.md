# Demo 03 — Defense subcontractor scoping CMMC Level 2 (NIST 800-171)

**Where the data came from.** A small aerospace machine shop that handles CUI on
prime contracts and must reach CMMC L2 — which is the 110 controls of NIST
800-171 r2. A pre-assessment by their MSP produced this brutally honest posture:
identity and IR are started, but there is **no** FIPS-validated encryption for
CUI at rest/in transit (3.13), **no** centralized audit logging (3.3), and **no**
supply-chain/flow-down program (3.12).

**What to expect.** Three high `missing` findings — **Crypto / data
protection (3.13)**, **Logging & monitoring (3.3)**, **Vendor / supply
chain (3.12)** — plus four `partial` (medium). Coverage is low (~29%): this org
is not yet assessment-ready and should not self-attest a high SPRS score.

**Run it.**

```bash
python -m atlas assess demos/03-defense-cmmc-800171/posture.json --framework 800-171
```

**How to act.** The three `missing` families are the make-or-break items for a
defensible System Security Plan and POA&M. Prioritize FIPS-validated crypto for
CUI (3.13) and a SIEM/log-retention capability (3.3) first — they gate the most
other practices — then build flow-down clauses for subs (3.12). Re-run after each
remediation to watch coverage climb.
