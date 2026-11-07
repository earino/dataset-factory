events: 514 merged; excluded false alarms 15, umbrella 1, licence triage 7; analysed 491

### Detecting layer x defect tier (all analysed events)

| detected_by | validity | legal | claims | pipeline | process | other | total |
|---|---|---|---|---|---|---|---|
| agent-self-check | 34 | 4 | 22 | 69 | 93 | 44 | 266 |
| codex-audit | 32 | 3 | 17 | 7 | 11 | 4 | 74 |
| unknown | 12 | 1 | 2 | 8 | 14 | 2 | 39 |
| worker-guard | 3 | 0 | 1 | 12 | 15 | 1 | 32 |
| ci-mechanical-check | 1 | 0 | 3 | 3 | 13 | 5 | 25 |
| external-provider | 0 | 1 | 0 | 13 | 0 | 0 | 14 |
| human-operator | 0 | 1 | 3 | 1 | 4 | 2 | 11 |
| qualification-gate | 3 | 0 | 1 | 1 | 0 | 5 | 10 |
| hub-loading-check | 0 | 0 | 0 | 9 | 0 | 0 | 9 |
| consumer-verification-job | 0 | 0 | 2 | 2 | 2 | 1 | 7 |
| post-publication-review | 0 | 1 | 2 | 1 | 0 | 0 | 4 |

### Validity defects (n=85): detecting layer x furthest stage reached before detection

| detected_by | never-built | built-unqualified | qualified | private-staged | public | total |
|---|---|---|---|---|---|---|
| agent-self-check | 29 | 2 | 1 | 2 | 0 | 34 |
| codex-audit | 2 | 3 | 2 | 14 | 11 | 32 |
| unknown | 1 | 2 | 2 | 5 | 2 | 12 |
| qualification-gate | 1 | 1 | 0 | 0 | 1 | 3 |
| worker-guard | 0 | 3 | 0 | 0 | 0 | 3 |
| ci-mechanical-check | 0 | 0 | 0 | 0 | 1 | 1 |

### Licence + public-claim defects (n=64): detecting layer x furthest stage reached

| detected_by | never-built | built-unqualified | qualified | private-staged | public | total |
|---|---|---|---|---|---|---|
| agent-self-check | 9 | 0 | 7 | 4 | 6 | 26 |
| codex-audit | 4 | 1 | 2 | 12 | 1 | 20 |
| human-operator | 0 | 0 | 0 | 1 | 3 | 4 |
| ci-mechanical-check | 0 | 0 | 1 | 2 | 0 | 3 |
| unknown | 1 | 0 | 0 | 2 | 0 | 3 |
| post-publication-review | 0 | 0 | 0 | 0 | 3 | 3 |
| consumer-verification-job | 0 | 0 | 0 | 2 | 0 | 2 |
| external-provider | 0 | 0 | 0 | 1 | 0 | 1 |
| worker-guard | 0 | 1 | 0 | 0 | 0 | 1 |
| qualification-gate | 0 | 1 | 0 | 0 | 0 | 1 |

Escapes past qualification (private-staged or public): 175 of 491; public: 58
validity escapes to public: ['abs-visitor-arrivals-direction', 'austin-911-response', 'chicago-doah-adjudication', 'chicago-food-inspections', 'eutl-installation-net-short', 'msha-enforcement-citations', 'my-pricecatcher-weekly-increase', 'noaa-tide-flooding', 'pins-planning-appeal-outcome', 'who-flunet-activity-exceedance']

false alarms by detector: {'agent-self-check': 14, 'qualification-gate': 1}
human_involved share: 115 / 491
