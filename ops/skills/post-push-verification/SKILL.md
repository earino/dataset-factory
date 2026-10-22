---
name: post-push-verification
description: "Use when verifying a pushed change before reporting it."
version: 1.1.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ci, github-actions, verification, clean-checkout, testing, reporting]
    category: software-development
    related_skills: [github, ephemeral-worker-lifecycle, requesting-code-review]
---

# Post-push verification

## When to use

Any time a change is pushed to a repository with CI, and especially when that push is the last step
before reporting the work done. Also when a CI failure needs diagnosing, or when a suite is green
locally and red on the runner.

Pushing is not completing. The change is complete when its own CI has been read and is green, or
when the reason it cannot be read has been stated out loud.

## Before the push: gate on the status, and read the whole output

Two habits that make the rest of this procedure reachable. Both concern the run that pushes, which
is otherwise easy to treat as a formality.

- **Make the commit conditional on the suite's own exit status.** Capture it
  (`suite=$?; if [ "$suite" -ne 0 ]; then echo "NOT COMMITTING"; exit 1; fi`) rather than letting an
  `&&`-chain carry on into `git commit`. A chain that continues past a failing suite treats the run
  as output to skim instead of as a gate, and the red state reaches the remote, where discovering it
  costs another commit and another CI round trip. A gate that cannot stop the action it guards is
  decoration.
- **Never truncate the output of a check whose purpose is to report problems.** Piping a validator
  through `head -3` when it prints one line per subject shows a tidy run of passes and hides the
  failing subject - the check did its job and the display undid it. Let such a check print in full,
  or search its output for the failure markers instead of shortening it; a trimmed result and a clean
  result look identical, which is the whole danger.

## Procedure

1. **Read CI for that exact commit.** Resolve the runs by SHA rather than by eye:

   ```bash
   gh api "repos/$OWNER/$REPO/actions/runs?head_sha=$(git rev-parse HEAD)" \
     --jq '.workflow_runs[] | "\(.head_sha[0:8]) \(.status)/\(.conclusion) \(.html_url)"'
   ```

   A run for an earlier commit, or a green run elsewhere on the same branch, says nothing about
   what you just pushed. A documentation-only follow-up needs its own check.
2. **Confirm the steps, not just the job verdict.** A step can be `skipped` inside a `success` job,
   and a skipped step is the opposite of evidence:

   ```bash
   gh run view <RUN_ID> --json headSha,event,conclusion,jobs \
     --jq '{sha:.headSha,conclusion:.conclusion,steps:[.jobs[].steps[]|{name,conclusion}]}'
   ```
3. **Read the failure before changing anything.** `gh run view <RUN_ID> --log-failed` yields the
   failing steps only; search it for failure markers and test names rather than reading the whole
   log.
4. **Ask whether the failure is about the code or about the machine.** The runner has a clean
   checkout: no gitignored config, no host-specific paths, no local services, no secrets, no caches.
   A test that reads any of those is testing your machine. Reproduce it with the clean copy below.
5. **Fix, then verify the new commit** - back to step 1. Repeat until the pushed commit is green.
6. **Either way, run the local suite too.** A test that CI *skips* because it is gated on private
   state can still fail on your machine, so local green and CI green are different claims; when they
   disagree, neither result alone is the answer.
7. **Report honestly when CI cannot be read.** If the run is still pending, or is blocked by
   something outside the repository, say exactly that - "pushed, CI still pending" or "CI blocked by
   X" - rather than implying the change passed. **A `failure` whose steps never executed is a
   platform condition, not a test result.** Read the run's annotation: "the job was not started"
   naming a billing or spending-limit reason is an account-level block. Actions minutes are consumed
   by **repository visibility** - a private repository draws on the plan's included minutes and is
   then refused until the spending limit is raised or the billing cycle resets, while standard
   runners on a public repository are free - so one repository can be blocked while another runs the
   same workflow untouched. Keep the dependent claims gated and name the affected commits as
   unverified; do not reach for a workaround (self-hosted runner, `continue-on-error`) to turn the
   badge green. Substitute the part of CI that actually tests the code - a clean-checkout run of the
   suite plus whatever doctor or static check the workflow runs - and state that it lacks the
   independent runner.

## Verifying a deployed static site (GitHub Pages)

A Pages deploy is a **second** artifact built from the commit; CI green does not mean the site
serves it, and the push does not mean the page changed. Verify the public URL, anonymously, and
only after allowing for the build:

1. **Cache-bust every check.** `https://<owner>.github.io/<repo>/?ts=$(date +%s)` — the CDN serves
the previous build with a 200 for a minute or two, and a stale 404 page can also come back with 200.
   A plain fetch right after the push reports "published, but old content" and looks like a failure.
2. **Look for a marker unique to this build**, not a marker that is always present: the snapshot
timestamp embedded in the page, or a hash of the artifact. Asserting on a static string proves only
   that some version is live.
3. **Poll with a bounded retry** (e.g. 6 attempts × 20 s) rather than failing on the first miss;
   treat "page live but marker is the previous build" as a failure, because it is.
4. **Make the publisher do this and exit non-zero.** If the verification lives only in the chat, a
   broken deploy reports success forever. When a scheduled job publishes, its script should fail the
   run on a missing marker so the scheduler records the truth.
5. **Check the whole surface**, not just `index.html`: the stylesheet, secondary pages and any
   `robots.txt` each deploy separately in the reader's cache.

## Reproducing a runner-only failure locally

Copy the tree the way the runner sees it and run the suite there:

