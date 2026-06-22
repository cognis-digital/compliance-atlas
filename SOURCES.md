# Sources (primary & authoritative where possible)

- AICPA Trust Services Criteria; AICPA TSC↔ISO 27001 mapping spreadsheet.
- ISO/IEC 27001:2022 (Annex A, 93 controls / 4 themes).
- NIST CSF 2.0 (Feb 2024) — csrc.nist.gov; CSF↔800-53r5 mapping workbook.
- NIST SP 800-53 Rev. 5 (Sept 2020); NIST SP 800-171 Rev. 2 & Rev. 3 (May 2024).
- DoD CIO — CMMC 2.0 model & "CMMC Alignment to NIST Standards".
- EU AI Act — digital-strategy.ec.europa.eu; artificialintelligenceact.eu (timeline & GPAI guidance).
- GDPR (Reg. 2016/679); CCPA/CPRA (Cal. Civ. Code); HIPAA (45 CFR 160/164); PCI DSS v4.0 (PCI SSC).

Compiled via web research on 2026-06-08; verify against the live source before relying on it.

## Data-feed ingestion (`atlas feeds`)

Real, keyless public feeds consumed by the edge/air-gap ingestion layer
(`datafeeds.py` + `data_feeds_2026.json`). See the README "Live data feeds" section.

- **NIST SP 800-53 rev5 catalog (OSCAL)** — `usnistgov/oscal-content` ·
  https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json
- **ATT&CK ↔ NIST 800-53 mappings** — Center for Threat-Informed Defense, Mappings Explorer ·
  https://github.com/center-for-threat-informed-defense/mappings-explorer

<!-- cognis-2026-live-sources -->

## Live 2026 sources (auto-expanded)

_Always-current feeds, live web-search queries, and keyless APIs for real-time monitoring. Ingest at runtime with `livesearch.py`._

### Ai
- **feed** · https://huggingface.co/blog/feed.xml
- **feed** · https://openai.com/news/rss.xml
- **feed** · https://www.anthropic.com/rss.xml
- **feed** · https://export.arxiv.org/rss/cs.AI
- **feed** · https://export.arxiv.org/rss/cs.LG
- **live search** · `frontier AI model release 2026`
- **live search** · `AI agent benchmark state of the art`
- **live search** · `open-weight LLM release`
- **live search** · `AI policy regulation 2026`
- **api** · http://export.arxiv.org/api/query (arXiv, free)
- **api** · https://api.github.com/search/repositories?q=stars (trending repos, free)
- **api** · https://hn.algolia.com/api (Hacker News, free)

### Cyber
- **feed** · https://www.cisa.gov/cybersecurity-advisories/all.xml
- **feed** · https://www.bleepingcomputer.com/feed/
- **feed** · https://thehackernews.com/feeds/posts/default
- **feed** · https://krebsonsecurity.com/feed/
- **feed** · https://www.darkreading.com/rss.xml
- **live search** · `actively exploited vulnerability 2026`
- **live search** · `ransomware campaign threat actor`
- **live search** · `zero-day disclosure CVE 2026`
- **api** · https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json (KEV, free)
- **api** · https://services.nvd.nist.gov/rest/json/cves/2.0 (NVD CVE, free)
- **api** · https://otx.alienvault.com/api (threat pulses, free key)

### Conflict
- **feed** · https://www.understandingwar.org/feeds/all.xml
- **feed** · https://www.bellingcat.com/feed/
- **feed** · https://www.acleddata.com/feed/
- **feed** · https://www.aljazeera.com/xml/rss/all.xml
- **feed** · https://feeds.bbci.co.uk/news/world/rss.xml
- **live search** · `frontline situational awareness OSINT`
- **live search** · `ceasefire escalation conflict monitor`
- **live search** · `ISW Russia Ukraine assessment`
- **live search** · `Middle East conflict live updates`
- **api** · https://acleddata.com/data-export-tool/ (conflict events, free API)
- **api** · https://ucdp.uu.se/apidocs/ (UCDP georeferenced events, free)
- **api** · https://firms.modaps.eosdis.nasa.gov/api/ (NASA FIRMS fire/strike proxy, free)
- **api** · https://opensky-network.org/apidoc/ (live aircraft, free)

