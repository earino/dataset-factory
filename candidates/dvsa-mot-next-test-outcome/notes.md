# dvsa-mot-next-test-outcome

**Verdict: GO (2026-10-19).** Status `investigating`; novelty search recorded by
`scripts/check-novelty.py` (differentiated). Construction belongs to an
advancement session.

## The task

For a vehicle with a completed MOT test, predict whether its NEXT test ends in
an initial failure (F or PRS), using only what is known up to and including the
previous test. Label = the documented `test_result` of the next test; features
= static vehicle attributes + full prior-test history (including defect
categories from the companion failure-item files). Next-test fields never ship.

## Probes (2026-10-19, anonymous, from the coordinator; ranged reads only, nothing bulk downloaded)

### Licence and provenance

| Command | Result |
|---|---|
| `GET https://ckan.publishing.service.gov.uk/api/3/action/package_show?id=e3939ef8-30c7-4ca8-9c7c-ad9475cc9b2f` | HTTP 200; license_title `UK Open Government Licence (OGL)`, license_url https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ ; org department-for-transport; resources list per-year result + failure-item files 2005-2022 (2005-2016 `test_result_YYYY.txt.gz`, 2017-2022 `dft_test_result_YYYY.zip`), user guide ODT, lookup.zip |
| `GET .../package_show?id=c63fca52-ae4c-4b75-bab5-8b4735e1a4c9` | HTTP 200; same OGL licence; org driver-and-vehicle-standards-agency; 2023+ files at `https://edh-dvsa-data-gov-uk-files-prod.s3.eu-west-1.amazonaws.com/...`; notes: "As of January 2025, datasets from 2023 will be published by DVSA" |

### 2024 zip shape (ranged zip reads: EOCD + central directory + partial member decompression, ~14 requests, ~4.5 MB)

| Measurement | Result |
|---|---|
| `MOT testing data results (2024).zip` | 1,531,265,132 bytes compressed; Last-Modified Tue 13 May 2025; Range supported; 12 monthly members `test_result_202401..202412.csv`, 461-746 MB each, **7,667,648,876 bytes uncompressed total** |
| `GET https://edh-dvsa-data-gov-uk-files-prod.s3.eu-west-1.amazonaws.com/mot-testing-data-user-guide-v5.1.odt` | HTTP 200, 73,606 bytes; documents the test regime, result codes and RfR types |

### Row schema and base rate (first 4 MB of `test_result_202408.csv`, 34,924 rows)

Header, verbatim:
`test_id,vehicle_id,test_date,test_class_id,test_type,test_result,test_mileage,postcode_area,make,model,colour,fuel_type,cylinder_capacity,first_use_date,completed_date`

Sample row: `982603987,596187188,2024-08-19,4,NT,P,65494.0,HG,BENTLEY,CONTINENTAL,SILVER,PE,5998,2006-03-01,2024-08-19T14:10:35.000Z`

- test_result: **P 27,026 (77.3%) / F 6,190 (17.7%) / PRS 1,516 (4.3%) / ABR 157 / ABA 35** -> initial-fail (F+PRS) 22.1%, final-fail 17.7%
- test_type: NT 29,058 / RT 5,866; test_class_id: 4 -> 32,073; 7 -> 1,911; 2 -> 734; 1 -> 149; 5 -> 53; 3 -> 4
- distinct vehicle_id: 19,328 across 34,924 rows (several tests per vehicle per month is normal - retests)
- **test_id is NOT unique**: 6,336 test_id values repeat within the prefix (top: test_id 1934795005 x36); the file's first two rows are byte-identical. Dedup + total order required at construction.

### Cross-check (publisher's own summary product)

`https://www.gov.uk/government/statistical-data-sets/mot-testing-data-for-great-britain`
(DVSA/MOT/01 CSV, read 2026-10-19): FY2025-26 classes 3&4 initial fail 27.51% /
final 22.30%; classes 1&2 13.40% / 8.20%; class 7 34.00% / 27.01%. The August-2024
prefix (22.1% initial, all-class mix) is the same magnitude and class ordering;
August is a historically lenient month. No contradiction.

## Novelty (checked BEFORE any source work, per the standing order)

Prior art found by web search (2026-10-19):
- github.com/adin786/mot-data - personal EDA project; SGD pass/fail classifier
  (76% accuracy) on one year (2019), one postcode area ('G'), class 4 only,
  two features (vehicle age, mileage). Exploratory, not an ML-ready task.
- Lisense (lisense.uk/vehicle-insights) - a commercial MOT-failure predictor
  built on DVSA history: shows the task is useful and NOT shipped as a dataset.
- gov.uk DVSA/MOT/01 - the publisher's own aggregate tables (cross-check product).
- No Kaggle/HF/Zenodo/arXiv ML-ready next-test-outcome task with splits was found
  (mechanical search recorded by check-novelty.py in record.json).

What is ours: full-history next-test outcome prediction (prior-test history
features incl. defect categories), frozen temporal splits 2010-2018/2019-2021/
2022-2024, leakage-disciplined shipped columns, scored runner contract.

## Construction (launched 2026-11-05, job dvsa-mot-build-001)

GO executed per the recorded next_action. Full preflight, design decisions,
pre-registered triad and deciding rule live in `record.json`
(`measurements.construction_preflight_2026_11_05`) and in the headers of
`source/build.py` / `source/score.py`. Key deltas from the original sketch, all
pre-registered before any score:

- Splits are by PRIOR-test year (the prediction instant), not next-test year:
  the next test's date is label-side timing and cannot ship, so next-test-year
  windows are unverifiable from the rows. Train priors 2009-2018, eval
  2019-2021, holdout 2022-2023.11; right-censoring cutoff 2023-11-30 (priors
  on/after it are excluded wholesale and counted).
