# Real-runner adapter verification

This job verifies the chronological scorer against the unchanged baseline from the
existing harness. It is an integration check on a public-source derivative, not a
new benchmark, published data version, or historical-availability certification.
The original harness checkout remains read-only. The published final holdout is
never downloaded.

## Artifact and protocol

`workers/smoke_artifact.py` constructs three disjoint files on the worker:

- Train: original public train excluding its final six observed calendar months.
- Development: those final six observed months, visible to baseline training.
- Scored test: original public eval, byte-identical, visible only to the scorer.

Source metadata declarations are preserved and derivative counts/windows/events
are recomputed. Feature timing is assumed, vintage is current-snapshot, label
availability is unverified, and source selection is outcome-conditioned because
Austin construction requires a recorded response_time. No publication timestamps
are invented. The actual gate must pass and `--accept` must verify those exact
artifact hashes before any baseline execution.

The worker builds the original pinned Dockerfile and uses its locked Python
dependencies. A protocol fixture checks network refusal, input mounts, absence of
credentials/image data, and one committed prediction before the next row. The
unchanged real baseline then predicts the full derivative test chronologically.
A separate trusted reference run uses the same baseline/train/development inputs
and predicts that test as a frame. Every probability must agree within the
predeclared 1e-12 tolerance. This comparison reports no AUC claim.

## Prepare a source-only job

The assembler reads original harness files with `git show <commit>:<path>` and
factory files from committed Git objects. The checkout need only contain the
pinned commit; it is never switched or modified. Source paths and SHA256 hashes
are explicit, and both encoded and decoded payloads are bounded to 2 MiB. Only
small metadata assets are downloaded during live source verification.

Create a fresh job directory such as `.factory/job-sources/<job-id>/` containing a copy of
`ops/smoke/austin-adapter-smoke-001.job.json` named `job.json`, then run:

```sh
python3 scripts/assemble-smoke-job.py <fresh-job-dir>/job.json --harness <read-only-harness>
python3 -m factory worker plan <fresh-job-dir>/job.json
```

The assembler writes `pinned.json` beside the copied job and updates its pins.
That directory must contain only those two files. Never use `.factory/<job-id>/`
for source: the worker launcher reserves that path for runtime state. The worker's source bundle puts
it at `source/pinned.json`. Keys in `expected_sha256` are logical names; Austin's
actual release asset filenames are `train.csv`, `eval.csv`, `meta.json`, and
`quality.json`. Data downloads and full-artifact qualification occur only on the
worker. A tracked source-bundle receipt is reference evidence, not a launch input;
reassemble after source changes.

`factory/worker.py` validates this specific Austin smoke operation and binds the
original harness, adapter, gate and artifact builder pins. `workers/executor.py`
runs the host child under the existing deadline/disk supervisor. The daemon must
be empty on the dedicated VM before work begins; exact job-owned container IDs
are removed at normal closeout and after supervisor termination. No Docker socket
or credentials are mounted into prediction containers. Fresh directories refuse
reuse rather than delete prior evidence.

## Launch, collect, and close

Scout is the sole coordinator of the worker ledger. Review the computed allowance
reservation (the template does not override pricing). Without `release: true`,
the existing construction-reserve deduction still applies to this job; the
reviewed EUR 0.32 plan fits that stricter cap. Then use the existing
worker launch/status/collect/cleanup commands from `docs/OPERATIONS.md`. The job
caps runtime/lifetime at 120/180 minutes, disk at 30,000 MiB, individual reports at
256 KiB, and collected output at 1 MiB. No bulk derivative or vectors are uploaded;
compact reports retain full hashes, provenance, qualification acceptance,
protocol checks and vector agreement. Confirm provider-side worker destruction.

If the trusted image build fails, `smoke-build-diagnostic.log` retains at most
32 KiB from each output stream, mode 0600, on the worker only. It is outside the
uploaded output directory; the compact receipt records its size and hash. Retrieve
only a bounded, credential-checked excerpt before destroying the failed worker.
Candidate inference output is never opted into this diagnostic log.

Software fixtures verify actual builder → qualify → accept behavior, and that
mutation after qualification is refused. They are explicitly software tests,
not substitute acceptance datasets. Passing tests alone does not close the real
worker verification requirement in issue #17.