```bash
mkdir -p /tmp/clean && tar --exclude='./.git' --exclude='./config/local.json' \
  --exclude='./.env' --exclude='__pycache__' --exclude='*.pyc' -cf - . | (cd /tmp/clean && tar xf -)
cd /tmp/clean && python3 -m unittest discover -s tests
```

Run the copy with bytecode writing **enabled** and under a non-local timezone as well: a suite that
passes only because the environment sets `PYTHONDONTWRITEBYTECODE=1`, or because the host is in UTC,
carries the same defect and will not show it until the runner disagrees. Adjust the exclusions and
the command to the project, but keep the principle: the copy must lack everything private.

## Fixing environment-coupled tests

- Commit a fixture with the same shape as the private file - a policy, a config, a credential-free
  sample - and point the test at it explicitly.
- Never make an assertion conditional on a private file existing. That is a test that only ever runs
  for you, and its absence on the runner looks like a pass rather than a skip.
- Put a rule *before* the environment check rather than inside it: refuse a protected path before
  asking whether it exists, so the guard does not depend on what the host happens to have.
- Keep one optional comparison test against the real private file, skipped when it is absent, so the
  committed fixture cannot silently drift from production values.
- When the committed fixture is deliberately **narrower** than the private file - one allowed value
  where production allows three - compare the intersection, not the whole mapping: the ordered lists
  that must match exactly, and the fixture's own keys against their production counterparts.
  Demanding equality across the entire mapping fails on the machine that has the private file while
  CI skips it, which turns the drift check itself into a runner-only defect.

## Pitfalls

- **Trusting a flag because it accepted your input.** `gh run list --commit <sha>` takes the flag
  and returns an empty list even when a run exists for that commit, which reads as "CI never
  started" about a commit that is already green. Before concluding that nothing ran, confirm the
  query returns a run you already know exists. The same applies to the `head_sha` filter in step 1:
  it matches the **full** SHA, so an abbreviation pasted from a commit list returns nothing and looks
  exactly like a commit with no runs. Pass `$(git rev-parse HEAD)`, never a shortened form - and when
  a query returns empty, suspect the query before concluding anything about the world.
- **Reading an empty response as evidence of absence.** The general form of the above: an empty
  filtered list usually means the filter is wrong, not that the world is empty. Prove the query on a
  known-positive case first.
- **Declaring a fix complete from the push that failed.** The next push is a new commit with its own
  run; the previous result cannot carry over.
- **Reporting a green run you did not look at.** Summarising a conclusion from memory or from a
  status badge is not reading the run.
- **Assuming the local suite is the stronger signal.** It is a different signal: CI lacks your
  private state, and your machine lacks CI's environment. Both are read, or the claim is partial.
- **Treating a rejected push as a local problem.** `! [rejected] ... (fetch first)` means the remote
  moved: another writer - a colleague, a delegated agent, a scheduled job - pushed while you worked.
  Fetch and **read the incoming commits before rebasing or merging them into your work**, then
  confirm your own commits are still present in the log afterwards; a rebase that drops or reorders
  your work is silent, and where the diff overlaps the same file it is a decision to review, not to
  resolve blindly. Never force-push over another writer's commits to save the review.
- **Calling a test-count difference a discrepancy before deriving it.** A reported count ("240 tests
  pass") that disagrees with your run is usually a tree difference, not a defect: count per file
  (`python3 -m unittest discover -s tests -p "test_x.py"` for each) and see whether the gap equals a
  known diff - tests that arrived with a rebase, tests you added, or tests the other environment
  skipped. Account for the difference before reporting it as a problem, and say which run carried
  which.
- **Reading a program's exit status through a pipe.** `cmd | tail` reports the status of `tail`, so
  a failing command that you piped for tidiness looks like a success - a refusing check printed
  `exit=0` and only its output revealed otherwise. Redirect to a file and read the status there
  (`cmd > out.txt 2>&1; echo $?`), or set `set -o pipefail` first. Never quote an exit code measured
  on the far side of a pipe, and when a status and its output disagree, believe the output and
  re-measure before reporting either.
- **Reading a zero-step failure as a code failure.** A run that concludes `failure` with no steps
  executed never reached the code; its annotation names the real cause (billing, spending limit, a
  disabled workflow). Diagnosing tests from it burns a round trip, and reporting it as "CI red"
  misstates the repository's health in the direction that makes working code look broken.
- **Repeating a cited run ID, count or SHA you never fetched.** When another agent's or colleague's
  handoff cites CI runs and test counts as evidence, those are claims about objects that exist: fetch
  each run and confirm it is at the **full** SHA it claims and actually succeeded before repeating it
  as verified. A quoted run ID is hearsay until you have read it, and a full SHA plus a quoted count
  is exactly the shape of evidence that is easy to accept and cheap to check. The same applies in the
  other direction, to identifiers **you** write down: a commit SHA, run id or release id copied by
  hand into a record, a pin or a report can carry a corrupted tail that looks entirely plausible and
  resolves to nothing - fetch the value from the API at the moment you record it, and when a
  recorded id is later suspected, compare it against the live value rather than trusting either.
- **Reading a path-filtered workflow's silence as a missing run.** A workflow triggered on changed
  paths has no run for a commit that touches nothing it watches, which is correct behaviour and at
  the API looks identical to "CI never started". Read the workflow's `on:` filter and check that it
  names the directory the commit touched before reporting anything about coverage; when it does not,
  say which workflows were expected to run and report the rest as unaffected rather than as
  unverified.
