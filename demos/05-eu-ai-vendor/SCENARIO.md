# Demo 05 — High-risk AI provider hardening its ISO 27001 ISMS

**Where the data came from.** An AI vendor whose product falls in the EU AI
Act's high-risk tier. They already hold ISO 27001 and are layering AI-specific
governance (risk management, third-party model/data provenance) on top. This is a
**mature** org — most themes are `implemented` — so the report is about the *last
mile*, not foundations.

**What to expect.** Only two `partial` (medium) findings: **Risk management
(Cl.6 / ID.RA)** and **Vendor / supply chain (A.5 / GV.SC)** — exactly the two
areas the AI Act's risk-management and data-governance duties stress. Coverage
~86%. With `--fail-on-gap` this returns exit code 1, so CI catches regressions.

**Run it.**

```bash
python -m atlas assess demos/05-eu-ai-vendor/posture.json --framework iso27001 --fail-on-gap
echo "exit: $?"   # -> 1 while the two partials remain
```

**How to act.** Deepen the risk-management process to cover model/AI risks
(continual-improvement loop under ISO Clause 6/10) and tighten supplier controls
for training-data and model dependencies. These map cleanly to the AI Act's
risk-management-system and data-governance articles — close them once, evidence
both. SARIF export (`--format sarif`) drops these into a code-scanning dashboard.
