# Demo 08 — MSP shared baseline across all six frameworks at once

**Where the data came from.** A managed-services provider that maintains one
hardened control baseline and maps it to every framework its clients ask about.
They run the assessment with **no `--framework`** flag so each theme is reported
against all six frameworks simultaneously — the "implement once, satisfy many"
view.

**What to expect.** The default (all-framework) report. **Vendor / supply
chain** is `missing` and shows up as six high findings at once — CC9, A.5,
GV.SC, SR, 3.12, Req 12 — vividly demonstrating how one weak theme propagates
across every framework. **Incident response** and **Risk management** are
`partial`. The SARIF export turns these into code-scanning alerts.

**Run it.**

```bash
# full cross-framework table
python -m atlas assess demos/08-msp-multiframework/posture.json

# SARIF 2.1.0 for a security dashboard / code-scanning upload
python -m atlas assess demos/08-msp-multiframework/posture.json --format sarif > atlas.sarif
```

**How to act.** Fixing the single Vendor/supply-chain gap clears six framework
findings in one project — the highest-leverage remediation in the report. Upload
`atlas.sarif` to your code-scanning tool to track gaps next to code findings, and
keep the `--fail-on-gap` gate green once vendor management is built.
