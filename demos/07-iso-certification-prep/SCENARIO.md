# Demo 07 — Clean run: ISO 27001 stage-2 readiness gate in CI

**Where the data came from.** A logistics company whose ISMS is complete and who
wants a machine gate that *proves* there are no open theme-level gaps before the
stage-2 certification audit. Every theme is `implemented`.

**What to expect.** Zero gaps. With `--fail-on-gap` the command exits `0`, so it
passes as a CI gate. (The matrix-level themes are all green — this does **not**
replace the auditor's control-by-control test; it gates the high-level posture.)

**Run it.**

```bash
python -m atlas assess demos/07-iso-certification-prep/posture.json \
  --framework iso27001 --fail-on-gap
echo "exit: $?"   # -> 0

# CSV snapshot for the audit evidence binder
python -m atlas assess demos/07-iso-certification-prep/posture.json --format csv
```

**How to act.** Wire the `--fail-on-gap` invocation into a CI job (see
`.github/workflows`) so any regression in the posture file fails the build. Keep
the CSV export as a dated evidence artifact in your ISMS document set.
