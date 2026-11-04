# notes — unhcr-corridor-entry-surge (opened 2026-11-04)

Verdict: READY (one-shot per-corridor redesign of the dropped panel task; primary
design = first-crossing x 2-year cumulative doubling, both shapes the operator's
recorded reopen condition named). This record is the FORMULATION + measured
capacity evidence for the reopen condition recorded in
candidates/unhcr-refugee-data-finder/record.json (2026-11-02 operator decision):
"a redesigned task that keeps corridor momentum WITHOUT adjacent corridor-years
both shipping (e.g. a one-shot per-corridor design, or an aggregate-outcome
label), constructed and audited fresh from the source." No construction, no
labels shipped, no model: counts and base rates from the pinned source only.

The dropped v2026.10 panel package is NEVER published (its own record governs);
any construction from this record is a fresh artifact with a fresh attempt ID.

## Source and vintage (unchanged from the parent record, re-pinned today)

Same single source as the parent: the UNHCR organisation account's HDX global
package `unhcr-population-data-for-world`, resource
`asylum_applications_residing_world.csv`. Licence re-verified on the live
package today (CKAN package_show, 2026-11-04): `license_id "cc-by-igo"`,
`dataset_source "UNHCR"`, `last_modified 2026-08-20T15:33:49Z`, 5 resources.

```
curl -sSL -o asylum_applications_residing_world.csv \
  "https://data.humdata.org/dataset/74cdbe77-0a0b-441b-9535-bacc263be2a8/resource/295cd9e4-8464-43ee-ad17-47196991a1f7/download/asylum_applications_residing_world.csv"
  -> HTTP 200, 8,669,567 bytes, 3.11 s (2026-11-04, coordinator)
  sha256 d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950
  (byte-identical to the parent record's 2026-10-23 discovery pin and its
   2026-10-27 preflight re-fetch: the vintage is stable; every parent-record
   measurement carries over: G/P population 99,281 rows / 6,936 corridors /
   2000-2025; sum-all rule per corridor-year validated against BAMF)
```

## The redesign (what changed and why)

The parent task shipped one row per corridor-YEAR (eligibility >=500 at year D,
label = D+1 doubling). Two audits showed the panel self-answers: a label-year
T+1 row ships the year-T total that is the T row's label operand (frozen
recoveries eval AUC 0.975 / holdout 0.983). The redesign takes ONE row per
corridor, at its FIRST year >= 500 ("entry year" T0):

- No corridor contributes two rows, so no row can ship another row's label
  operand. The exact-copy exposure is gone STRUCTURALLY, not by feature
  pruning. The momentum feature family survives (see association below).
- Population: 1,129 of the 6,936 G/P corridors ever reach >=500 in a year.
- Eligibility and outcome are decided from information published at the
  instant (the year-T0 row is what makes the corridor eligible; the outcome
  years are T0+1 and T0+2).

## Measured one-shot population (probe_hdx_oneshot.py)

```
python3 candidates/unhcr-corridor-entry-surge/probe_hdx_oneshot.py
  (CSV default: the scratch download above; --json to capture)
```

- Corridors ever >=500: 1,129. Entries by year (first crossing):
  2000:193, 2001:57, 2002:88, 2003:63, 2004:21, 2005:23, 2006:19, 2007:20,
  2008:21, 2009:12, 2010:17, 2011:35, 2012:24, 2013:39, 2014:35, 2015:52,
  2016:36, 2017:43, 2018:52, 2019:44, 2020:8, 2021:33, 2022:79, 2023:58,
  2024:31, 2025:26.
- Labeled next-year rows (T0<=2024, host active in T0+1): 1,093
  (26 live-edge 2025 entries excluded; 10 host-silent-in-T0+1 excluded).
- Momentum-feature coverage: 761/1,093 have a published T0-1 value;
  192 are left-censored T0=2000 (panel starts 2000); 719 have >=2 prior years.
