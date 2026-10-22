---
name: provider-endpoint-verification
description: "Use when an LLM provider call fails: verify the wiring."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [providers, gateways, api-keys, verification, hermes, harness, curl]
---

# Provider & Gateway Endpoint Verification

Class of task: an agent, CLI, or benchmark harness is wired to an
OpenAI-compatible LLM endpoint and calls fail — or the wiring must be *proven*
working. Covers Hermes provider plugins and `providers.*` config, harness
`base_url` + `api_key_env` pairs, and any OpenAI-compatible client. Use it to
verify endpoint host, auth, model ids, and lanes layer by layer before blaming
the credential.

Report first, fix second: when asked "is it working or not", the deliverable is
a verified verdict backed by real status codes, not a description of the setup.

## When to Use

- A provider/gateway call fails (401/403/404/400, wrong model, empty answer) and
the cause is not obvious — in Hermes, a benchmark harness, or any
OpenAI-compatible client.
- The user says an integration "is set up wrong" and asks you to prove whether
it works, especially with the credential in hand.
- Adding a new provider/gateway (new host, new plugin, new `base_url`) and it
must be proven working before dependent work runs.
- Suspected credential problem: verify the key, host, and model id separately
before changing any of them.

## 1. Reproduce with a raw curl before touching any config

Run the caller's exact command (or the vendor docs' canonical one) against the
endpoint and keep the HTTP status and body. A 200 carrying a completion proves
key + host + model id together. Do not edit config until that ground truth
exists, so the fix is verifiable by comparison.

## 2. A 401 is usually the WRONG HOST, not a bad key

An invalid-host or invalid-path response reuses the same envelope as a bad key
(`{"error":"Invalid or expired token"}`, `invalid_api_key`, ...). Probe every
plausible host and path with the *same* key — `api.<vendor>` vs `gw.<vendor>`,
`/v1/models` vs `/v1/chat/completions` — and treat the combination that returns
200 as the real API surface. Read the vendor's **docs** site for the canonical
base URL and auth header; marketing pages 404 and vendor "roster"/ledger pages
drift. Never weaken or rotate a key on the strength of a 401 alone.

## 3. Confirm the key the tool will actually use is the key you tested

Without printing the secret, compare the stored value against the one you have:

```bash
python3 - <<'EOF'
import hashlib
env = dict(l.split('=', 1) for l in open('$HERMES_HOME/.env')
           if '=' in l and not l.startswith('#'))
v = env.get('VENDOR_API_KEY', '').strip().strip('"')
given = '<the key under test>'
print('len', len(v), 'prefix', v[:8], 'matches:', v == given,
      'sha8', hashlib.sha256(v.encode()).hexdigest()[:8],
      hashlib.sha256(given.encode()).hexdigest()[:8])
EOF
```

Report only "matches" / "differs" plus a hash prefix. Never echo the key in any
surface, even when the user pasted it in chat, and never ask them to resend it.

## 4. Read back the DECLARED wiring, not the config file

The config file shows what someone edited; the registry shows what will run
(and the two can disagree — Hermes may have no `providers.*` keys at all and
instead register a user plugin under
`$HERMES_HOME/plugins/model-providers/<name>/`). Fix whichever one is actually
registered.

```bash
cd /opt/hermes && HERMES_HOME=$HERMES_HOME PYTHONPATH=/opt/hermes \
  /opt/hermes/.venv/bin/python3 -c "
from providers import get_provider_profile as g
p = g('<name>')
print(p.base_url, p.env_vars, p.fallback_models, p.default_aux_model)
"
```

User plugin files live under `$HERMES_HOME/plugins/` (persistent). Never patch
the image tree (`/opt/hermes`) — it resets on restart.

## 5. Fix in place, then verify in layers

Each layer below fails independently; a green layer does not vouch for the next.

1. Registry readback shows the corrected `base_url`.
2. Live model listing succeeds:
   `provider_model_ids('<name>', force_refresh=True)`.
3. One plain chat turn returns text
   (`hermes chat -q 'Reply with exactly: PONG' --provider <name> --model <id>`).
