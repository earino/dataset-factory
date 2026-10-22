# ea-flood-alert-escalation — probe notes

Discovery session 2026-10-22 (UK-regional tick). All probes ran as scratch scripts
(`.factory/probe_ea_flood*.py`, deleted after the session); scratch data
(`Historic_Flood_Warnings.zip`, 3.5 MB; `fwa_register.json`) was fetched to
`$TMPDIR` and removed at session end.

## Licence triage (done first, minutes)

- `data.gov.uk/dataset/historic-flood-warnings2` page, "Licence information"
  section: **Open Government Licence** with `rel=license` link to
  `https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/`.
  CKAN extras: `licence ["Open Government Licence"]`,
  `access_constraints "There are no public access constraints to this data. Use of
  this data is subject to the licence identified."`
- Same OGL extras on `flood-warning-areas3` and `flood-alert-areas2` (both
  Environment Agency).
- EA Hydrology API `meta.license` = nationalarchives OGL v3 URL, `licenseName`
  "OGL 3".
- Class **A**. Access: anonymous everywhere, no registration (the API landing
  record itself states "no requirement for registration").

## Commands and results

1. `probe_ea_flood1.py` — flood-monitoring API + CKAN search.
   - `environment.data.gov.uk/flood-monitoring/id/floods` → HTTP 200, 7 live items.
   - CKAN `package_search?q=flood warnings historic` → found
     `historic-flood-warnings2` (Environment Agency, updated 2026-10-09).
2. `probe_ea_flood2.py` — `package_show` for the three records. Historic Flood
   Warnings: "issued since the flood warning system went live on January 26th
   2006 to the end of June 2026", quarterly updates, 1 ZIP resource.
3. `probe_ea_flood3.py` — licence extras + page text + ZIP size.
   Ranged GET: **3,628,573 bytes**. `HEAD` is refused (405) on the file API.
4. `probe_ea_flood4.py` — download ZIP. Members: `202607 Historic Flood Warnings
   Documentation.odt` (275,716 B) + `202607 Historic Flood Warnings – EA Only.ods`
   (3,463,034 B uncompressed).
5. `probe_ea_flood5.py` — documentation text + ODS schema. Columns:
   `DATE, AREA, CODE, WARNING / ALERT AREA NAME, TYPE`. Documented meanings from
   the ODT: DATE = "date and time that the warning was issued from the flood
   warning system"; AREA = "Environment Agency operational Area that issued the
   warning message"; CODE = "The Target Area code"; TYPE = "The severity of the
   flood warning message sent". Update frequency: "quarterly during April, July,
   October, and January". Notes three warning codes plus removal notification,
   "Update" messages for ongoing events, pre-2010 "Flood Watch" naming.
6. `probe_ea_flood6.py` — 85,993 data rows; TYPE mix (raw, case-variant);
   per-year messages 2006-2026 present throughout; 4,553 unique CODEs.
   First-pass 48h-gap episode analysis: mostly single-message episodes ->
   same-code escalation is rare; flagged for redesign.
7. `probe_ea_flood7.py` — case-normalised types; same-code alert→warning
   follow-up within K days: K=3: 24, K=7: 29, K=14: 33 — all pre-2010.
   **Conclusion: alert codes and warning codes are different code spaces**;
   same-code escalation is the wrong join.
8. `probe_ea_flood8.py` — OGC Features collections exist for both registers;
   items endpoint 500s; operational-area-grain proxy: 56.34% of alerts see a
   warning in the same op-area within 2 days (degenerate — op areas are too
   coarse); EA Hydrology API live, OGL 3 meta.
9. `probe_ea_flood9.py` — DATE grain: 0 of 85,982 rows carry a time-of-day.
10. `probe_ea_flood10.py` — WFS GetFeature schemas. **Flood_Warning_Areas
    properties include `parent`** (sample: `fws_tacode 111FWFBRT150`,
    `parent 111WAFWDRS`). Flood_Alert_Areas has no parent (top level).
    Same-code warning→severe: 363/22,586 (1.61%) within 7d, clustered in ~10-15
    national storm events → too thin for splits.
11. `probe_ea_flood11.py` — fetched both registers properties-only via WFS
    (3,426 warning areas, 3,424 with parent, 694 distinct parents, 2 orphans;
    782 alert areas). **Parent-linked escalation base rates**: [D,D+7]:
    11,173/53,048 = 21.06%; splits all both-classes. Register code coverage:
    89.0% of alert messages, 84.5% of warning messages.
12. `probe_ea_flood12.py` — offset histogram of positives: 46.9% same-day
    (day-grain ambiguity), so the label window starts at D+1. Persistence probe:
    prev-7d-escalation rule 2x2 AUC 0.559 (P(esc|prev) 45.11%, P(esc|no prev)
    18.91%). 577 distinct positive year-weeks ([D,D+7] definition); 566/694 areas
    ever escalate.
13. `probe_ea_flood13.py` — **label window [D+1,D+7]**: 7,606/53,048 = 14.34%;
    train 2006-2019: 28,864/3,638 (12.60%); eval 2020-2022: 9,623/1,560 (16.21%);
    holdout 2023-2026H1: 14,561/2,408 (16.54%); positives every year;
    458 distinct positive year-weeks.
14. `probe_ea_flood14.py` — CKAN licence extras for `flood-alert-areas2` (OGL);
    measured construction fetch cost: registers 9 WFS requests, 1,320,726
    bytes, 3.8 s wall clock on the coordinator.

## Novelty probes (web search, 2026-10-22)

- "flood warning issuance prediction machine learning dataset Environment Agency
  England" — returns only the source datasets themselves (flood-monitoring API,
  Historic/Live Flood Warnings, Flood Warning Areas) and a Defra blog on river
  level telemetry. No ML-ready escalation task.
- ""machine learning" predict flood alert escalation warning issued benchmark
  dataset" — prior art is sensor-side: HaorFloodAlert (Bangladesh flash floods,
  Sentinel-1 + gauges, arXiv 2605.20167), Iowa river-stage DNN benchmark
  (arXiv 1902.02308), GFF coastal inundation segmentation benchmark
  (arXiv 2409.18591), Wupper river-stage QML (arXiv 2407.01001), and flood-related
  112-call prediction (NHESS 26:3943, Slovenia). None predicts an agency's
  warning *issuance/escalation* from its own warning history.
- The publisher's own adjacent product is a live 3-day flood-risk forecast in
  the flood-monitoring API; it is not a historical, ML-ready escalation dataset.

## Verdict: go

Class A (OGL v3.0), anonymous access, documented quarterly release schedule,
event-grain, parent-published join, measured base rate 14.34% with both classes
in all three windows, persistence single-rule AUC 0.559 leaves headroom, and the
whole panel is small (3.6 MB ZIP + 1.3 MB registers). Recorded go 2026-10-22.