- One-shot base rates (n=1,093): decline 58.0% | >=1.5x 19.8% | >=2x 11.1%
  | >=3x 5.0%. (Panel task's label family for comparison: >=2x 9.3%.)
- Live edge at the observed 2026-08-20T15:33:49Z instant: 26 corridors
  entered 2025 (their outcome is entirely future: strict forecast rows);
  largest SSD->ETH 50,148 (South Sudan emergency into Ethiopia).

## Design table (probe_hdx_oneshot_designs.py) — the decisive measurement

```
python3 candidates/unhcr-corridor-entry-surge/probe_hdx_oneshot_designs.py
```

Gate minimums (qualify_dataset.py): eval AND holdout >=30 positives and
>=20 distinct events (origin|entry-year among positive rows). Splits below are
rows/positives/distinct-events, eligibility 500, entry-year windows mirroring
the panel task's label-year windows shifted by one:

| label family            | train        | eval        | holdout     | gate |
|-------------------------|--------------|-------------|-------------|------|
| next1_2x (house 2x)     | 709/68/57    | 183/25/20   | 201/28/28   | FAIL |
| next1_1.5x              | 709/118/94   | 183/45/34   | 201/53/49   | PASS |
| next1_g25 (>25% growth) | 709/185/136  | 183/59/46   | 201/68/59   | PASS |
| next1_3x                | -            | 183/11/8    | 201/16/16   | FAIL |
| cum2_2x (aggregate)    | 653/214/153  | 230/103/83  | 170/73/64   | PASS |

cum2_2x windows: train entries 2000-2014, eval 2015-2020, holdout 2021-2023
(outcome years T0+1..T0+2 must be published, so entries stop at 2023).
cum2_2x exclusions: 57 live-edge (entries 2024+2025: outcome includes 2026,
unpublished at the instant), 19 host-silent in an outcome year.

Key negative finding: the DIRECT analogue of the parent task (one-shot +
next-year 2x) does NOT clear the gate at the recorded eligibility
(eval 25, holdout 28 < 30) and has zero-positive entry years (2019 entrants'
label year is the 2020 COVID collapse; 2024 so far). Window re-drawing can
reach exactly 30 holdout positives (train 2000-2014 / eval 2015-2019 /
holdout 2020-2024: eval 35, holdout 30) but with ZERO margin and only by
capacity tuning - recorded, not chosen.

Threshold sensitivity (measured, same script): lowering eligibility to 200
makes next1_2x pass (eval 37/31, holdout 37/31) only by admitting sub-500
corridors whose "doubling" is small-number noise; cum2_2x passes at every
threshold tested (200/250/300/400/500). The recorded 500 eligibility is kept.

## Momentum association by label (the operator's "keeps corridor momentum")

Positive rate by growth INTO the entry year (T0-1 -> T0), eligibility 500:

| label      | <1.5x into entry | 1.5x-3x | >3x    | no published prior |
|------------|------------------|---------|--------|--------------------|
| next1_2x   | 5.8%  (n=87)     | 11.8% (n=279) | 16.2% (n=395) | 5.7% (n=332) |
| next1_1.5x | 13.8% (n=87)     | 21.1% (n=279) | 24.8% (n=395) | 14.2% (n=332) |
| next1_g25  | 23.0% (n=87)     | 32.6% (n=279) | 32.7% (n=395) | 21.7% (n=332) |
| cum2_2x    | 42.0% (n=81)     | 45.6% (n=270) | 37.5% (n=373) | 28.3% (n=329) |

- Next-year labels keep the parent task's momentum-continuation phenomenon
  (monotone increasing with into-entry growth; next1_2x risk ratio ~2.8x).
- cum2_2x INVERTS it (past-peak corridors revert; 1.5x-3x entrants sustain
  best). The momentum features remain the informative family, but the
  phenomenon includes mean reversion. This is a measured property of the
  aggregate-outcome label, recorded so construction describes it honestly
  rather than inheriting the parent's "momentum continuation" framing.

## PRIMARY design and measured fallback

PRIMARY: one row per corridor at first crossing; label = corridor total over
T0+1..T0+2 >= 2 x T0 total ("cum2_2x"). Chosen because it is the operator's
second named shape verbatim, keeps the house 2x threshold and the recorded
500 eligibility, clears the gate everywhere with 2.4x margin on holdout
positives (73 vs 30) and 3.2x on events (64 vs 20), has no zero-positive
entry year, and carries the richest live edge (57 corridors). Measured
splits (full population): train 653 rows/214 pos (32.8%), eval 230/103
(44.8%), holdout 170/73 (42.9%); prevalence drift train->holdout is recorded
as a phenomenon property. Under the parent's momentum-feature eligibility
(published T0-1 required): train 363/127, eval 202/98, holdout 159/72 - the
gate still passes, so construction may adopt the stricter rule safely.

FALLBACK (measured, not preferred): next1_g25 (will the crossing year's flow
grow >25% next year) if the operator reads "keeps corridor momentum" strictly
as continuation: eval 183/59/46, holdout 201/68/59, monotone association,
no zero-positive entry years. Threshold NOT to be re-tuned after any score is
seen; the fallback label choice must be made before construction scoring.

## Censoring rules (carried from the parent, re-applied per design)

- Corridor row missing with the host still reporting that year = observed 0.
- Host silent in an outcome year = unobserved target, row excluded (19 rows
  for cum2_2x, 10 for next-year labels).
- Left-censored T0=2000 entrants (192) have no published prior year: they
  stay in the full-population variant, are excluded by the stricter
  momentum-eligibility variant (capacity measured for both).

## Known-event fixtures (values from the pinned CSV, all UTC)

- AFG->USA: entered T0=2021 (533; 2020 was 44). Outcome 2022: 25,082,
  2023: 19,320 -> cum2_2x TRUE (44,402 >= 1,066). Post-Aug-2021 Taliban
  takeover. Also TRUE on next-year labels.
- VEN->COL: entered T0=2017 (582; 2016 was 316). Outcome 2018: 2,592,
  2019: 10,479 -> TRUE (13,071 >= 1,164). Venezuelan displacement.
- SYR->DEU: T0=2000 (3,069) is LEFT-CENSORED (crossed before the panel
  starts; no published prior). Outcome 2,653+2,174 = 4,827 < 6,138 -> FALSE.
  Recorded to show the left-censoring honestly, not as a known-event anchor.
- UKR->POL: entered T0=2014 (2,511; 2013 was 41). Outcome 2015: 2,295,
  2016: 1,194 -> FALSE (3,489 < 5,022). The 2022 Ukraine displacement is
  largely absent from this stream (EU temporary protection, not asylum
  applications) - the parent record's definitional insight carries over.
- SSD->ETH: entered T0=2025 (50,148, single-year corridor). LIVE EDGE: its
  outcome window 2026-2027 is entirely future at the 2026-08-20 instant -
  the strict-forecast case (historical rows are publication-lag nowcasts).

## Prediction timing - dated example (AFG->USA, all instants UTC)

Publication-lag NOWCAST (the abs-visitor-arrivals-direction / parent-record
pattern): the outcome window does NOT follow the instant for historical rows.

- Feature event window: 2000-01-01T00:00Z .. 2021-12-31T24:00Z (the
  corridor's published yearly totals; here rows exist 2002-2021; T0-1 = 2020
  total 44).
- First availability of year-T0 (2021) data on the machine-fetchable channel:
  the channel's annual refresh cycle (HDX package activity 2026-06-11/19/22
  refreshes; the 2026-08-20T15:33:49Z file carries 2000-2025). No archived
  vintages exist, so the historical instant is the first 2022-cycle refresh
  known to carry 2021 data - exact timestamp unobserved, current-vintage
  assumption, sha256-pinned, same posture as the parent record. What is NOT
  claimed: historical operational availability of today's vintages.
