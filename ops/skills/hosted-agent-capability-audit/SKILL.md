---
name: hosted-agent-capability-audit
description: "Use when auditing a hosted agent or granting it access."
version: 1.0.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [audit, inventory, capabilities, credentials, secrets, provisioning, hosted, environment, github, tokens]
    category: devops
    related_skills: [hermes-agent]
---

# Hosted agent capability audit

## When to use

Any task that hinges on **what this instance can actually do** before you design around it:

- "Inventory what your instance can do before we build tooling."
- "Can we use X here?" / "What's missing for Y?"
- "Give me access to Z" (GitHub, a cloud provider, an API).

These run on a platform-managed container you do not own: persistent disk is a single path, the OS root filesystem resets, there is no sudo, no public IP, and outbound network is the main channel. Audit facts, not the product.

## The three-state distinction — always report which one you mean

| State | Means | Not yet proven |
|---|---|---|
| **Catalog** | A tool name exists (deferred catalog, plugin tree, docs page) | that it is present or connected |
| **Installed** | The binary/plugin is on disk | that it is usable |
| **Usable** | Connected (daemon up, credential present, gateway route served) AND you exercised it | — |

Never collapse these, and never upgrade one to the next on your own authority. A capability named in a **skill is instructions, not a capability** — a skill can document a CLI workflow end to end while the CLI and its credential are both absent. A missing CLI also does not mean the capability is missing: check for another route (a tool, the provider's REST API, the tool gateway) before declaring a gap.

## Procedure (read-only; batch aggressively)

Batch independent probes into single shell calls. Read env **names only** — `env | cut -d= -f1` — never values, and never dump config files wholesale.

1. **Version + install method.** `hermes --version` (the binary may not be on `PATH`; resolve it, e.g. `/opt/hermes/bin/hermes`), plus `grep -m5 -iE "^(name|version)" /opt/hermes/pyproject.toml`. The install method decides whether self-update is even possible — on a platform-managed image it is not, so say so instead of attempting it.
2. **Binaries.** Loop `command -v` over the candidate list and report every `MISSING` explicitly rather than only the hits.
3. **Resources.** `df -h` on the persistent path *and* `/`, `free -h`, `nproc`. **Report the actual numbers and flag divergence from the stated spec** — provisioned specs and live reality often differ, and an agent that quietly accepts the stated figure will plan work that cannot fit.
4. **Terminal backend and persistence.** `TERMINAL_ENV` (local vs containerized), `TERMINAL_PERSISTENT_SHELL`, `HERMES_WRITE_SAFE_ROOT`, `TERMINAL_TIMEOUT`. `TERMINAL_ENV=local` means the shell is unisolated on the instance — relevant to every disk/memory claim you make.
5. **Deferred tool catalog.** `tool_search` per capability, then `tool_describe` the names it returns. A no-lexical-match result is **not** absence — read the `available_sources` list it hands back before concluding anything.
6. **Managed connectors.** `manage_connections` `action=status`. A gateway error here means connector tools are not served on this instance; that is a platform-side setting, not something you repair.
7. **MCP.** Look for a client config file. A bundled `mcp_serve.py` means the instance can *serve* MCP, not *consume* external servers.
8. **Services: probe the daemon, not the binary.** `docker info`, not `command -v docker`. A present CLI with a dead daemon is not a usable capability.
9. **Credentials.** Check `~/.ssh`, global git config, and the `.env` **key names**. Missing credentials are a "needs user action" item to list — not a defect to report as broken.
10. **Network reachability.** Cheap read-only probes per host: `curl -s -o /dev/null -w "%{http_code}" --max-time 10 <url>`. Interpret carefully: any HTTP status means DNS+TLS+egress succeeded; `401/403` means reachable-but-unauthenticated (the capability is one credential away); a `404` on a CDN root is reachability **success**, not failure. Also test raw ports when a protocol matters (`bash -c 'cat < /dev/null > /dev/tcp/host/22'`).
11. **Scheduling.** Read the cron provider config and the scheduler heartbeat timestamp before claiming scheduling works, and report the delivery constraint that applies to the current surface.

## Report shape

This user wants an inventory of **their environment**, not a description of the product:

- A compact table: **capability | exact tool/plugin/skill | availability | evidence | limitations**. Evidence is a command or an observed result — never an assertion.
- Then, in this order: **what access/configuration you need from the user**; **which existing capabilities to reuse**; **what project-specific tooling is still necessary**.
- **Label uncertain findings explicitly** as uncertain.
- No credential value ever appears in the report; env output is names-only.
- Reuse existing monitors/skills as patterns rather than proposing new tooling for work a `no_agent` script or an existing skill already covers.

## Credential delivery — standing rules

1. **Never ask for, accept, or repeat a secret in chat. Never type one into any field.** Route the user to a delivery channel and let them enter it there.
2. Channel that works on a hosted instance: the web dashboard's env page — `$HERMES_DASHBOARD_PUBLIC_URL` + `/env`, gated by the platform's own login. It writes `KEY=VALUE` into `$HERMES_HOME/.env` with no key allowlist, so an arbitrary provider variable name is accepted. Mechanics and caveats: `references/credential-delivery.md`.
3. **Choose the variable name from what the consumer already reads**, not one you invent — grep the Hermes source for the provider's resolution order first. For GitHub the name is `GITHUB_TOKEN`; scope maths and alternatives are in `references/github-token-scopes.md`.
4. **Consume a delivered secret without printing it**: resolve it inside the same command that uses it (parse the `.env`, or read the loader's dict) and pass it as an argument or header. Never `echo` it, never put it in a URL you might log.
5. **Verify immediately after delivery** with a real end-to-end exercise of the intended path (clone, commit, push, and for release workflows *create a test release with an asset*) — the asset path is the one that fails late and is worth proving before it is load-bearing.

## Granting access when the consumer is not installed

Delivering a credential is only half of granting access: the thing that consumes it may not exist on the instance yet, and there is no root to install it with.

1. **Install into the persistent path from a verified release artifact.** Fetch the vendor's release tarball *and* its published checksums file, compare `sha256sum` before extracting, install under the persistent path. Never install an unverified binary and never pipe a download straight into an interpreter. Recipe: `references/no-root-cli-install.md`.
2. **Make it resolvable.** Append the install directory to `PATH` in both `~/.profile` and `~/.bashrc` on the persistent home — terminal-tool shells do source these — then confirm with `command -v` in a **fresh** call, not the one that wrote the file.
3. **Authenticate the CLI from the credential the user already delivered**, with the value never touching stdout or chat: parse the variable out of `.env` inside the same command that feeds the CLI's own login (a `--with-token` stdin form). The CLI then keeps its own copy in `~/.config/<tool>/` at mode 0600.
4. **Collapse duplicate credential paths before declaring done.** The CLI store and `.env` now both hold the secret, so a rotation must update both; and once the CLI installs its own git helper (`gh auth setup-git` and friends), remove any hand-rolled helper added earlier — exactly one resolution path should be live, or a later auth failure is ambiguous and a rotation silently incomplete.
5. **Prove write access, then remove the evidence.** Exercise the intended write path against the real target and read the effect back — push a throwaway branch, confirm the ref with `ls-remote`, delete it, confirm the remote is back to baseline — rather than pushing to the default branch or leaving test commits behind. Expect side effects: a push can trigger CI, so keep test work on a throwaway ref and report the run it produced. When the load-bearing path is **release-asset upload**, exercise that instead: create a uniquely named **draft** release, upload a tiny file, read the asset back from the API and compare the server-reported size and `sha256:` digest against locally computed values, then delete the asset and the release and confirm both reads return 404 with no leftover tag. Delete only what the test created, and report a cleanup failure explicitly rather than glossing it.
6. **Verify the credential through its own file, with the variable scrubbed from the test environment.** When the consumer will read a file (a `_FILE` path, a token file), run the test as `env -u VAR -u VAR_FILE …` and have the script assert the variable is absent before reading the file — otherwise a secret that happens to be visible in the process environment lets the test pass without ever exercising the path the real consumer uses, and the first genuine failure lands in production.
7. **Deliver paths, not values, when the consumer is invoked from cron.** A wrapper the consumer is always called through, exporting `<PROVIDER>_TOKEN_FILE` defaults, works in non-interactive shells with no startup file and no restart; explicit overrides still win. The tool behind it should report each credential as present/absent/unreadable with no contents shown, and exit non-zero when one is unusable.
8. **Prove a credential is *restricted*, not merely working.** For any token you asked to be narrow — a worker/staging credential kept separate from the coordinator's — probe a resource it must **not** reach and expect a 404, and enumerate what it can see to confirm the set matches the intent. A credential that authenticates successfully says nothing about its breadth, and an over-broad token silently defeats the isolation the whole design rests on. Recipes: `references/github-token-scopes.md`.

## Granting access to an external service the agent will drive

Different from installing a CLI: here the credential authorises changes on someone else's infrastructure, and the failure mode is money or lost work.

1. **Verify the provider token through its own file, scrubbed, with a read-only list call** — and report only the auth outcome and the resource count. Recipe: `references/cloud-provider-access.md`.
2. **Register the agent's SSH public key idempotently**: create when the name is free, reuse when the existing key matches, and **stop and report when the name is taken by a different key**. Verify by reading it back and comparing fingerprints computed locally in the provider's format, not by trusting the create response.
3. **Prove a key is fit for unattended use before registering it**: it must re-derive its public key with an empty passphrase and match the `.pub` blob.
4. **Wire the service's own scheduled job through stdin and confirm the job body ran**, reading job steps and step logs rather than the run conclusion. Recipe: `references/scheduled-external-jobs.md`.
5. **Distinguish plumbing from effect in the record.** A successful authenticated call that found nothing to act on verifies the wiring and the credential, not the mutation path. Write both halves down, and keep the untested half in the smoke-cycle plan.
6. **Treat scheduler-driven confirmation as pending until observed**, and bound the wait with a deadline and a cutoff timestamp rather than declaring success from the configured interval.

## Pitfalls

- **A run-level `completed/success` is not evidence a job executed.** A job gated by a variable concludes `skipped`, and a dispatch is accepted before anything runs. Read the job's steps and its own log output before claiming execution.
- **An empty result list is not a verified mutation path.** "Deleted 0 because there was nothing to delete" leaves ownership checks, per-resource cleanup and error handling untested — say so explicitly instead of letting a green run imply the feature works.
- **Never widen a credential's scope to fetch a diagnostic number.** When a billing/quota figure needs a scope the token lacks, report the gap; do not refresh or re-scope a working credential as a side effect of an inspection task, and do not modify a login the user depends on.
- **A skill is not an installed capability.** Do not mark something available because a bundled skill documents it. Check the CLI, the credential, and a live call — all three.
- **No lexical `tool_search` match is not absence of tools.** Read the returned `available_sources`; the catalog may hold tools whose names share no words with your query.
- **A binary present != a daemon running.** Probe the service (`docker info`, a health response) rather than trusting `command -v`.
- **A value written to `.env` reaches nobody's environment by itself.** A child process inherits the parent's `os.environ` snapshot from process start, so neither internal plumbing nor a plain shell command sees a value added mid-session; the `.env` cache is re-read only by code that calls the loader itself. Say which consumer you mean before promising an effect, and prefer handing the consumer an explicit file path over hoping it resolves the variable. **Do not predict which way it went on a given instance — probe it** (`env | grep -c '^VAR='`): the same host has shown one delivered variable absent from child shells and another present in them, depending on the delivery route.
- **Do not propose the browser credential vault for CLI or API auth.** It injects passwords server-side into browser form fields on their bound origin; it cannot supply a token to `git`, `curl`, or a CLI. Correct channel selection is in `references/credential-delivery.md`.
- **Don't report an unconfigured credential as a broken tool.** "Needs a token from you" and "this is unsupported" are different findings with different next actions.
- **Two credential helpers is one too many.** Once a CLI installs its own git credential helper, remove any helper you hand-rolled earlier; stacked helpers make an auth failure ambiguous and a rotation incomplete.
- **"It worked" is not "it is scoped."** A repo payload's `permissions` block reports the **authenticated user's** access to that repo, not the token's grant, and a fine-grained token's permission list is not enumerable through the API at all. Never cite that block as evidence of scope; prove scope by what the credential *cannot* reach.
- **Write long scripts to a file inside `HERMES_WRITE_SAFE_ROOT`, then execute the file.** Piping a multi-kilobyte heredoc into an interpreter through the terminal tool can hang until the call times out, and writes outside the safe root are refused outright. Two short calls — write, then run — beat one clever one.
- **A ceiling taken from the instance-type price alone understates the real hourly cost.** Providers bill some instance add-ons separately — a primary IPv4 is the usual one — so the ceiling must cover the sum of the gross hourly line items, compared the way the launch path compares it. Verify with the product's own ceiling check rather than re-doing the arithmetic, and state the headroom: a ceiling that passes with a rounding error to spare is a launch failure waiting for the next price change.
- **A per-job reservation is not a cap on the month.** Reservations bound which jobs you admit; a resource left running is not bounded by them at all and can bill more per month than the entire allowance. Compute the monthly gross and present the allowance as a conservative admission estimate, never as a spending guarantee.
- **A config value you were handed still needs proving.** Check it against the code's own bounds and demonstrate the reject branch too (a value just outside the range), rather than writing it into the file and reporting success.
- **An exported secret is written to disk, not just to the process environment.** The terminal backend snapshots the session environment into `$TMPDIR/hermes-snap-<id>.sh`, and on a hosted instance `TMPDIR` is the persistent scratch path - so a token exported into the shell, or inherited by it, sits in plaintext on durable disk and outlives the session that used it. Keep credentials in mode-0600 files read at the point of use (the `_FILE` convention), and treat any secret that was ever exported into a shell as written to disk. Decide rotation from whether the value could leave the box - transcripts sent to the model provider, a public surface, another tenant - not from the export alone: 0600 files on a single-tenant container behind a logless provider make rotation hygiene, not an emergency. Inventory and decision procedure: `references/secret-exposure-triage.md`.
- **Answering "where exactly did it leak" with assurance instead of an inventory.** Run the value against every carrier and report each as full-value, prefix-only, or at-rest copy - transcript database and its FTS tables, logs, cron output, shell env snapshots, `.env` and its backups, git objects, release assets, delivered messages, and the model-provider request payload. Redaction is not deletion: a SQL `UPDATE` leaves the old bytes in freelist pages and in the write-ahead log until a checkpoint and often a `VACUUM`, so state the residue you chose not to remove rather than reporting zero. Ground the conclusion in the provider's retention policy rather than in how alarming the finding feels, and when rotation is deferred, schedule a dated reminder instead of carrying it as a live worry.
- **Expanding a default on a secret prints it.** `${VAR:-fallback}` returns the **value** when the variable is set, so a presence check written that way dumps the secret into the transcript while looking like a guard. Test presence with `${VAR:+set}` or `[ -n "$VAR" ]`, and reach for `env -u VAR` when the point of the run is to exercise the file path instead.
- **A credential that can push a branch may still be refused a ref update.** Moving a tag or a ref is a separate grant from write access, so a rejected ref update is a scope signal, not a broken command: switch to the credential that holds it rather than widening the one that refused, and record which credential each direction uses.

## References

- `references/credential-delivery.md` — every channel a secret can take to reach a hosted instance (dashboard env page, `.env` load mechanics, browser vault, external secret managers, egress credential injection), with what each can and cannot authenticate.
- `references/github-token-scopes.md` — `GITHUB_TOKEN` resolution order, the exact fine-grained permissions for clone/push/releases/repo-creation, when a deploy key or device flow beats a PAT, and the three tests that prove a delivered token works, is scoped, and can upload a release asset without leaving residue.
- `references/no-root-cli-install.md` — installing a CLI on a rootless hosted instance: verified release download, persistent path, PATH wiring, authenticating from the delivered secret, and the checksum/PATH footguns.
- `references/cloud-provider-access.md` — verifying a provider API token from its own file, registering an SSH worker key idempotently (fingerprint read-back, no-passphrase proof, name-collision rule), and verifying cost ceilings against live prices before paid provisioning is enabled.
- `references/secret-exposure-triage.md` — locating every copy of a leaked credential (transcript DB and FTS, env snapshots, backups, git, public surfaces, provider payloads), classifying full vs prefix vs at-rest, redacting without claiming deletion, and deciding rotation from egress rather than alarm.
- `references/scheduled-external-jobs.md` — configuring and then *proving* a hosted service's scheduled job: stdin secret/variable input, job-vs-run verification, scheduler delay and dropped runs, cut-off-timestamp polling, metered-minute budgeting, and choosing the interval.
