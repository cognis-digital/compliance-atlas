# Roadmap

`compliance-atlas` stays deliberately small: a pure-standard-library tool that
turns a hand-transcribed crosswalk matrix into an actionable, CI-gateable gap
report, optionally enriched with real public feeds and runnable fully offline.
This roadmap describes where it goes next without compromising that character.

Guiding constraints (these do not change):

- **No invented requirements.** Every framework reference printed is transcribed
  verbatim from `crosswalks/master-matrix.md`; a test enforces it.
- **Standard library only** at runtime. No service, no database, no keys.
- **Offline-first.** Feed enrichment must keep working on an air-gapped host.
- **Additive.** New capability never removes or silently changes an existing
  command, flag, or exporter.

## Near-term (next few releases)

- **Posture drift in CI (done in 0.2).** `atlas diff old.json new.json` reports
  per-theme improvement/regression and the coverage delta, with
  `--fail-on-regression` as a gate. Next: an optional Markdown drift comment
  suitable for posting on a pull request.
- **Remediation planning (done in 0.2).** `atlas plan` ranks open gaps by
  priority and coverage upside. Next: a `--top N` flag and effort-weighting so a
  team can plan a sprint's worth of controls.
- **Template scaffolding (done in 0.2).** `atlas template` emits a valid posture
  skeleton. Next: an interactive `--from-matrix` mode that pre-fills `n/a` for
  themes outside a chosen framework's scope.
- **HTML report (done in 0.2).** Self-contained `--format html`. Next: an
  optional single-file report bundle (report + drift + plan) for evidence
  binders.
- **Coverage gate (done in 0.2).** `--min-coverage` fails CI below a threshold.
  Next: per-framework thresholds (e.g. require 100% for the framework you are
  certifying against, 60% for the rest).

## Mid-term

- **More themes, same discipline.** Grow the matrix beyond the current seven
  control themes (e.g. availability/BCDR, privacy/data-subject rights, secure
  SDLC) — each still transcribed from a primary source and crosswalked across all
  frameworks, with the doc-parity test extended to cover them.
- **Weighted coverage.** Let a posture assign relative weight to themes so the
  coverage score reflects an organization's real risk profile, not a flat mean.
- **Evidence hooks.** Allow a posture entry to carry an evidence pointer (ticket,
  runbook, doc URL) that flows into the `json`/`csv`/`html` exports and SARIF
  properties — turning a gap report into an audit-ready index.
- **Feed breadth.** Add more authoritative, keyless crosswalk feeds (still scoped
  to this repo's compliance domain) so enrichment can annotate frameworks beyond
  800-53.

## Long-term

- **First-class agent surface.** A stable JSON/MCP contract over `assess` /
  `diff` / `plan` so agents can drive readiness checks and propose remediations,
  reusing the existing `integrations/` layer.
- **Historical trendlines.** Given a series of posture snapshots, chart coverage
  and per-theme status over time — the drift view generalized to a timeline —
  while remaining a single offline binary.
- **Framework version awareness.** Track when a framework revision changes a
  control reference and surface the delta, so the matrix's provenance stays
  auditable as standards evolve.

## Non-goals

- Becoming a GRC platform, ticketing system, or system of record.
- Making authoritative compliance determinations — this is a planning aid, not an
  audit, and explicitly not legal advice.
- Adding runtime third-party dependencies or a required network service.

Contributions are welcome — see `CONTRIBUTING.md`. Ideas and direction are
discussed in the repository's Discussions.
