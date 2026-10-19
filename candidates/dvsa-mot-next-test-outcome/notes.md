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

## Next action (construction, advancement session)

See record.json `next_action`. Key construction constraints measured here:
dedup by total order (test_id repeats), vehicle_id never the runner id column,
next-test fields + their failure items are label-source and excluded, class-4
bounding to cut the ~23 GB download / ~115 GB processing estimate.
