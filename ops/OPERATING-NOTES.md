# Operating notes

Written 2026-10-22 from the live coordinator. Each answer is a procedure I actually run, with the
files and commands that carry it, and bounded evidence rather than logs.

## 1. A successful candidate, end to end

1. **Discovery** writes `candidates/<id>/record.json` the moment the verdict is decided — `go`,
   `park` or `reject` — plus `jurisdiction`, `licence_class` (A/B/C/D), `prediction_question`,
   `prediction_time`, `target_definition` and `license_evidence`. A C or D licence ends it there.
2. **Construction** writes `candidates/<id>/source/build.py` with a `--source-dir` path for cached
   inputs and an `--out` extract, then assembles a job bundle:
   `python3 scripts/assemble-job.py <id>` → `jobs/<id>-001.json` (never launch from a candidate
   directory; the bundle must carry the builder).
3. **Worker run** produces `public/` + `private/` splits, `meta.json`, `quality.json`,
   `summary.json`, and the gate report. The gate is `skills/dataset-qualification/scripts/
   qualify_dataset.py <extract> --report qualification.json`; a pass is the only thing that lets
   bytes be called an artifact (identity = the gate digest).
4. **Baseline** runs the harness's own `train.py` + `validate.sh` unmodified on public splits only;
   `CONTRACT OK` and two identical AUC paths are required before any number is quoted.
5. **Packaging**: `candidates/<id>/{release.json,license.json}`, `baseline/{expected_artifact.json,
   baseline_result.json}`, then `python3 scripts/release-manifest.py <id>` and
   `python3 scripts/check-package.py release/<id>`.
6. **Publication**: stage private, verify digests from the destination's own API, then flip; the site
   is published by `scripts/site-publish.py prepare|publish` with an approved plan hash.
7. **Verify anonymously** — no token — and record it in `DESTINATIONS.json`; a 200/404 check is the
   only proof that counts.

## 2. An interrupted session, and how I recovered

Two shapes, both from 2026-10-22:

- **Killed for memory.** The PriceCatcher builder accumulated ~7.7 M row dicts on a 1.9 GiB host.
  Nothing was written; `ps` showed 963 MB RSS and 4 % CPU with swap at 96 %. Recovery was *not* a
  re-run: I read `dmesg`-equivalent evidence (RSS, swap), rewrote the build to stream each week to
  CSV, and re-ran from the same cached inputs. The first run left no partial artifact because the
  writer never opened a file before the emit stage.
- **Session died before committing.** The research session shut down between writing `record.json`,
  `STATE.md` and `DESTINATIONS.json` and committing them. Recovery is: read what is on disk, confirm
  it matches the provider's own records (job result, release assets, digests), then commit *that*
  state — never re-run the work. The watcher did exactly this twice today.

The rule: **an interrupted job is resumed from its records, not repeated.** Re-running is only
correct when the artifact was never produced.

## 3. When records disagree, which one wins

Authority order, highest first:

1. **The provider's own inventory** (Hetzner API; GitHub/HF APIs) — servers, assets, tags.
2. **The job record and its result release** — what ran, exit code, artifact digest.
3. **The gate report** — the artifact identity and whether it passed.
4. **`DESTINATIONS.json`** — what was verified, and when.
5. **`record.json`** — workflow state.
6. **`STATE.md`** — narrative, useful for *why*, never for *what is true now*.

Worked examples: a launch notice claimed a worker was up while the inventory said `deleted` — the
inventory won and the candidate was rebuilt. `STATE.md` said five commits were unpushed because a
tracking ref was stale — `git rev-parse` against the remote won. A record said `packaged` while the
audit was failing — the gate report and the audit won, and the status was pulled back.

## 4. Three chores I repeat most

1. **Re-verifying digests after any documentation change.** Any byte change invalidates the artifact
   identity, so the sequence is: regenerate manifest → `check-package` → re-upload docs → re-verify
   from the destination. It happens on nearly every release, usually twice.
2. **Rewriting the five release documents per dataset** (README, DATA_DICTIONARY, VERIFICATION,
   REPRODUCE, RELEASE_NOTES) with the same facts in five voices. This is where most of the stale-number
   defects came from.
