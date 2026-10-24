# Prediction contracts and dataset suitability

A dataset is useful for a stated purpose, not universally certified. Gate 1.5 separates
structural consistency from historical availability. Existing frozen artifacts remain
reproducible under their original gate; they are not retroactively accepted by gate 1.5.
Current suitability records apply to exact dataset/tag/artifact identities and live outside
those immutable packages in `suitability/`.

## Research and final evaluation

`public/train.csv` is fitting data. `public/eval.csv` is labeled development/validation data:
model selection, early stopping and keep/discard decisions intentionally use it. It is not an
untouched final test. `private/holdout.csv` is final scoring data, excluded from agent development.
The downloadable holdout is public, not cryptographically sealed. Isolation in a run and public
availability are different properties. Joint labels matrices and all other auxiliary outcome
files must remain outside solver inputs, even when public for reproducibility.

A frozen predictor may receive only information available for the stated decision. Historical
panels must not be handed wholesale to arbitrary prediction code: a later row can expose an
earlier outcome. This is a protocol vulnerability, not proof that a particular baseline exploited
it. The original template fits XGBoost on train and predicts row-wise, but the original scorer
passes the full holdout feature frame. Never describe its historical scores as obtained under
new isolation enforcement.

Retrospective research with stated timing assumptions remains useful. Operational forecasting
claims require stronger evidence. Neither a high score nor a bounded unsuccessful attack proves
historical validity or optimal honest-model headroom.

## Required before new construction

Record the decision/user, prediction instant, outcome horizon and availability, source release
calendar, revision policy, scored population, and solver-visible files. Distinguish observation
time from availability time. An earlier inspection start does not prove its citations were known;
a past statistical reference month does not prove its revised value was published then.

Create `quality.json.evaluation_contract` in the builder. Do not retrofit assumed fields as
verified to make a gate pass. Required fields:

- `use`: `retrospective_research` or `historical_forecasting`.
- `access`: `isolated_rows`, `chronological`, or `common_cutoff_batch`.
- `feature_evidence`: every shipped non-target column (including IDs/carry columns) mapped to
  `source`, `availability` explanation and `status` (`verified`, `assumed`, `unverified`).
- `vintage`: `kind` (`as_of`, `current_snapshot`, `mixed`) and specific `evidence`.
- `selection`: `kind` (`prediction_time`, `outcome_conditioned`) and specific `evidence`.
- `limitations`: a nonempty list of concrete limitations.
- `training_label_timing`: `unverified` if there is no measured ledger; never claim verified
  solely because prediction dates are disjoint.
- `cross_row_audit`: `rationale`, `auxiliary_files_review`, and `probes` (possibly empty only
  with a source-specific explanation of why no probe applies). Review every config, not a proxy.

Gate checks are not source-authenticity proofs. Review citations and code independently, and
record the evidence status in the public suitability summary. For real-time forecasting the
source must support historical vintages, each input's availability must be verified, and scored
membership must be decidable at prediction time.

## Full-row availability ledger

For historical forecasting, supply `availability_ledger`, a relative private artifact path to CSV:
`split`, all `id_columns`, `prediction_time`, `features_available_at`, `label_available_at`.
Timestamps must include timezone. There must be exactly one entry for every row, with a unique
composite ID. `features_available_at` is the latest availability of any supplied input, including
joined histories and revised attributes. Preserve the supporting source timestamps/evidence;
the ledger is a measured construction output, not a value guessed from the row date.

The gate checks features precede prediction; all training outcomes precede the first validation
prediction; all training and validation outcomes precede the first holdout prediction (validation
feedback selected the final algorithm). Use a sufficient embargo, an explicit historical model
freeze cutoff, or revise the task. Date-disjoint splits alone are insufficient. Ledger bytes are
hashed into qualification and reverified by `--accept`. Never mount this outcome-timing ledger
into an evaluated agent. Retrospective tasks may qualify without it only with label timing
explicitly unverified, and must not be marketed as verified historical forecasts.

## Cross-row probes

