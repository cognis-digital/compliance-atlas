# Demo 11 — Fully clean posture: the green-CI / no-gap case

**Where the data came from.** A company that has *already* completed both a SOC 2
Type II and an ISO 27001 surveillance audit and now runs compliance-atlas purely
as a **regression gate**: every theme is `implemented`. This is the case that
proves the tool reports honestly when there is nothing to flag.

**What to expect.** 100% coverage. The table/markdown reports list every theme as
`implemented`; the **SARIF export contains zero results** (only gaps become
results); and `--fail-on-gap` returns **exit 0**. This is the posture demo 03's
clean branch and several tests pin against — it is the canonical "merge allowed"
state.

**Run it.**

```bash
python -m atlas assess demos/11-clean-soc2-iso/posture.json --framework soc2 --fail-on-gap
echo "exit: $?"   # 0

# SARIF has no results on a clean posture
python -m atlas assess demos/11-clean-soc2-iso/posture.json --format sarif
```

**How to act.** Nothing to remediate — keep the gate green. If a control later
regresses to `partial`/`missing`, `--fail-on-gap` flips to exit 1 and the SARIF
feed lights up the offending theme in code scanning, so the regression can't be
merged silently.