- Eligibility cutoff: the year-T0 row (533 >= 500), evaluated at the instant.
- Prediction instant: the first 2022 annual refresh carrying 2021 data.
- Target: 2022-01-01T00:00Z .. 2023-12-31T24:00Z (years T0+1, T0+2). At the
  instant (mid-2022) the window has partially elapsed but 2022 totals are
  unpublished on this channel (first published ~mid-2023) and most non-EU
  hosts have no public monthly corridor data - the forecaster's information
  set is genuinely years <= T0. For LIVE rows entering 2025 the whole
  outcome window follows the instant (strict forecast, SSD->ETH above).
- Label: (25,082 + 19,320) = 44,402 >= 2 x 533 -> TRUE.

## Contracts (reconciled 2026-11-04; carried evidence re-pinned today)

1. Redistribution: SUPPORTED - the parent record's class A evidence carries
   (HDX package cc-by-igo, CC BY 3.0 IGO legal code grants adaptations; RDF
   methodology page grants CC BY 4.0 on the same datasets; third parties
   already redistribute these panels under cc-by-igo). Re-verified live
   today: package_show license_id cc-by-igo. Acquisition is the documented
   bulk resource, no scraping of unhcr.org.
2. Timing: SUPPORTED with the documented current-vintage assumption - annual
   instant = first refresh carrying year-T0 data; the same nowcast framing as
   the parent and abs-visitor-arrivals-direction; no "window follows the
   instant" claim for historical rows; live 2025-entrant rows are strict
   forecasts. Limitation carried: annual grain only on this channel.