3. **Reconciling shapes** — a manifest, a quality file, a summary, a card and a dashboard each
   wanting rows/AUC/destinations in a different form. This is the chore the refactor brief targets.

## 5. What can overlap and edit the same state

| Pair | Shared state | Protection |
| --- | --- | --- |
| discovery tick ↔ advancement tick | `.factory/research-session.lock`, `candidates/`, `STATE.md` | lock file; schedules offset (00/04/… vs 02/06/…) |
| worker-watch agent ↔ research session | `STATE.md`, `record.json`, job close-outs | watcher refuses to write while a session is live |
| dashboard cron ↔ manual publish | `dataset-factory-dashboard` repo, Pages | last-writer-wins; verify catches stale pages |
| site publisher ↔ dataset repo | `MANIFEST.json`, tags | publisher pins the tag; a stale tag blocks it (seen twice) |
| refactor branch ↔ `main` | nothing, by design | separate branch and worktree |

The real hazard is not two agents editing a file — it is **two agents closing out the same job**.
That is why every job has a `handled` marker and the watcher checks it first.

## 6. Rules that obstruct valid work

- **90-minute session envelope.** It was raised from 40 minutes precisely because three ticks died
  mid-research with no report. It still truncates a long construction; the wrap-up rule exists
  because of it.
- **Approval denial in cron.** `cron_mode: deny` is correct — no human is there — but it means a
  scheduled session cannot take an action the smart-approval layer flags, and it must plan around
  that rather than discover it at the wrong moment.
- **One worker at a time.** Deliberate (cost and race safety), but it serialises builds: a 40-minute
  job blocks the next candidate entirely.
- **Licence class C is a drop, not a queue.** This closes real datasets (Melbourne) but the
  arithmetic was compelling: 18 of 31 parked candidates died on licence *after* probing.
- **External-dir skills are read-only to `skill_manage`.** Correct for reviewability, annoying
  mid-task: the edit must be a repo file change and a commit.
- **Memory caps** (2,200 / 1,375 chars) force consolidation; useful facts get dropped when a bigger
  one arrives.

## 7. Status vocabulary, and what proves each

| Status | Means | Evidence required |
| --- | --- | --- |
| `qualified` | the artifact passed gate 1.4.0 on its exact bytes | `qualification.json` with `ok: true`, artifact digest, zero failed checks |
| `packaged` | a complete release exists and is staged | `release/<id>/` with manifest + package check OK; both destinations staged and digest-verified; `awaiting_operator: true` |
| `published` | public and verifiable without a credential | anonymous 200 on repo/release/HF/site; `DESTINATIONS.json` with `verified_at`; `MANIFEST.visibility: public` |
| `dropped` | closed, with a reason a future reader can act on | `rejection_reason` naming the specific blocker (licence clause, dominance by persistence, volume), and what would reopen it |

Nothing is `published` on a success response. It is published when someone with no token can fetch
it and the digest matches.

## What I most want preserved

1. **The gate's timing checks** — `timing.features_available_at_instant` and
   `timing.selection_uses_only_available_data`. They exist because a dataset reached `packaged` with
   a prediction instant that preceded its own features, and another shipped a selection that used
   M+1.
2. **Anonymous verification as the standard of proof.** Every "published" claim in this repo is
   backed by a credential-free fetch.
3. **The rule that a declaration is not evidence** — in timing, in licences, and now in release
   shape.
4. **The shims outside Git.** They are small, load-bearing, and would be lost with the host.

## Hardening I recommend

- Vendor `/opt/data/scripts/` into the repo (`ops/shims/`) and have the scheduler run the vendored
  copy, so the schedule is reconstructible from Git alone.
- Extend `scout-snapshot.py` to export **scheduler rows** (schedule, kind, delivery, toolsets,
  workdir) — never prompts containing identifiers — so a host loss does not lose the cadence.
- Make `check-package` refuse a manifest whose `splits` is empty; the ABS release proved an empty
  map passes every current check.
- Add a conformance test over `release/*/` (the refactor brief's item 4) so shape drift fails CI
  rather than surfacing as a blank dashboard cell.
- Treat the dashboard cron's non-zero exit as a first-class alert with the page name, instead of a
  bare `verified=False`.
