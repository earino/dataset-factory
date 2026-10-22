# Refactor brief: one release record, one reader

## The problem

A published release is described by six files written by different code at different times, and
nothing enforces that they agree:

| File | Written by | What it holds |
| --- | --- | --- |
| `release/<ds>/MANIFEST.json` | `scripts/release-manifest.py` | artifact id, assets, splits, licence, baseline, destinations |
| `release/<ds>/DESTINATIONS.json` | publisher / hand | per-destination verification |
| `release/<ds>/quality.json` | the dataset's `build.py` | features, timing, unit/frame declarations, splits (paths *or* counts) |
| `release/<ds>/summary.json` | the builder | split counts, builder stats |
| `candidates/<ds>/record.json` | research sessions | status, qualification, jobs, measurements |
| `candidates/<ds>/baseline/baseline_result.json` | baseline job | the eval AUC and references |

Consumers (`scripts/build-dashboard.py`, `factory/dashboard_render.py`, `factory/site_model.py`,
`factory/site_hf.py`, `scripts/hf-publish.py`, `factory/site_pipeline.py`) each implement their own
fallback. A missing or differently-shaped field does not fail at write time; it renders as "no data"
or "—", and is noticed weeks later by a human looking at a page.

### Bugs this produced in a single day

1. **Rows missing** for `abs-visitor-arrivals-direction` (manifest `splits: {}`, counts only in
   `summary.json`) and `noaa-tide-flooding` (splits nested under a level name).
2. **Baseline AUC missing** for six releases. The number existed under five key names:
   `eval_auc`, `train_py_eval_auc`, `auc_from_train_py`, `auc_eval_runner_measured`,
   `eval_auc_from_train_py`; sometimes as a string; Chicago food's is a suite median that must not
   be shown as a single model.
3. **Site destination missing** for seven releases with live pages. The publisher wrote a receipt
   but not `DESTINATIONS.json`.
4. **Two artifact identities** in one manifest: `artifact_version` (packaging hash) and
   `qualification.artifact_version` (gate digest) disagreed.
5. **HF card without `configs`** on one release, so `load_dataset` would not produce the splits the
   manifest promises.
6. **Gate crash** on a duplicate CSV header (`ValueError` from the leakage scorer) instead of a
   named check failure. Fixed; keep the named failure.

## Target

1. `factory/release_schema.py` — the single definition of a release record:

   ```python
   @dataclass(frozen=True)
   class Split:
       rows: int
       positives: int | None
       # target window, optional
   @dataclass(frozen=True)
   class Baseline:
       eval_auc: float
       scope: str | None        # "median of 40 configs" when not a single model
       references: dict[str, float]
   @dataclass(frozen=True)
   class Destination:
       kind: str                # github | huggingface | site
       locator: str             # repo, or url
       private: bool
       verified_at: str
   @dataclass(frozen=True)
   class Release:
       dataset: str
       artifact_id: str         # ONE id: the gate digest
       tag: str
       splits: dict[str, Split]
       baseline: Baseline | None
       destinations: dict[str, Destination]
       licences: dict
   ```

   `load_release(path) -> Release` normalises every legacy shape above and returns a typed object,
   or raises `ReleaseShapeError` naming the file and the field.

2. **Writers fail closed.** `release-manifest.py` refuses to emit a manifest whose canonical fields
   are missing — no `{}` defaults. Unknown is represented once, explicitly, and every consumer shows
   it the same way.

3. **Consumers stop reaching into raw dicts.** Dashboard, site model, Hub adapter and card renderer
   read `Release` objects.

4. **Conformance test in CI:** every `release/*/` must parse into a `Release`; every published
   release must have at least one verified destination and a baseline with an eval AUC or an
   explicit `baseline: null` plus a recorded reason.

## Acceptance criteria

- `python3 -m unittest discover -s tests` green, with the existing guards untouched: gate 1.4.0
  timing checks, release preemption, jurisdiction requirement, licence classes, timing counterfactual.
- The conformance test passes for all ten existing releases **without editing their published
  artifacts** — legacy shapes are normalised on read, not rewritten on disk.
- No consumer reads `manifest["splits"]`, `manifest["baseline"]` or `destinations[...]` directly;
  `grep` proves it.
- The dashboard renders rows, baseline AUC (with scope) and destination pills for every release,
  including the two that were blank.
- `scripts/release-manifest.py` exits non-zero on a release missing rows or baseline rather than
  writing a manifest with nulls.

## Constraints

- Do not weaken or bypass the qualification gate. The timing checks exist because a dataset shipped
  with a prediction instant that preceded its own features.
- Do not fabricate figures. If a field is unknown, the schema says unknown and every surface says so.
- Do not rewrite published artifacts to fit the schema; normalise on read.
- Keep the licence semantics: a class C source may not be published without a recorded operator risk
  acceptance; the manifest must state NOASSERTION rather than imply a grant.
- Documentation must stay truthful about limitations; the refactor must not tidy away caveats.
