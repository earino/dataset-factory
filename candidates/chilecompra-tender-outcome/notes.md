# chilecompra-tender-outcome — notes

ChileCompra / Mercado Público (Chile). Opened 2026-10-21 in the Latin America discovery tick.
Everything below was measured anonymously from the coordinator (no ticket, no registration).

## Access probes

`python3 probe_desertion.py` (kept in this directory) — 2026-10-21, 214 requests, 2.67 MB, 209 s:

- Monthly licitación totals via `https://api.mercadopublico.cl/APISOCDS/OCDS/listaOCDSAgnoMes/{y}/{m}/1/1`
  (`pagination.total`): 2010-01: 33,366 · 2014-01: 22,218 · 2018-01: 13,049 · 2020-01: 11,661 ·
  2023-01: 11,382 · 2025-01: 7,785. (Earlier quick probes also: 2012-01: 27,701; 2015-01: 20,228;
  2021-01: 7,431; 2026-01: 8,101; 2026-06: 9,302.)
- First 100 processes of closed month 2019-06, award docs fetched: `active` 78 (79.6%),
  `unsuccessful` 17 (17.3%), `cancelled` 3 (3.1%); 2 processes without `urlAward`.
- First 100 processes of 2023-06: `active` 78 (79.6%), `unsuccessful` 14 (14.3%), `cancelled` 2 +
  `cancelled | 15-Revocada` 2 (4.0%), 1 empty status; 2 without `urlAward`.
- Award statusDetails vocabulary observed: `7-Desierta (o art. 3 ó 9 Ley 19.886)`, `8-Adjudicada`,
  `15-Revocada`. The desertion label is directly machine-readable in the OCDS award release.
- Doc sizes: award docs avg 11,418 B (2019-06, n=98) / 8,488 B (2023-06, n=98); tender docs avg
  100,620 B (2019-06, n=5) / 31,987 B (2023-06, n=5). API throughput ~1 req/s ⇒ per-process
  fetching cannot build the historical panel; the monthly bulk zips below are the channel.

## Bulk monthly OCDS zips (construction path)

Found in the datos-abiertos React bundle (`main.b731c6dc.js`, 3.1 MB): the descargas page
documents `https://ocds.blob.core.windows.net/ocds/yyyymm.zip` with "variantes URLs en las que
se modifique la fecha del archivo".

Ranged GET (bytes 0-3, PK magic + Content-Range), 2026-10-21:

- 200901, 200906, 201001, 201406, 201806, 201906, 202006, 202106, 202112, 202202, 202203,
  202204 → real zips. Sizes: 201001: 377,010,777 B; 201406: 948,139,521 B; 201806: 613,891,953 B;
  201906: 1,131,029,693 B.
