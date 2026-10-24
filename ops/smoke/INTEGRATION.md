# Adapter smoke: integration contract (issue #17)

Status: **assembly and artifact construction only — no launch.** The runtime
(smoke runner, executor dispatch, worker bundle wiring, container/stream probes)
is owned and integrated separately; this document covers the artifact half.

## Ownership

| Half | Owner | Files |
| --- | --- | --- |
| Artifact + assembly + job/docs | Scout | `workers/smoke_artifact.py`, `scripts/assemble-smoke-job.py`, `tests/test_smoke_artifact.py`, `ops/smoke/*` |
| Runtime integration | Codex | `workers/smoke_runner.py`, `workers/executor.py`, `factory/worker.py`, adapter protocol/cleanup, their tests |

The assembler's `bundle_files` above intentionally lists only the artifact half's
sources. The runtime owner adds `workers/smoke_runner.py` (`repo:` source) and
worker provisioning fields to the job when integrating; the assembler refuses a
listed source that does not exist, so a wrong path fails at assembly, not on the
worker.

## The derivative artifact

`workers/smoke_artifact.py::build_derivative(input_dir, output_dir, smoke)`
constructs, from a directory holding the published release's **public** assets
under their real release-asset names (`train.csv`, `eval.csv`, `meta.json`,
`quality.json`):

- `public/train.csv` — train' = public train minus its final `dev_months`
  calendar months (months are calendar-sorted, never encounter-ordered);
- `public/eval.csv` — dev = that tail; the only eval-role rows the candidate
  sees;
- `private/holdout.csv` — the published eval bytes, **unchanged**; the
  scorer-owned test, never candidate-visible.

The published private holdout is never fetched. The derivative `meta.json` and
`quality.json` preserve every truthful source declaration verbatim and re-measure
everything the gate recomputes: rows, positives, rates, split windows, clustered
positive events, duplicate identifiers, cross-split identifier sharing. The gate
1.5 timing and evaluation-contract blocks are derived honestly:

- `timing`: administrative event-time instant (kind
  `administrative_event`, 0-day lag), `observations: []` — no publication dates
  are invented; `latest_period_used` is the last month actually present in the
  derivative rows.