- Class 4 only, both sides of every pair; vehicles hash-sampled
  md5(vehicle_id) mod 1000 == 0 (~0.1%); ABR/ABA excluded and counted;
  defect-item features omitted in v1 (test_id is measured NOT unique, so the
  item join is ambiguous - documented, not silent).
- MEASURED 2026-11-05: data.dft.gov.uk IGNORES Range headers (a ranged probe
  streamed ~1.08 GB before being killed). DfT-era schemas are therefore measured
  by the build itself; the DVSA S3 origin still answers ranged reads. The 2024
  zip is byte-pinned (1,531,265,132 bytes, 12 monthly members, header
  verbatim).
- Dry run on synthetic three-era fixtures (headerless pipe, headered pipe,
  single- and 12-member zips): build exit 0, gate 1.5.0 45/45 PASS, --accept
  ACCEPTED, triad machinery exercised. The declared cross-row probe measured the
  blind-join exposure as designed (synthetic eval 420/570 rows covered, 0
  mismatches); access is isolated_rows. Fixture numbers are not findings.

Status: worker cpx32 (server 174661065, hel1) running the build; expected
reports and the collection/baseline standing order are in `record.json`
`next_action`.

## Repair relaunch dvsa-mot-build-002 (advancement 2026-11-07)

Build-001 died at the 2015 source value 'ABRVE' (see record
`measurements.build_failure_2015_abrve_2026_11_05`). This session executed the
recorded repair: exactly two construction-side changes, before any score has
ever existed.

- build.py: any test_result outside {P, F, PRS} is a NON-COMPLETED test -
  excluded from both sides of every pair (the build_pairs filter is now
  not-in-COMPLETED_RESULTS, not the ABR/ABA tuple), counted per year with a
  distinct-value inventory (population.per_year non_completed_rows /
  non_completed_values in summary.json). The fail-loud assertion now covers
  schema-level unmappability only; looks_like_data recognises headerless-era
  data rows by parseable date so an undocumented value cannot masquerade as a
  header. The parse-time counters the deterministic 2005-2014 cross-check reads
  (rows_seen / class4 / sampled) behave identically to build-001.
- source/job.json + bundle.json: max_artifact_mb 8 -> 200 (extract estimate
  ~57-65 MB, 3x headroom; the 8 MiB launch allowance would have refused the
  whole upload per artifact_allowance_check_2026_11_05).
- Every shipped declaration string that named the ABR/ABA tuple now states the
  general non-completed rule (module docstring, meta split_description, quality
  task target_definition, timing row_selection basis, limitations).
- Red/green dry run (probe/dryrun_abrve_2026_11_07.py, synthetic fixtures from
  the committed generator + the exact measured ABRVE row injected): pre-repair
  build exits 1 on ABRVE as recorded; repaired build exits 0 with ABRVE+ABR
  inventoried in 2015 and excluded from pairs; gate 1.5.0 45/45 PASS,
  --accept ACCEPTED, post-acceptance triad machinery exit 0. Fixture numbers
  are not findings.
- Launched dvsa-mot-build-002: server 174936753 (cpx32, hel1), 06:13:46Z,
  reservation 0.32 EUR (budget month 2026-11). This is the ONE rebuild allowed
  for this defect; a second value/schema refusal is a new finding requiring
  fresh diagnosis. Expected reports and the collection order (collect ->
  2005-2014 cross-check EXACT -> gate PASSED + exact-byte --accept before any
  figure -> triad recording -> destroy with provider read-back -> baseline
  bundle with re-accept before any score) are in `record.json` `next_action`.

## dvsa-mot-build-002 outcome + Deflate64 diagnosis (2026-11-07, same session)

- The relaunch parsed 2005-2016 - the ABRVE repair is PROVEN on real data:
  2015 carries 242 ABRVE rows and 2016 carries 27, all counted as
  non-completed and excluded from pairs; the 2005-2014 receipts reproduce
  build-001 EXACTLY.
- NEW defect at the 2017 DfT zip (first zip-era file; build-001 died before
  it, and the dry-run fixtures were Python-written deflate, so it was not
  observable earlier): every member is compress_type 9 = Deflate64. Stdlib
  zipfile raises NotImplementedError. Measured on the worker: 2017 zip =
  1,082,702,159 B, sha256 8b52a91e..., 12 members ~277 MB uncompressed each.
  Bounded S3 tail probes show the DVSA S3 origin has no 2017-2021 mirrors
  (403) and its 2022/2023 mirrors are ALSO Deflate64 - no URL switch avoids
  it. The pinned 2024 zip is standard deflate (measured 2026-10-19).
- Package evidence: zipfile-deflate64 0.2.0 has no cp313 wheel (dead end on
  python:3.13-slim); inflate64 1.0.4 (LGPL-2.1+) has cp313 manylinux wheels
  and exposes the raw Inflater, but no zipfile integration - the build must
  parse local headers itself (30-byte fixed header + name/extra, then
  compress_size bytes) and inflate explicitly.
- First in-container verification (python:3.13-slim + inflate64 on the
  build-002 worker) OOM-killed (exit 137) with the buffered progress output
  lost, so the memory behaviour of a single-shot inflate on a ~90 MB member
  is UNMEASURED. Next session must instrument RSS (python -u, --memory cap,
  chunked feeding if needed) and only then patch + relaunch as
  dvsa-mot-build-003. Full plan in `record.json` `next_action`; diagnosis in
  `measurements.build_failure_2017_deflate64_2026_11_07`.
