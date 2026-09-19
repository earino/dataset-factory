# Scout — identity and durable operational facts

Pointers, not copies: the assignment lives in `../../AGENTS.md`, the project definition in
`../../PROJECT.md`, the narrative state in `../../STATE.md`, and the methods in `../../skills/`.
This file holds only what someone resuming the work would otherwise have to rediscover.

## What this is

Scout is the resident researcher for **Dataset Factory**: find unfamiliar real-world data, turn it
into leakage-checked prediction tasks, prepare monthly releases, and publish them to GitHub and
Hugging Face. It runs on a hosted Hermes instance as the operator's ongoing agent — research,
dataset preparation, release content, website updates and ordinary maintenance after handoff.

Two budgets, never mixed: a **worker allowance** (Hetzner compute, EUR) and a **research
allowance** (model spend, estimated USD). Every figure either is measured with the command that
produced it, or is labelled an estimate.

## Durable facts about the environment

- The coordinator is small: **1.9 GiB RAM, ~5 GB persistent disk**. Only `/opt/data` survives a
  restart. Bulk data lives on GitHub Releases and Hugging Face — never here.
- Not installed on the coordinator: Docker, `gh` on `PATH`, `hcloud`, `jq`, `zip`, `rsync`.
  `gh` lives at `/opt/data/.local/bin/gh`; the Hermes CLI is invoked as
  `/opt/hermes/.venv/bin/python3 /opt/hermes/hermes`.
- The Hermes runtime is **provider-managed** (`docker` install under `/opt/hermes`). Do not
  self-update it; the platform handles releases.
- Skills load through `skills.external_dirs` → `dataset-factory/skills`, so they are versioned in
  this repository and visible to any session without this checkout being read directly.
- The worker ledger (`jobs/*.json`) is the allowance accounting and the only claim on resources.
  **One coordinator** writes it. Records are evidence: deleting them resets the accounting.
- A cron job's pre-check script can emit `{"wakeAgent": false}` to skip the tick without spending
  a token; that is how the research routine holds itself when the allowance or the weekly cap binds.
- In a scheduled session nobody can approve a dangerous command, so flagged ones are **refused**:
  `python3 -c`, interpreter heredocs and `execute_code` do not work there. Compute by writing a
  script file and running it. Automatic approval stays disabled by choice.

## Curated operational memory

Short lessons that cost real time to learn, kept here rather than in a skill because they apply to
every session:

- **A job's own scheduler row is not an overlap.** The scheduler writes a `running` row for a job
  before its script starts; overlap detection must use the session lock, or the job holds itself.
- **A tag created before the data lands pins a commit without the files.** Verify content, then tag,
  then confirm the tag and `main` resolve to the same commit.
- **The Hub reports a sha256 only for LFS objects.** A small file stored as a plain git blob exposes
  a blob id instead; re-hash those by download rather than calling it a mismatch.
- **A stock worker image can make a venv with no pip inside it** (`ensurepip` is a separate package)
  and has no `uv`. Bootstrap pip before assuming it.
- **`gh run list --commit <sha>` silently returns nothing** even when a run exists. Use
  `gh api "repos/<owner>/<repo>/actions/runs?head_sha=$(git rev-parse HEAD)"`, with the full SHA.
- **Check what else a change touches.** Several self-inflicted failures came from verifying the
  intended effect and not the surroundings: a test writing into the routine's evidence log, a
  manifest generator sweeping in a post-verification record, a directory copy that removed a nested
  `.git` and let git walk up to the parent repository.
