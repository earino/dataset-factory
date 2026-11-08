# Cutover runtime diagnosis and verified zero-tool selection (2026-11-08)

**Integration correction:** the empty-list observations below cover selected
source functions, not an end-to-end quiet CLI invocation. In this installed
revision, `cli.py::_build_cli_from_args` treats an empty `toolsets` string as
an unspecified selection and may substitute the profile/coding defaults before
the gateway mapping. Therefore `-t ''` is **not established as a working zero-tool
CLI command** by this evidence. No such inference probe was run. The replacement
uses the already observed, explicit `web` toolset for construction as well as
research; it does not rely on the proposed empty selection.

Tick `07d6f8be3783` paused 12:35:32Z for the adapter fix; independent cleanup
sweep `e80975eddd4a` remained active. Candidate/attempt rows untouched.

## Verified supported explicit zero-tool selection (read-only source, no probe)

The installed gateway refuses unknown toolset NAMES but accepts an EMPTY LIST:

- `gateway/session_policy.py` (sha256 `2fd143cfa7be04a2c3cea181dbe39d32945cfc9d8449e499f4aa2766213dd878`)
  `session.create` toolsets validation, lines 659-671:
  ```python
  explicit = params.get('toolsets')
  if 'toolsets' in params:
      if not isinstance(explicit, list):
          _refuse('toolsets', f'must be a list of toolset names, got {type(explicit).__name__}')
      known = validate_toolset if bypass else saved_toolset_resolver(config)
      for name in explicit:
          if not isinstance(name, str) or not known(name):
              _refuse('toolsets', f'unknown or invalid toolset name: {name!r}')
  ```
  A list with zero members passes validation -> a session created with zero toolsets.
- `hermes_cli/gateway_chat.py` (sha256 `f689d2471c2020e2b884375f45dc850332af934f958d2a633ec1275cf6ebdb02`)
  `_requested_policy` conversion:
  ```python
  policy["toolsets"] = [name.strip() for name in policy["toolsets"].split(",") if name.strip()]
  ```
  An empty CLI string becomes `[]`; `_launch_flags` retains it (drops only None/False).
- `toolsets.py` (sha256 `9aed91987f1403b02df22997491b90fedcf2516756a0f7ab9b6c245d5f769159`)
  `validate_toolset`: known means `{"all","*"}`, the TOOLSETS registry, plugin
  toolset names, or registry aliases. `__none__` is in none of these.

Conclusion: for code tasks the adapter should pass `-t ''` (empty string) rather
than `-t __none__`. The empty-string form converts to `[]`, the gateway accepts
`[]`, and the session's recorded tool pin should then assert `names == []`
(the same assertion `factory/audit_model_session.py` already applies).

## Demonstrated failures (evidence in this directory)

Mode A, deterministic (all `research=False` tasks): gateway session.create
refused `-t __none__` — `invalid_params field=toolsets detail=unknown or invalid
toolset name: '__none__'` at 12:31:10Z (build-1) and 12:34:10Z (build-2); the
child exits 1 with zero sessions, surfacing as `accounting: "Expected one model
session; observed 0 new sessions"` (see both failure.json files).

Mode B, intermittent (provider): `openai.NotFoundError: 404
INFERENCE_MODEL_NOT_FOUND` for `deepseek/deepseek-v4.1-flash-1017` on the
primary route; a `Fallback activated ... (nous)` rescue succeeded at 12:33:46Z
on a diagnostic probe, but `rw-e2258bc4dc52-discover-1` (session
`local-c291a022…`, usage retained here) ended exit 1 without a parseable
response, consistent with a mid-session terminal 404 before rescue.

Disclosure: that diagnostic probe (one 1-turn call, ~3k tokens via the nous
fallback) ran at 12:33:44-49Z before the no-reproduction instruction arrived and
overlapped `rw-e2258bc4dc52-discover-2`'s accounting window; that attempt dir
holds only attempt.json/prompt.txt (no usage/failure/response), the expected
signature of the resulting session-identity ambiguity. No further probes.

## Selected actual source (successful discovery, response.json here)

`source-000001` discovery attempt `rw-4fa4bc1fda01-discover-1` succeeded
(296.3 s, 11 calls, route deepseek-v4.1-flash:1017 via provider nous) and
selected `nid-dam-condition-screening` — U.S. Army Corps of Engineers National
Inventory of Dams, public domain (U.S. Government work), with access/terms/task
evidence; the controller advanced the candidate discover -> build. The
candidate remains unqualified until built, qualified and reviewed.