- 202205, 202206, 202212, 202301, 202306, 202509, 202510 → clean Azure 404 ("The specified blob
  does not exist").

Series = 2009-01 .. 2022-04 (160 months). Panel bytes ESTIMATE ~100-150 GB compressed.

## Provenance streams (per the discovery skill's stream-mix rule)

The OCP registry (data.open-contracting.org/es/publication/144, fetched 2026-10-21) records
that the publisher's bulk downloads carry **only the Licitación stream**; Trato Directo
(`listaOCDSAgnoMesTratoDirecto`) and Convenio Marco (`listaOCDSAgnoMesConvenio`) are separate API
streams. The task is defined on the licitación stream only; streams are not summed. The OCP's own
harvest (Jan 2022–May 2026, all streams) counts 4,920,375 licitaciones / 4,939,558 awards —
cross-check aggregate only. OCP also hosts per-year mirrors (full.jsonl.gz 2,527 MB; 2022: 506 MB;
2023: 620 MB; 2024: 682 MB; 2025: 434 MB; 2026: 186 MB) — not the construction bytes; publisher
bytes preferred.

## Licence channels (posture procedure, all 2026-10-21)

1. OCP registry: "Licencia: Creative Commons CC0 1.0 Universal Dedicación de Dominio Público …
   Puede copiar, modificar, distribuir e interpretar la obra, incluso para propósitos comerciales,
   sin pedir permiso."
2. Publisher's own terms (chilecompra.cl/terminos-y-condiciones/): "La plataforma de Datos
   Abiertos, a disposición del público en general … en formatos que facilitan su análisis,
   monitoreo y fiscalización, así como la reutilización de la información para el desarrollo de
   nuevos informes o aplicaciones." Also confirms the platform publishes in the OCDS standard.
3. Statutory: chilecompra.cl/datos-abiertos/ — the Ley de Compras Públicas amendments effective
   2024-12-12 require "formatos de datos abiertos y reutilizables" for all system information.
4. Channels with NO licence statement (measured): datos-abiertos React bundle (grep for
   licencia/términos/creative commons: no match); OCDS list API metadata (no licence field);
   publisher publication-policy URL recorded by OCP
   (api.mercadopublico.cl/APISOCDS/Utilidades/Politicas/Actualizacion → HTTP 404);
   datos.gob.cl CKAN package_search q=chilecompra → count 0; Política de Gobierno de Datos PDF
   (Res. Exenta 143-B/2024) = internal staff rules only.
5. Field dictionary for the (ticket-gated, unused) v1 API:
   chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-Licitaciones.pdf
   — documents tender states "publicada, cerrada, desierta, adjudicada, revocada y suspendida",
   buyer fields, procedure-type codes L1/LE/LP/LQ/LR/E2/CO/B2/H2/I2/LS, currency and payment-term
   code tables.

## Novelty

`check-novelty.py` run 2026-10-21, verdict `differentiated` (in record.json). Prior art compared
explicitly: TenderKG (FR, bidder recommendation), ANAC-Italy tender-variation ML, TED/CAN
void-rate analysis (Springer 2026), MiDES (BR municipal raw tables). None ships a
desertion-prediction task with splits and a scored contract.

## Verdict

GO (ready) 2026-10-21. All four discovery contracts hold with measured evidence: licence
(CC0 registry + publisher reuse terms + statutory mandate), timing (publication instant;
award fields excluded), target (award status unsuccessful/desierta, 14–17% measured base rate),
splits (160 anonymous bulk months; windows proposed in record.json), not a mirror (novelty
check recorded). Next action in record.json names the construction steps.

## 2026-10-23 advancement: built, qualified and accepted (job cl-tender-002)

Constructed on a Hetzner cx23 (`cl-tender-002`, 1,120.8 s, EUR 0.06 reservation). The
construction channel is the monthly OCDS bulk zips, parsed member by member (entries are
STORED, one JSON record package per process, central directory readable by ranged GET).

**Cohort choice was forced by a measured vintage defect.** The 2016 zips were rebuilt at
migration (blob Last-Modified 2020-03) and carry a single release stamped 2018-12-31 with
`tender.status = "complete"` and the final text: a compiled state, not a publication
snapshot. Sampled 201906 (n=12) and 202101 (n=18) carry a genuine progressive history -
first release == `tenderPeriod.startDate` within 0-1 days, status `active`, 3-7
tenderUpdates, status moving to `complete` at closing. The build therefore *requires*
`tender.status == "active"` on the first tender release and buckets anything else as
`publication_state_not_evidenced` (2 / 12 / 14 rows). The 2016 cohort was abandoned before
any download of it; no 2016 artifact exists.

Splits (same calendar months, one year apart): train 2019-05..06, eval 2020-05..06,
holdout 2021-05..06. Membership is the first tender release's month; the award release is
read afterwards only to compute the label. Cancelled awards and processes without an award
release are counted per split as `unobserved:*`, never used as a membership rule.

| split | rows | positives | rate | distinct positive days |
| --- | --- | --- | --- | --- |
| train (2019-05/06) | 23,457 | 4,151 | 0.1770 | 53 |
| eval (2020-05/06) | 11,943 | 1,992 | 0.1668 | 50 |
| holdout (2021-05/06) | 17,319 | 4,351 | 0.2512 | 51 |

Unobserved: train 794 none / 774 cancelled, eval 556 / 605, holdout 861 / 743. The
holdout's zips are the 2021-12-31 vintage, so its outcome window is ~6.5 months (latest
release seen 2021-12-30); train's is ~17 months. 86 labelled rows disagree between award
status (`unsuccessful`) and compiled tender status (`active`); recorded, not resolved away.