4. The **aux model path** works — auxiliary (title) generation runs on
   `default_aux_model`, so a stale aux id fails on an otherwise healthy provider.
5. A **tool-calling** round trip works: agent workloads need `tools`, not just
   chat. Any harness/benchmark file naming the provider gets its own smoke run.

## When the request is accepted and then goes silent

A gateway can accept the connection, take the key, and never send a chunk. That failure looks
nothing like a rejection and is routinely misreported as one, so separate the two from evidence
before saying anything to the user:

- **Rejection** has a status: 401/403, 429 rate limit, 404/400 unknown model. The body names the
  key, the quota or the model id.
- **Degradation** has no status at all: `Stream stale for 60s (threshold 60s) — no chunks received`,
  then `[Errno 32] Broken pipe`, repeated until the client's own abort threshold fires (for example
  "unresponsive for 6 consecutive stale attempts"). The key is fine; the backend is limping.

Corroborate with latency, not with the error text: read per-call latency from the agent log
(`API call #n: model=… provider=… latency=…`) or the session record. Calls that succeed at 50-90s
where the same route did 1-17s the day before prove degradation, and they prove the credential is
still accepted. A single stalled turn is not a payload-size problem either - check the context size
before blaming a long prompt.

Retrying into a degrading route repeats the stall, because the abort threshold is client-side. The
durable fix is a failover chain:

```yaml
fallback_providers:
  - provider: nous
    model: <model-id-on-the-other-route>
```

- Put it above `model:` in the config and validate through the product's own loader
  (`from hermes_cli.config import load_config`) rather than a YAML library you happen to have or not
  have - the loader is what will actually read it.
- Unpinned cron jobs and fresh sessions inherit the chain; a job or child pinned to an explicit
  provider/model does **not**, by design. Say which callers are covered.
- A running session keeps the route it started with, so say plainly that the failover applies to the
  next run rather than implying the current one is fixed.
- Back up the config before editing it, and report the backup path.

## 6. Rosters drift; lane variants are separate ids

`fallback_models` / curated lists are only what the picker shows when the live
`/models` fetch cannot be reached, so they go stale silently. Refresh them from
the live catalog (`GET {base_url}/models`) and keep only ids the gateway
actually serves. Batch/background/flex/vision variants (`-background`, `-flex`)
are distinct ids: include them only when they should be selectable.

## 7. Clear the stale model cache

`$HERMES_HOME/provider_models_cache.json` keys a row per provider + credential.
A row marked `fallback: true` means the live listing has *never* succeeded —
leave it and the picker keeps serving the dead roster after you fix the
endpoint. Once the live fetch works, clear it
(`from hermes_cli.models import clear_provider_models_cache;
clear_provider_models_cache()`) and re-list to confirm it repopulates live.

## Pitfalls

- `content: null` with a populated `reasoning` field is not a failure — a
  reasoning model spends `max_tokens` on thinking first. Raise the cap before
  declaring a model or route broken, and use the short probe only to prove the
  route, never to judge the model.
- Docs may prescribe a supported wiring different from what is installed (e.g.
  config keys vs a plugin). Both can be legitimate: verify the one in play and
  state in the report which form is installed, rather than converting it
  unilaterally.
- A vendor's published "roster" (site diagram, usage ledger, pricing page) is
  not the catalog. Only `GET /v1/models` is.
- A client's own stall-abort message ("provider has been unresponsive for N consecutive stale
  attempts") is not evidence of a rejection. It is a local timeout policy; check status codes and
  latency before telling the user they are being refused or rate-limited.
- Do not report a fix as done off the emitting call alone; re-run the failing
  command and quote its status.

## Reporting

- Lead with **working / not working**, then the evidence: status codes, model
  ids exercised, which commands ran.
- Name the defect as a mechanism ("pointed at the wrong API host, which 401s
  every key") rather than narrating the debugging.
- Never include the credential, even partially, except a hash prefix for
  matching.

See `references/endpoint-quirks.md` for known per-vendor host, header, and
model-id quirks gathered from real integrations — add a line there for each new
endpoint instead of growing this file.
