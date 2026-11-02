# Verification record - ocha-fts-appeal-funding-trajectory v2026.11

Artifact `ac529cd4e9d4da90f804ecef425e74c94a946b857fe39095fd73a0407506b8c0`,
gate 1.5.0. What was verified, how, and what is **not** covered.

## Verified

| Check | Evidence |
| --- | --- |
| Qualification on the full artifact, on the worker | Job fts-appeal-003 (2026-11-02, cx23/hel1, 1396.6 s, exit 0): gate 1.5.0 `ok: true`, `failed_checks: []` over all 758 rows; contract checks 6/6. Report shipped as `qualification.json`. |
| Exact-byte acceptance on the worker | `--accept` ACCEPTED for `ac529cd4...` against the gate's own report (run.sh stage 3; nothing scored before it). |
| References reproduced after the rebuild | Job fts-appeal-003 stage 4, post-acceptance: every reference matches the pre-rebuild figures to the last digit - persistence 0.7171136653895275, prior-mean 0.7143465304384845, ask-size 0.7126436781609196, country-history 0.6729459344401874, plan-type 0.669220945083014, majority accuracy 0.5827338129496403, per-year persistence 0.73611 / 0.66579 / 0.74716 / 0.72727. Equality proves both the unchanged panel and the scorer-side recompute. |
| Rows unchanged by the remediation | train 437/279, eval 139/81, holdout 182/96 - identical to the audited e7441e1f artifact; the rebuild removed columns, not rows. |
| Download + checksums + re-accept | Job fts-baseline-002 (2026-11-02, 52.8 s, exit 0): the five accepted assets fetched from private staging release 431492902 with every sha256 verified on arrival, then gate `--accept` re-run on the fetched bytes BEFORE any score (accept.log: ACCEPTED, matches `ac529cd4e9d4da90`). |
| Runner-contract baseline on the released bytes | Same job: benchmark's own `train.py` + `validate.sh` unmodified (bundled sha256 equal the read-only clone's, recorded `unmodified: true`), `[validate] CONTRACT OK`, eval AUC **0.6452** from both the runner's own log and `validate.py`'s independent predict_proba recompute. Workdir materialized from public splits only; the holdout was never copied. Result: `measurements.json` and the candidate record. |
| In-build fixtures (units and frame) | Asserted on every build (exit 0 proves them): AFG 2023 orig 4,627,363,573 / funding 1,678,347,238 / label 0 (revised 3,227,372,908 NOT the denominator); YEM 2023 funding 1,774,327,599; Burundi RRP 2021 slice 14,978,233 of 19,282,778; flow-vs-CSV within the 10% guard, 37/758 disclosed differences. |
| Label provenance | Every label recomputed independently in the 2026-11-01 audit from the staged compact source caches: 0/758 label discrepancies, 0 original-requirement discrepancies, 0 country discrepancies. |
| Licence instruments | FTS use-and-republish terms and the HDX record's CC BY-IGO, both read 2026-10-29 and quoted in the candidate record's license_evidence; attribution carried in `LICENSE.md`. Class A (explicit permission for redistribution and derivatives with attribution). |
| Worker cleanup | Both workers collected then destroyed with provider 404 read-backs (fts-appeal-003: server 174163321; fts-baseline-002: server 174177604; project server list empty). |

## The finding, stated with its qualifier

The stock runner's full model scores **0.6452** eval AUC; the persistence
reference (`persistence_last_coverage`, scorer-side recompute from prior-in-time
labels, train+eval only) scores **0.7171136653895275** on the identical 139 eval
rows. The model trails persistence by 0.0719 and every other measured reference
except the majority-class rate: **no demonstrated headroom under this protocol
for the stock runner**. The information-asymmetry note travels with the number:
the model is deliberately denied the last prior same-country outcome (the P0
recovery channel), while the persistence reference reads it scorer-side. An
observed result on these rows with this configuration - not a bound on other
models, not an operational-validity claim.

## NOT covered

- **No historical-vintage reconstruction.** The FTS API exposes no historical
  vintages (checked); which values were visible at each past instant cannot be
  re-established, and no as-of claim is made. The panel is current-vintage
  retrospective research data under a restricted-protocol declaration
  (`quality.json` `evaluation_contract`, access `isolated_rows`).
- **No full independent API re-harvest.** The audit's label recompute used the
  staged compact source caches, not fresh API responses; the original raw API
  response bodies were not retained by the builder. Rebuilding today fetches
  the current vintage and may differ from the shipped bytes if the publisher's
  data has moved.
- **No holdout evaluation.** The holdout was fetched for exact-byte acceptance
  but never scored, never copied into a workdir, and stays sealed until the
  design is frozen.
- **No agent/harness comparison.** The baseline is the runner contract only; no
  claim is made about coding-agent performance.
- **A fresh independent pre-flip audit of these rebuilt bytes** is required
  before any public flip: the 2026-11-01 audit's frozen attack code recovered
  labels on the PREVIOUS artifact; it must be re-run label-blind against these
  bytes and find no operand columns. That audit has not yet been executed for
  this version.
