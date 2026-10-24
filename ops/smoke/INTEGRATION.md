# Adapter smoke: executor integration path (issue #17)

`workers/smoke_runner.py` is the host-side child for a new supervised executor host
operation, `smoke_adapter`, following the exact trust pattern of the existing
`transfer` / `hf_publish` children. This file records the precise integration; the
runner and job spec are on `remediation/dataset-review-17` for review.

## Executor hook (two additions, both in Codex-owned files)

`workers/executor.py` `host_child()` gains one branch:

```python
        elif operation == "smoke_adapter" and job.get("smoke_adapter"):
            smoke_run(base, job, report)          # thin wrapper: runpy the bundle's
            report["status"] = "succeeded"        # workers/smoke_runner.py main()
```

and `execute()` routes the job kind before the container path, beside the existing
host operations:

```python
    if job.get("transfer") or job.get("hf_publish") or job.get("smoke_adapter"):
        operation = ("transfer" if job.get("transfer")
                     else "hf_publish" if job.get("hf_publish")
                     else "smoke_adapter")
```

`factory/worker.py` treats the job as non-container (`runs_container = not (...
or job.get("smoke_adapter"))`) exactly like transfer/hf_publish: no image/command
required, no Docker socket ever enters a job container. The supervised-host
mechanism (`supervise_host`) already enforces the disk/deadline monitors and the
fresh-receipt directory; the smoke child inherits all of it unchanged.

## Bundle layout (assembled by the existing `scripts/assemble-job.py` flow)

`job.json` carries `smoke.bundle_files` mapping repository paths to bundle paths:

- `workers/smoke_runner.py` (the child; dispatched by the hook above)
- `scripts/install-prediction-adapter.py` + `adapters/score_holdout.py` (PR #18)
- `gate/qualify_dataset.py` (gate 1.5 from the runner bundle)
- `smoke/derivative-descriptor.json` (the reviewed research descriptor:
  retrospective_research, assumed timing, explicitly not a historical claim)
- `runner/train.py`, `runner/task.json` (the Austin baseline's frozen runner files)

Everything the child reads comes from `/opt/scout/source` (the uploaded bundle) or
fetches it verifies first. No credential is used: Austin's release is public and
the harness repo is public; `credentials.json` is never opened by the smoke child.

## What the child does (see smoke_runner.py for the authoritative steps)

1. Clone the harness at the pinned commit; preserve the original scorer hash.
2. Build the pinned image on the worker host; record the digest.
3. Fetch public train/eval/meta/quality; verify digests; never fetch the holdout.
4. Stream-split the derivative (train-minus-tail / dev-tail / test=original eval
   bytes), O(1) memory, distinct hashes recorded.
5. Gate 1.5 + `--accept` over the three derivative files.
6. Host scoring venv (pandas/scikit-learn/numpy resolved from the harness lock and
   recorded); adapter install with receipt cross-check.
7. Candidate stream run: locked-down container, one row per committed response,
   dev file mounted only via `FACTORY_DEV_EVAL`, scored file parent-side only,
   `FACTORY_PREDICTIONS_OUTPUT` parent-only.
8. Reference run: TRUSTED container, ordinary full-frame access to the test file.
9. Element-wise vector agreement (no AUC reported).
10. Negative probes: scored file absent in-container, network refused, whitelist
    exactly the four files.

## Launch and reconcile (existing commands, unchanged)

```
sh scripts/scout-factory worker plan ops/smoke/austin-adapter-smoke-001.job.json
sh scripts/scout-factory worker run  <job id from plan>
sh scripts/scout-factory worker status/collect <job id>
```

Bounded retries on collection; normal watchdog/cleanup ownership; provider
read-back on destroy. Budget: reservation EUR 0.06, cx32, 150/180-minute caps.

## Deliberately not done here

- No edits to `workers/executor.py` or `factory/worker.py` (Codex-owned; the two
  hook lines above are the proposed diff for review).
- No generic root hook, no Docker socket exposure to any job container, no
  schedule or budget changes, no new construction.
- The exact gate CLI invocation is the runner bundle's documented contract; if
  1.5's accept flow differs, the call site is one line to adjust at review.