- `evaluation_contract`: `use=retrospective_research`,
  `access=chronological` (the dev split is a later period than train'),
  per-column `feature_evidence` with `status=assumed` for every shipped
  non-target column (administrative event-time availability assumed from the
  release's dispatch definition — never `verified` without as-of evidence),
  `vintage=current_snapshot`, `selection=prediction_time`,
  `cross_row_audit` with rationale and auxiliary-file review, and
  `training_label_timing=unverified` with no availability ledger.
- The release's own `id_columns` are used (`incident_number` for Austin); no
  synthetic identifiers are declared.

If the source release predates a declaration the gate requires, the builder
refuses and names the missing key. If the re-cut produces an artifact the gate
would refuse (overlapping windows, cross-split identifiers), the finding is
measured, returned in the metadata and left to the gate — never spoofed.

## The source bundle

`scripts/assemble-smoke-job.py <job.json>` assembles the source-only bundle from
the read-only pinned harness:

- every `bundle_files` entry becomes one entry of the **`source/pinned.json`
  payload** the runtime places inside the worker source bundle. The payload
  carries exactly the runtime schema:

  ```json
  {"harness_commit": "<40hex>",
   "files": {"image/Dockerfile": {"base64": "...", "sha256": "..."}, ...}}
  ```

  The coordinator-side file is `ops/smoke/<id>.source-bundle.json`; the runtime
  copies it to `source/pinned.json` verbatim.
- harness sources are read via `git show <commit>:<path>` — provenance binds to
  the pinned commit `58b434fee9b53eab953b6a3d84baf5cbeb01bc6e`, not the
  worktree;
- the runtime materializes from the payload: the `image/` context (original
  `Dockerfile`, `.dockerignore`, `uv.lock`, `pyproject.toml`, `bench.yaml`, all
  `bench/*.py`, full `task_template/`), `adapter/score_holdout.py`,
  `gate/qualify_dataset.py` and `workers/smoke_artifact.py`;
- forbidden paths (`.git`, `data`, `runs`, `results`, `auth`) and every `.csv`
  are refused, so no bulk row and no credential can enter the bundle;
- the job's `smoke.pinned_sources` is the exact relative-path→sha256 map of the
  payload, and `smoke.source_provenance` records each file's origin binding;
- the job's `expected_sha256` is keyed by the **real** GitHub release asset
  names, taken from the frozen `MANIFEST.json` `assets` block (`train.csv`,
  `eval.csv`, `meta.json`, `quality.json` for Austin — the old
  `public/train.csv`-style URLs do not exist as release assets);
- with `gh` present, live verification confirms each asset name and size, and
  re-downloads only the two small metadata assets to confirm digests; the CSVs
  are never fetched by the assembler.

Run it:

```
python3 scripts/assemble-smoke-job.py ops/smoke/austin-adapter-smoke-001.job.json
```

The run writes `ops/smoke/austin-adapter-smoke-001.source-bundle.json`, fills
`smoke.pinned_sources`, `smoke.source_provenance` and `smoke.source_bundle` in
the job, and prints the verification proof.

## Runtime contract

`build_derivative(input_dir, derivative_dir, smoke)`:

- `input_dir` holds the fetched public assets under their real release-asset
  names: `train.csv`, `eval.csv`, `meta.json`, `quality.json`;
- `derivative_dir` already exists, containing only the `.smoke-owned` marker;
  the builder keeps the marker and refuses any other pre-existing content;
- output is exactly `meta.json`, `quality.json`, `public/train.csv`,
  `public/eval.csv`, `private/holdout.csv`;
- the gate report's success key is `ok` (top-level boolean in the report JSON).

## Gate proof (required before any launch)

The derivative must pass the real gate, two-phase, on the worker:

```
python3 gate/qualify_dataset.py <derivative> --report <report.json>   # report.ok must be true
python3 gate/qualify_dataset.py --accept <report.json> <derivative>   # must ACCEPT
```

`tests/test_smoke_artifact.py` proves this locally on a software fixture built
**through** `build_derivative`: the fixture passes qualification and acceptance,
and a mutated CSV after the report is refused by `--accept` (digest mismatch).
Selftest or `--help` invocations do not count as this proof.

## Job fields

- `candidate`, `dataset`, `note`, `smoke_adapter` — job identity; the smoke is
  host-side, so no container image is provisioned by the job itself.
- `location`, `server_type`, `cpus`, `memory_mb`, `timeout_minutes`,
  `lifetime_minutes`, `max_disk_mb`, `max_artifact_mb`, `max_report_bytes`,
  `reservation_eur` — worker provisioning, validated by `factory/worker.py`.
- `smoke.harness_commit` — the 40-hex pinned harness commit the bundle reads
  its harness sources from.
- `smoke.image_tag`, `smoke.release_tag` — the locally built image tag and the
  published release being smoked.
- `smoke.artifact_version` — the frozen manifest's artifact version, filled
  by the assembler programmatically.
- `smoke.time_column`, `target`, `positive_label`, `dev_months` — the re-cut
  parameters; `tolerance` bounds streamed-vs-reference vector agreement.
- `smoke.threads`, `smoke.score_timeout` — runtime knobs for the runner.
- `smoke.expected_sha256` — keyed by the LOGICAL names the runtime's fetch loop
  uses (`public/train.csv`, `public/eval.csv`, `meta.json`, `quality.json`);
  `smoke.asset_names` maps each logical name to its REAL GitHub release asset
  name (`train.csv`, `eval.csv` for Austin), `smoke.asset_bytes` carries the
  frozen sizes. All three are filled by the assembler from the manifest's
  `assets` block and verified live.
- `smoke.bundle_files` — bundle path → `harness:<path>`, `repo:<path>` or
  `repo:<path>@<ref>` (a resolved repository commit; the adapter is pinned to
  the runtime owner's `fix/worker-smoke` commit so the bundle carries the
  job-label-capable version).
- `smoke.pinned_sources`, `smoke.source_provenance`, `smoke.source_bundle` —
  filled by the assembler.

## What is deliberately absent

- No worker provisioning fields (`server_type`, timeouts, budget) — the runtime
  owner's integration adds them through `factory/worker.py` validation.
- No `smoke_runner.py` in `bundle_files` yet — added by the runtime owner.
- No launch: the smoke runs only after both halves are integrated and reviewed.
