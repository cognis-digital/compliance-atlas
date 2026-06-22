# Demo 04 — Digital-health startup mapping SOC 2 and NIST CSF together

**Where the data came from.** A digital-therapeutics startup that handles health
data through a HIPAA-covered partner. They want one control program that answers
both their SOC 2 auditor and a hospital customer's NIST CSF 2.0 questionnaire.
This posture came from a combined readiness review.

**What to expect.** This demo shows the *cross-walk* payoff: one posture,
reported against **two** frameworks at once (default = all, here narrowed via
`--format json` for the GRC pipeline). The standout gap is **Incident
response**, `missing` — surfaced as both SOC 2 `CC7` and CSF `RS`. So a single
remediation (stand up an IR program) closes a high finding in two frameworks.

**Run it.**

```bash
# both frameworks, machine-readable for the GRC pipeline
python -m atlas assess demos/04-health-startup/posture.json --format json

# or just the NIST CSF view for the hospital questionnaire
python -m atlas assess demos/04-health-startup/posture.json --framework nist-csf
```

**How to act.** Build the IR runbook + tabletop once and claim it against CC7 and
RS. Then mature the three `partial` themes (logging, change management, risk).
Pipe the JSON into your evidence tracker to auto-open tickets per finding.