**Qualification: PASSED** - gate 1.4.0, 38/38 checks, 0 failed, on the full artifact on the
worker; `--accept` re-verified `6f8cef93850f1211` on the coordinator against the
download-verified bytes. No single shipped column determines the target; only `tender_id`,
`estimated_value_clp` and `pub_date` are declared high-cardinality. `--selftest` passed
with the unchanged gate and fixtures.

**Simple references (eval rows only, fitted on train):** procedure 0.5164, buyer region
0.5309, UNSPSC segment 0.5673, calendar/identity 0.5270, value-band x procedure 0.5410;
majority-class accuracy 0.8332. Persistence is recorded INAPPLICABLE (one row per tender,
no per-entity series) rather than replaced by a lookalike. These are single-feature
conditional rates, **not** a model - no headroom claim exists and none may be quoted.

Artifacts: staging release `job-cl-tender-002` (id 421653257); bulk CSVs stay there, only
compact reports collected to `.factory/cl-tender-002/reports/` (digest-verified).

Next: baseline job with the harness runner against this exact artifact, compared on eval to
the 0.5673 UNSPSC reference and reported per split (holdout prevalence 0.2512 vs train
0.1770 makes a pooled number unreadable). Package only if headroom is real.

## 2026-10-23 selection review (operator-directed): the four questions, answered from the publisher's records

Probes kept in this directory: `probe_horizon.py` (241 requests, 7.2 MB, 246 s; first 40
processes of each cohort month 2019-06 / 2020-06 / 2021-06, tender + award docs) and
`probe_horizon2.py` (99 requests, 3.3 MB, 107 s; first 15 per month, detail-preserving,
plus the first 5 urlContract docs of 2021-06). Aggregates in the raw outputs kept at
`/opt/data/cache/scratch/cl_probe_horizon{,2}.json` (scratch; distilled here).

1. **Publication-time field for every tender: YES.** 119/119 sampled processes carry a
   first tender release dated at the publication instant with `status: active` and the
   full publication-time feature set. Full-build measurement (cl-tender-002 buckets):
   `publication_state_not_evidenced` only 2 / 12 / 14 rows per split cohort-pair.
2. **Award status/date or contract signature date: award YES, contract signature NO.**
   Award release `date` present on 100% of award releases; per-entry `awards[].date` on
   110/119 sampled entries. `urlContract` documents exist only for 2021+ list items and
   every sampled contract carries `signatureDate: null` and `date: null` - only
   `period.startDate` (the delivery period) exists. The terminal state must therefore be
   defined on award status + award release date. Observed award statuses: active,
   unsuccessful, cancelled, pending. (statusDetails, which carried the 7-Desierta /
   8-Adjudicada / 15-Revocada vocabulary on 2026-10-21, was empty in every 2026-10-23
   sample; the label rule uses status only, so nothing depends on it.)
3. **Eligibility from publication-time fields only: YES for membership** (first tender
   release month + publication state + ocid). The scored-row restriction to observed
   terminal outcomes is outcome-dependent; the rebuild declares it as such and measures
   it per split (`outcome_conditioning` in quality.json / summary.json).
4. **One terminal award state and horizon: YES.** Terminal vocabulary
   {active -> adjudicated, unsuccessful -> deserted, cancelled -> revoked}; pending is
   non-terminal. Horizon H = 180 days after publication, frozen from the measured lag
   distribution (first-award-release lag p50 33-41 d, p90 49-102 d, max 526 d for one
   2020-06 outlier) and capped by the zip vintages: every cohort zip covers pub+180 d
   for every row (train 2021-01-13, eval 2021-01-14, holdout latest release 2021-12-30
   vs 2021-06-30 + 180 d = 2021-12-27). 180 d is the MAXIMUM uniform horizon the source
   supports. Sampled terminal-within-180d: 40/40 (2019-06), 36/39 (2020-06), 40/40
   (2021-06); the not-terminal cases were awards at +375/+375/+526 d - real late
   processes, right-censored at the horizon by design.