3. Target: SUPPORTED - label from the corridor's T0+1/T0+2 totals (source
   column Number of Applications, G/P rows, sum rule), never shipped as
   features; observed-zero vs host-silent censoring measured (19/10 rows).
   Eligibility (first >=500 year) is decided from at-instant information
   only - no whole-corridor future inclusion leaks into eligibility.
4. Split capacity: SUPPORTED for the primary design with margin (eval
   103/83, holdout 73/64 vs minimums 30/20; measured both full-population
   and momentum-eligibility variants). The direct next-year-2x analogue is
   measured NOT viable (25/28) - recorded above.
5. Not a mirror: SUPPORTED - novelty searches 2026-11-04 (below) + the
   parent's prior-art list; no released corridor-grain first-crossing task
   with fixed temporal splits and a scored contract exists.

Remaining limitation (recorded, construction must carry it): the one-shot
design's rows share origins across windows (a later entrant's origin-level
aggregates can contain components of an earlier entrant's outcome years).
That is partial information, not the parent's exact-copy exposure; the gate's
cross-row probe must still be run on the built artifact (gate 1.5.0), and the
origin/host aggregate features should be declared to it.

## Novelty (searches 2026-11-04, mechanical, anonymous)

Queries: "asylum applications corridor prediction benchmark machine learning
dataset splits"; "new asylum corridors emergence first time crossing
threshold prediction displacement early warning"; "huggingface OR zenodo
asylum corridor dataset train holdout prediction task UNHCR". Prior art
(same set the parent found, none a released first-crossing corridor task):
bilateral monthly Eurostat forecasting (J Econ Geography 25(1):3, 2025;
BSE WP 1387), Italy-aggregate 6-month forecasting (Cambridge Data & Policy
2024), JRC122178 4-week EU system, Napierala et al. 2022 cusum early-warning
alerts (EU weekly/monthly, detection not a released benchmark), OECD Migration
Anticipation and Preparedness (2025, a survey), arXiv:2505.06249 early-warning
displacement (origin-grain monthly, no released task), HF/Zenodo raw-panel
repackages only. Verdict recorded via scripts/check-novelty.py:
differentiated - ours is a one-row-per-corridor first-crossing benchmark on
the global (130 hosts, not EU27) UNHCR channel with fixed entry-year splits
and a scored contract; theirs is EU-focused monthly panel forecasting,
aggregate nowcasting, or unreleased research code.

## What construction must NOT do (handoff constraints)

- No two rows per corridor (the reopen condition); no feature computed from
  any year > T0; no re-tuning of the 2x threshold or eligibility after any
  score is seen; run the gate 1.5.0 cross-row probe on the built artifact
  and declare the origin/host aggregate features to it; construct and audit
  FRESH from the source (fresh attempt ID; the dropped v2026.10 package is
  never published and its bytes are not reused).
- Deciding check after the gate + exact-byte acceptance: reference baselines
  on the accepted artifact (majority; identity-only origin/host; naive
  momentum into-entry; persistence) - the wb-loan-disbursement-completion
  precedent: if identity-only matches the reference model, the candidate is
  dropped for no headroom, not published.
