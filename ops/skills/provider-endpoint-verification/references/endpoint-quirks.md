# Known endpoint quirks

Per-vendor facts verified against live endpoints. Extend with a short entry per
new integration; keep each to host, auth header, and id conventions.

## LunaRoute (`lunaroute`)

- **API host:** `https://gw.lunaroute.com/v1` is the only API surface — every
  path (`/chat/completions`, `/messages`, `/responses`, `/models`,
  `/embeddings`, `/images/...`) is served from it. `https://api.lunaroute.com/v1`
  returns `401 {"error":"Invalid or expired token"}` for *every* key: a host
  error that reads exactly like a revoked credential.
- **Auth:** docs show `LUNAROUTE-API-KEY: $LUNAROUTE_API_KEY`; plain
  `Authorization: Bearer <key>` is also accepted, so Hermes' `auth_type="api_key"`
  works against the correct host.
- **Model ids:** the live catalog is the authority. Seen: `glm-5.3`,
  `glm-5.3-flash`, `glm-5.2-vision`, `deepseek-4.1-flash`, `kev-4b`, `djev`,
  plus lane/variant ids (`<id>-background`, `glm-5.2-vision-flex`,
  `glm-5.3-vision`, `glm-5.3-vision-background`). Background ids are the
  low-priority lane of the same model, not a different model.
- **Client metadata:** each catalog entry carries `client_compat` (per-client
  `maxTokensField`, `thinkingFormat`, `thinkingLevelMap`), so check a dialect's
  entry before sending fields like `reasoning_effort`.
- **Hermes wiring — two supported forms:** the vendor's guide drives
  `hermes config set providers.lunaroute.api|key_env|transport`; the other is a
  user plugin at `$HERMES_HOME/plugins/model-providers/lunaroute/`, whose
  `base_url` in the `ProviderProfile(...)` call is what actually decides the
  host. Check which one is registered before editing.
- **Reasoning budget:** `deepseek-4.1-flash` thinks before answering, so a
  16-token probe returns `content: null` with all completion tokens reported as
  `completion_tokens_details.reasoning_tokens` — a 200, not an error.

## Blocked / failing fetches

When the vendor docs site itself is unreachable (bot wall, 404 marketing path),
recover it per the `blocked-page-recovery` skill before concluding the vendor
publishes no API documentation — the docs subdomain is usually the live one.