Extra findings: (a) award status sequences were single-release for every sampled
process and pooled-any-active vs last-terminal-within-180d agreed on all 119 - but the
publisher's tag vocabulary includes `awardUpdate`, and the previous build's exact
`"award" in tags` filter silently ignored awardUpdate-tagged releases; the rebuild
matches any award-prefixed tag. (b) The previous build's compiledRelease label fallback
is dropped in the rebuild (a compiled award cannot always be dated into the horizon);
its impact is measured by the `unobserved_target:compiled_only_awards` bucket instead of
being assumed away. (c) The two not-urlAward processes per 100 (2026-10-21 probe)
reappear as right-censored rows under the horizon rule.

## 2026-10-23 rebuild (cl-tender-003) - what changed and why

All four questions supportable, so the operator's "rebuild once" branch was taken.
Changes in `source/build.py`: terminal-state-within-180d label rule
(`terminal_outcome`), award-prefixed tag filter, compiledRelease fallback dropped
(bucketed), honest `row_selection` with derived cohort months (the old prose still said
"2016-05..2016-06 / 2021-01..2021-02"), measured zip-vintage `observations`, per-split
`outcome_accounting` in summary.json and `outcome_conditioning` in quality.json.
`source/score.py` gained `--previous-eval` (shipped `previous_eval_rows.txt`: the
11,943 (ocid, label) pairs of cl-tender-002's eval CSV, downloaded from staging release
421653257 asset file-0003-part-0000, sha256 f4865ce092061ddbeffc5a341c96ffd65f1b2621ba8
aa36b4b8704c3d4bd8782) so the references against the 0.5673 UNSPSC bar are measured on
identical rows, with the row-set movement and label disagreements quantified.

Synthetic-fixture smoke (`tests_smoke_build.py`, kept in this directory) runs the real
build + gate + accept + score over fabricated member documents covering every label
path; it caught two real defects before worker spend: the awardUpdate tag filter and
the horizon's timestamp-exact boundary (pub 12:00 + 180 d cuts at 12:00, not midnight).
SMOKE OK; gate selftest OK; `check-candidate.py` OK. Worker cl-tender-003 launched
2026-10-23T12:20:41Z (server 172043826, EUR 0.06 reservation).

### cl-tender-003 verified outcome (worker follow-up, 2026-10-23)

Exit 0 after 48.4 min; staging release 421857839 (tag job-cl-tender-003). Verified from the
collected, sha256-manifest-verified bytes in .factory/cl-tender-003/reports/:

- Gate 1.4.0: 38/38 checks, 0 failed, on the full artifact on the worker; `--accept` on the
  exact bytes -> `ACCEPTED: /output/extract matches the qualified artifact 27e610ba65e13805`.
- container.log stage order: build -> qualification -> acceptance -> simple references;
  no performance figure exists before acceptance.
- Splits (gate recomputed from rows, equal to the build summary): train 23,188/4,089 (17.63%),
  eval 11,791/1,959 (16.61%), holdout 17,236/4,333 (25.14%); 52/50/51 distinct positive days;
  mixed_terminal 0, duplicate_ocid 0 in every split.
- Outcome conditioning (scored = observed-terminal subset), per split train/eval/holdout:
  scored_share 0.9262/0.8990/0.9105, censored_rate 0.0453/0.0566/0.0512, revoked_rate
  0.0286/0.0444/0.0383; unobserved-target buckets counted, never inferred.
- References (eval only, fitted on train, post-acceptance): procedure_only 0.5183,
  region_only 0.5330, unspsc_only 0.5707, calendar_only 0.5295, value_procedure 0.5443;
  majority-class accuracy 0.8339 on 11,791 rows; persistence INAPPLICABLE (one row per tender).
  previous_eval_comparison vs cl-tender-002: identical rows 11,791, old_only 152, new_only 0,
  label disagreements on identical rows 0; the 0.5673 UNSPSC bar (11,943 rows) re-measures at
  0.5707 on the identical rows under the new labels.
- Cleanup: worker destroyed 13:17:15Z through the supported lifecycle; provider-confirmed
  (GET /servers/172043826 -> 404 'server not found'; project primary IPs: []).
