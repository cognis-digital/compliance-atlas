# Demo 06 — Greenfield: assess-by-default when you have nothing yet

**Where the data came from.** A pre-seed company with no security program at all.
This demo exists to show the tool's **fail-safe default**: an empty `controls`
object. Because silence is a gap, every theme is assessed as `missing` rather
than silently passing — you cannot accidentally score 100% by leaving the file
blank.

**What to expect.** All seven themes report `missing` (high). Coverage 0%. This
is the maximal-gap baseline you remediate down from.

**Run it.**

```bash
python -m atlas assess demos/06-greenfield-baseline/posture.json --framework nist-csf
```

**How to act.** Use this as your starting template: copy it, then flip themes to
`partial`/`implemented` as you build. NIST CSF 2.0's Govern + Identify functions
(Risk management) are the usual first move, followed by Protect (Access control,
Crypto). Re-run after each sprint to track coverage from 0% upward.
