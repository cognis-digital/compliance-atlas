# Usage

A task-oriented tour of the `atlas` CLI. Everything here runs against the real
API on real data (the worked postures under `demos/`), pure standard library, no
network. Set `PYTHONUTF8=1` on Windows for consistent encoding.

## Install

```bash
git clone https://github.com/cognis-digital/compliance-atlas.git
cd compliance-atlas
pip install -e ".[dev]"      # editable install + pytest/ruff for development
# or, zero-install: run modules directly with `python -m atlas ...`
```

The runtime has **no third-party dependencies**; `pip install -e .` only wires
the `atlas` console entry point. See [INSTALL.md](INSTALL.md) for more.

## 1. Scaffold a posture file

Rather than hand-authoring the theme keys (and risking a typo that the loader
will reject), start from a template:

```bash
python -m atlas template --org "Acme, Inc." > posture.json
# every theme pre-filled as "missing"; edit to implemented/partial/n/a
python -m atlas template --org "Acme, Inc." --status implemented > baseline.json
```

A posture file describes your control posture per theme. Omitted themes are
assessed as `missing` (silence is a gap):

```json
{
  "org": "Acme, Inc.",
  "scope": ["soc2"],
  "controls": {
    "Access control": "implemented",
    "Crypto / data protection": "partial",
    "Logging & monitoring": "missing"
  }
}
```

Status values: `implemented` | `partial` | `missing` | `n/a`.

## 2. Assess

```bash
# one framework
python -m atlas assess posture.json --framework soc2

# all six frameworks at once (implement-once-satisfy-many view)
python -m atlas assess posture.json
```

### Output formats

| `--format` | Use it for |
|---|---|
| `table` (default) | a quick human read in the terminal |
| `json` | feeding a GRC pipeline / opening tickets per finding |
| `csv` | an evidence-binder snapshot / spreadsheet |
| `markdown` | pasting into a readiness deck or PR |
| `sarif` | uploading gaps to a code-scanning / SARIF 2.1.0 dashboard |
| `html` | a self-contained, colour-coded report for a dashboard or email |

```bash
python -m atlas assess posture.json --format html   > report.html
python -m atlas assess posture.json --format sarif   > atlas.sarif
python -m atlas assess posture.json --format json    > findings.json
```

The `html` report is a single self-contained `<div>` fragment (inline styles, no
external assets). All dynamic text is HTML-escaped, so an untrusted `org`/`scope`
value in a posture file cannot inject markup.

## 3. Gate CI

Two independent gates, combinable:

```bash
# fail if ANY theme is partial/missing
python -m atlas assess posture.json --fail-on-gap

# fail if overall coverage is below a threshold (0.0-1.0)
python -m atlas assess posture.json --min-coverage 0.8
```

Both still print the report to stdout; only the exit code changes (`1` on a gate
failure, `2` on a bad/unreadable posture file).

## 4. Plan the remediation

Turn a gap report into an ordered punch list. `missing` themes rank above
`partial`; each item shows the exact coverage gain from taking it to
`implemented` and the control it satisfies in **every** framework:

```bash
python -m atlas plan posture.json
python -m atlas plan posture.json --format json     # machine-readable
```

```
# compliance-atlas remediation plan — Acme, Inc.
# coverage 33%  ·  2 open gap(s), most impactful first

 1. [high  ] Logging & monitoring (missing -> implemented, +33% coverage)
      satisfies: soc2:CC7, iso27001:A.8, nist-csf:DE.CM, 800-53:AU, 800-171:3.3, pci-dss:Req 10
 2. [medium] Crypto / data protection (partial -> implemented, +17% coverage)
      satisfies: soc2:CC6, iso27001:A.8, nist-csf:PR.DS, 800-53:SC, 800-171:3.13, pci-dss:Req 3-4
```

## 5. Track drift over time

Compare two posture snapshots to see what improved or regressed between them —
ideal for a scheduled CI job that commits a posture and flags any slippage:

```bash
python -m atlas diff last-quarter.json this-quarter.json
python -m atlas diff old.json new.json --format json
python -m atlas diff old.json new.json --fail-on-regression   # CI drift gate
```

```
# compliance-atlas posture drift — Acme, Inc.
# coverage 33% -> 67% (+33%)  [improved:2 regressed:0 unchanged:5]

   THEME                     FROM         TO           CHANGE
▲  Logging & monitoring      missing      implemented  improved
▲  Crypto / data protection  partial      implemented  improved
=  Access control            implemented  implemented  unchanged
```

Re-scoping a theme to or from `n/a` is treated as neutral (`unchanged`), so
narrowing an assessment's scope never looks like a regression.

## 6. Explore the inputs

```bash
python -m atlas matrix        # the embedded 7-theme × 6-framework matrix
python -m atlas frameworks    # known framework keys
```

## 7. Enrich with real feeds (optional, offline-capable)

See the [main README](../README.md#live-data-feeds--real-nist-800-53--attck-edge--air-gap-deployable)
for the full feed workflow. In short:

```bash
python -m atlas feeds update                      # fetch + cache (online, once)
python -m atlas feeds enrich                       # 800-53 titles + ATT&CK coverage
python -m atlas assess posture.json --framework 800-53 --format json --enrich
COGNIS_FEEDS_CACHE=/srv/feeds python -m atlas feeds enrich --offline   # air-gap
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success (report printed; no gate tripped) |
| `1` | a CI gate tripped (`--fail-on-gap`, `--min-coverage`, `--fail-on-regression`) |
| `2` | usage error or a malformed / unreadable posture file |