- No baseline model job, no packaging, no publication - advancement owns the review sign-off
  and the baseline decision.

## 2026-10-23 assisted-review sign-off (advancement, operator-directed)

Decision: RESOLVED. The declared outcome-conditioning and the 180-day terminal-state rule
close the assisted review; artifact 27e610ba65e13805 (cl-tender-003) is the accepted evidence
base and the baseline decision may proceed on it. Full reasoning is in `record.json`
`review.signoff`; the substance:

- The label is now a deterministic function of a closed, vintage-covered window (last
  terminal award status within pub+180d; frozen horizon capped by the zip vintages;
  mixed_terminal 0, duplicate_ocid 0; awardUpdate releases matched).
- The scored population is no longer misdeclared: membership is publication-time-only, and
  the scored subset is DECLARED outcome-dependent with per-split measured rates
  (scored_share 0.9262/0.8990/0.9105, censored 0.0453/0.0566/0.0512, revoked
  0.0286/0.0444/0.0383), which quality.json requires to be quoted beside any score.
- A conditional (competing-risks style) population is a legitimate task when declared with
  measured rates; the review's defect was the false publication-time claim plus the
  ill-defined any-active label, and both are gone.
- Scope limitation carried forward: every score describes the conditional population only
  (~90-93% of eligible rows); deployment over all published tenders faces the excluded
  revoked (~3-4%) and unresolved-at-180d (~5%) cases.

Baseline decision criterion (recorded before the run): model eval AUC vs the unspsc_only
0.5707 bar on the identical 11,791 eval rows, decided on the paired difference with a
publication-day-clustered bootstrap interval (the day is the gate's independence unit).
Headroom is demonstrated only if the model exceeds the bar AND the clustered interval
excludes zero; otherwise the finding is negative-or-inconclusive and gets recorded as such.

## 2026-10-23 runner-contract baseline (cl-tender-baseline-001): NO HEADROOM - negative finding recorded, candidate dropped

The one operator-authorized baseline job ran on the accepted artifact 27e610ba65e13805 (fresh attempt
id, server 172057629, 116.1 s container, exit 0, EUR 0.06 reservation, worker destroyed
provider-confirmed). Bytes fetched from staging release 421857839 with on-arrival digest checks and
RE-ACCEPTED on the worker before any scoring; the private holdout was fetched for re-acceptance only
and never entered the workdir; the benchmark's runner was bundled verbatim (hashes identical to
tsb-baseline-001's record).

On the identical eval rows (identity asserted in-job: 11,791 rows / 1,959 positives / 23,188 train):

- Model (unmodified train.py, XGBoost 3.4.1): eval AUC 0.4752 - three agreeing implementations
  (train.py's print, validate.py's recompute, reference_check.py's independent std-lib AUC).
- unspsc_only bar, recomputed independently from the fetched bytes: 0.57075 (accepted 0.5707;
  0 fallback rows, 55 segment levels).
- Paired difference -0.0955; publication-day-clustered 95% bootstrap CI [-0.1134, -0.0745]
  (1000 resamples, 0 skipped, 58 distinct eval days); naive row bootstrap [-0.1159, -0.0741].

The full model loses to the one-column reference decisively, and sits below 0.5. Under the
pre-declared criterion (model must EXCEED the bar with the clustered interval excluding zero) this is
no demonstrated headroom; per the operator directive the negative finding is recorded and the candidate
is DROPPED (no packaging, no publication). Outcome-conditioning rates quoted beside every score:
scored_share 0.9262/0.8990/0.9105, censored 0.0453/0.0566/0.0512, revoked 0.0286/0.0444/0.0383
(train/eval/holdout).

Recorded as an UNVERIFIED hypothesis, not a diagnosis: an eval AUC below 0.5 suggests the model
learned feature-label associations that reversed between the 2019 train cohorts and the 2020 eval
cohorts (plausible regime change, e.g. pandemic-era procurement), while the single stable categorical
keeps modest signal. Further diagnosis was outside the one-job authorization and would not change
the criterion's verdict. Reopen conditions are in record.json next_action.
