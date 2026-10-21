# cer-pipeline-incident-significant

Record dated evidence, decisions, and failed approaches here.

## 2026-10-21 discovery session (tick region: Canada)

Publisher: Canada Energy Regulator (CER). open.canada.ca packages 7dffedc4
("Pipeline Incident Data") and fd17f08f ("Incidents At CER-Regulated Pipelines
And Facilities"), both license_id=ca-ogl-lgo.

### Access probes

- `python3 .factory/ca_probe_packages.py` -> CKAN package_show for both packages:
  anonymous HTTP 200; resources: pipeline-incidents-data.csv,
  pipeline-incidents-comprehensive-data.csv (en/fr), a data-dictionary CSV, and an
  HTML link to github.com/CER-REC/incidents-pipeliniers_pipeline-incidents.
- `python3 .factory/ca_probe_cer.py` -> downloads: data 580,376 B +
  comprehensive 2,451,628 B + dictionary 15,407 B = 3,047,411 B in 6.48 s,
  anonymous, Range honored (HTTP 206), last-modified 2026-10-01 (both data files).
  NOTE: files decode as cp1252, not utf-8 (UnicodeDecodeError at byte 7463 with
  utf-8-sig) - a construction detail to carry.

### Measurements (command = probe_download_measure.py)

- data.csv: 2,034 rows x 16 columns, years 2008-2026 (52-173 rows/year).
- Significant=yes: 361/2,034 = 17.75%; per year 6-51, both classes in all 19 years.
- Status: Closed 2,002, Submitted 15, Initially Submitted 17 (recent rows still
  open - a recency caveat for holdout windows).
- Incident Types: Release of Substance 810, Operation Beyond Design Limits 499,
  Fire 446, Serious Injury (OPR) 125, Adverse Environmental Effects 80,
  Fatality 7 (+combination rows). Substance: Not Applicable 1,188, Natural Gas -
  Sweet 559, ... Release Type: Not Applicable 1,188, Gas 673, Liquid 97.
- Volume released (m3): n=594 numeric, median 19.3, >=1: 479, >=10: 330, >=100: 233.
- Dictionary: "Significant :: Whether the incident is a significant incident,
  which is an acute event that results in: -death; -a serious injury (as defined
  in the OPR); -a fire or explosion that causes a pipeline or facility to be
  inoperative; -a LVP hydrocarbon release in excess of..." -> the label is a
  MECHANICAL function of consequence fields that cannot ship as features.
- Honest report-time feature AUC vs Significant (in-sample, categorical levels
  >=5 rows; command = probe_honest_auc.py): Company 0.7295, Province 0.7015,
  Substance 0.6585, Year 0.6526, Release Type 0.5294; the excluded label-adjacent
  Incident Types alone scores 0.9143.

### Prior-art check

- `python3 .factory/ca_probe_statcan_hc.py` -> GitHub API, anonymous:
  CER-REC/incidents-pipeliniers_pipeline-incidents is "A visualization of pipeline
  incident data from the National Energy Board" - a JS/webapp (webpack, app/),
  not an ML dataset or benchmark. The publisher ships raw CSVs + a viewer.
- Web search: US analog (PHMSA incidents) is public raw data with Kaggle
  analyses; no public ML-ready pipeline-incident SIGNIFICANCE benchmark with
  splits/scored contract found. Not a mirror - a marginal-task park.

### Decision

PARK. The label is mechanically derived from fields that cannot ship
(Incident Types contains 'Serious Injury'/'Fatality'; volume and release type are
outcomes), so the honest feature set is company/province/substance/date, and the
measured AUCs show the surviving task is operator risk profiling (Company 0.73).
2,034 rows / ~180 positives total, and the same 'predict the regulator's
classification' family as hc-recalls-classification in the same jurisdiction.
Access and licence are excellent; the record keeps the measured panel so a future
formulation costs one re-read.
