# npri-facility-spill-year

## 2026-10-19 discovery session (regional focus: Canada)

Alternative formulation measured while vetting the NPRI source; probe
`python3 .factory/probe_ca_npri_measure.py` (year_stats spill columns), script deleted
after use.

- Spill facility-years (any non-zero "Air Emissions - Spills" / "Water Releases -
  Spills" value): 2021: 110/7,322 (1.50%); 2022: 114/7,521 (1.51%); 2023: 149/7,986
  (1.87%). Row level: 378/56,115, 447/60,202, 491/62,125.
- Same source, licence and file-location details as candidates/npri-facility-reporting-exit.

## Verdict: DROPPED (measured split capacity), recorded 2026-10-19

~1.5-1.9% base rate with heavy clustering: a holdout window carries only a few hundred
positives dominated by repeat facilities - below the independent-positive capacity the
qualification gate needs, and the exact 'thousands of rows, tiny effective sample'
failure mode. Novelty would also be weaker than the exit task (adjacent to published US
facility-incident/compliance prediction literature). The exit formulation
(npri-facility-reporting-exit, 10.8-12.3% base rate) is the NPRI verdict for this source.
