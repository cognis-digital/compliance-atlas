# Demos

Two layers of demos ship with `compliance-atlas`, and both use the **real** API
and **real** data — nothing is mocked or fabricated:

1. **Runnable scenarios** — `demos/*.py`: narrated, audience-specific walkthroughs
   that drive `atlas.assess` / `atlas.summarize` / the exporters / `atlas_feeds`
   end to end and exit 0. Start here.
2. **Worked posture pairs** — `demos/NN-name/`: a realistic `posture.json` +
   `SCENARIO.md` (where the data came from, what to expect, the exact command,
   how to act). The runnable scenarios load these same files.

## Run them

```bash
# everything, in order (offline — feed enrichment reads the committed cache)
PYTHONUTF8=1 python demos/run_all.py

# or one at a time
PYTHONUTF8=1 python demos/01_startup_first_soc2.py
```

> Demos run with `PYTHONUTF8=1` so the narration renders identically on every
> platform. They require no network and no dependencies beyond the standard
> library.

## Runnable scenarios by audience

| Demo | Audience | What it shows | Real API exercised |
|---|---|---|---|
| `01_startup_first_soc2.py` | Founders / startups chasing first SOC 2 | A readiness gut-check becomes a prioritized punch list: *stand up* (missing) vs *prove* (partial), plus the coverage number to quote the board | `load_posture`, `assess(framework="soc2")`, `summarize` |
| `02_grc_implement_once.py` | GRC / compliance leads | One shared baseline assessed across all six frameworks at once; each open gap's cross-framework blast radius made explicit ("implement once, satisfy many") | `assess` (all frameworks), `MATRIX`, `summarize` |
| `03_auditor_ci_gate.py` | Auditors / CI engineers | Clean-run proof + the exact `--fail-on-gap` exit codes; emits real SARIF 2.1.0 for a code-scanning dashboard | `assess`, `to_sarif`, `summarize` |
| `04_security_engineer_threat_coverage.py` | Security engineers | 800-53 gaps reframed as **ATT&CK technique exposure** using real NIST OSCAL titles + the CTID crosswalk — fully offline | `atlas_feeds.enrich_matrix` / `enrich_findings` (`offline=True`) |
| `05_greenfield_assess_by_default.py` | Pre-seed / greenfield founders | An empty posture honestly returns a 0% roadmap (silence == gap); the same themes anchor a portable, framework-agnostic blueprint | `assess` (empty posture), `MATRIX`, `to_markdown` |

## Worked posture pairs (`demos/NN-name/`)

| Dir | Situation |
|---|---|
| `01-saas-soc2` | Series-B SaaS heading into its first SOC 2 Type II |
| `02-fintech-pci` | Payment facilitator on the road to PCI DSS 4.0 |
| `03-defense-cmmc-800171` | DIB subcontractor scoping CMMC L2 / NIST 800-171 (CUI) |
| `04-health-startup` | Digital-health startup mapping SOC 2 **and** NIST CSF together |
| `05-eu-ai-vendor` | High-risk AI provider hardening its ISO 27001 ISMS |
| `06-greenfield-baseline` | Pre-seed: assess-by-default when you have nothing yet |
| `07-iso-certification-prep` | Clean run — `--fail-on-gap` as an ISO stage-2 CI gate |
| `08-msp-multiframework` | MSP shared baseline reported across all six frameworks at once |
| `09-feed-enrichment` | Air-gapped enclave: enrich 800-53 themes with real OSCAL titles + ATT&CK coverage, fully offline |

Tests for both layers live in `tests/` — `python -m pytest -q`.