Each probe has `entity_columns`, `time_column`, `left`, `operation` (`copy`, `gt`, `lt`,
`scaled_gt`) and optional `right`, `threshold`, `scale`. It points a donor row to an earlier
row using `offset_days`, `offset_months`, or `lag_days_column`. The operands are donor features;
target labels cannot be operands. Set `right_row: earlier` to compare a donated price with the earlier row’s own feature. Donors include train for validation and train+validation for holdout; future private splits are never donors to development. The gate executes the joins on each full split on the worker,
requires singleton target keys and unanimous donors, and records coverage and mismatches.
No AUC is manufactured for abstentions. Examples:

- Food/MSHA: entity licence/mine, inspection date, day lag, copy previous-target flag.
- ABS: country, month, offset 1 month, `val_m < val_m12`.
- EUTL: installation, year converted to calendar date by construction, offset 12 months,
  copy `net_short_l1`.
- FluNet: country/week, offset 28 days, `10 * inf_all_w > denom_w`.
- NOAA: station/date, offset 1 day, `observed_max_ft > threshold_ft`. Nonzero mismatches
  against the official flag do not make the exposed outcome measurement permissible.

The generic probes are a bounded mechanism, not an exhaustive attack search. Add source-specific
probes for multi-row price ledgers, alternative histories and auxiliary files. A declared outcome
probe with covered rows requires restricted access; it does not force a useful retrospective
artifact to be discarded. No applicable probes is a reviewed claim, not a silent default.

## Labels and release decisions

`scripts/check-suitability.py` checks every package has a version-bound evidence record. Use
`retain_restricted` for retrospective research with unresolved timing; `retain` requires verified
availability and training-label chronology, as-of vintage and prediction-time selection.
`rebuild_before_use` and `retire` cannot be newly recommended publicly by the site pipeline.
A bounded no-recovery result is not an unrestricted retain decision.

Sites and current GitHub/Hub notices use the same public projection. Private source paths and
operational review notes are excluded. Correct inaccurate current claims explicitly; preserve
original data, checksums and tags. Editorial revisions advance site_revision, never data tags.
A new data version needs the full worker qualification, acceptance and release procedure.

## Current disposition (24 October 2026)

All ten published datasets remain available for restricted retrospective research; none is
certified as a historically faithful operational forecast by this review. Seven have demonstrated
cross-row exposure under the supplied audit; Austin, DOAH and TSB have bounded no-recovery findings.
NHS and NZ-EA remain private and require reconstruction/review before use or publication.
NOAA's current notice corrects row D versus label D+1 and raw-max versus official-flag semantics.
See each exact-artifact record for evidence, limitations and prerequisites.

## Existing harness adapter

`python3 scripts/install-prediction-adapter.py --source <read-only-harness> --destination <new-worker-execution-copy>`
creates an owned execution clone and replaces only its holdout scoring entrypoint. It preserves
the existing train.py/predict_proba contract, experiment loop and sklearn metrics. It never edits
`../harness_benchmark`. Use the existing trusted benchmark image (`BENCH_IMAGE`) on a worker host,
with `FACTORY_PREDICTION_TIME_COLUMN` set to the reviewed prediction-order column. Set
`FACTORY_SCORE_TIMEOUT` within the job allowance. No image build or data processing belongs on
the coordinator. Worker-host execution is required; nested Docker paths are refused.

The scorer sends one chronological feature row, waits for a committed probability, then releases
the next row. Candidate code runs without network, with only train.py/task.json/train/eval mounted
read-only. Holdout files, targets, availability ledgers and credentials are not mounted. Past rows
may remain in process memory: this is chronological access, not a fresh process per row. No
future-row lookup is possible through the supplied stream. The adapter does not repair historical
feature vintages, label-delay contamination in development data, or model contamination from
previous exposure to public holdout labels. Those limitations must stay attached to any score.

Validate the adapter on a worker with the real runner before reporting it operationally verified.
Software protocol tests are not acceptance-task benchmark runs. Record image ID, runner commit,
adapter hash, exact data identity and protocol beside every new score; never compare protocols
without naming the difference.
