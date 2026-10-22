# Credential delivery to a hosted agent instance

Channel selection first, mechanics second. Match the channel to **what has to consume the secret**, not to what is easiest to hand over.

## Decision table

| Consumer | Channel |
|---|---|
| A git remote, REST API, or CLI on the instance | Provider variable in `$HERMES_HOME/.env`, written by the user |
| A website's login form the agent drives in a browser | Credential vault (`browser_vault_*`) |
| A remote/sandboxed worker process on another machine | Its own narrowly-scoped token, provisioned at boot; never the main one |
| A team-shared, centrally rotated secret | External secret manager via `hermes secrets` |

## 1. Dashboard env page — the general-purpose channel

The web dashboard is a machine-level admin surface with a credentials page. Route `/env`, labelled *API keys* / *Environment* / *Credentials* in the UI.

- UI path: `$HERMES_DASHBOARD_PUBLIC_URL` + `/env`. On a hosted instance the dashboard root typically 302s to the platform's own OAuth login gate, which is the correct behaviour — the user signs in as themselves.
- Backend: `PUT /api/env` → `save_provider_env_credential(key, value)` → `save_env_value(key, value)`, i.e. an **append/update of `KEY=VALUE` in `$HERMES_HOME/.env`**. There is no key allowlist, so a non-provider variable name is accepted.
- Practical consequence: the user can hand over an arbitrary API credential without it ever entering a conversation.

### Read-visibility of a newly written value

| Reader | Sees it immediately? | Why |
|---|---|---|
| Code that explicitly calls the config loader or parses the file | **Yes** | the env cache key includes the file's `mtime` **and** `size`, so a changed file is re-read |
| The already-running process's `os.environ`, and anything resolving through it | **No** | `os.environ` is a snapshot taken at process start |

So `get_secret()`-style lookups used by *internal plumbing* (cloning a private plugin or profile repo, for instance) can miss a credential added mid-session until the gateway restarts. **A plain shell command misses it too** — the terminal spawns a child that inherits the same start-of-process snapshot, and it does not parse `.env` for you. A credential added mid-session is picked up only by a command that parses the file itself or is handed the value/path explicitly. Never tell the user a consumer will see a new secret because the file changed; either restart the process or hand it the path.

### Delivering a path instead of a value

On an instance whose process env you cannot change, the reliable pattern is a wrapper the consumer is always invoked through:

```sh
#!/bin/sh
# scripts/<project> — export credential-file paths for terminal AND cron.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export PROVIDER_TOKEN_FILE="${PROVIDER_TOKEN_FILE:-/opt/data/.secrets/<provider>.token}"
cd "$project_root"
exec python3 -m <module> "$@"
```

Properties worth copying: it exports `*_FILE` **defaults** so an explicit override still wins; it works in non-interactive cron shells with no startup file and no restart; it carries **paths, never values**; and the tool behind it reports each credential as present/absent/unreadable without printing contents, exiting non-zero when one is unusable. Token files live at mode `0600` inside a `0700` directory under the persistent path, and the token file must never be a copy of a broader credential than the consumer needs.

### Consuming the value without exposing it

Resolve the secret *inside* the command that consumes it, so it never reaches stdout:

```bash
cd /opt/data/repos && \
  TOKEN=$(python3 -c "import sys; sys.path.insert(0,'/opt/hermes'); from hermes_cli.config import load_env; print(load_env().get('GITHUB_TOKEN',''))") && \
  git -c http.extraheader="Authorization: Basic $(printf 'x-access-token:%s' "$TOKEN" | base64 -w0)" clone https://github.com/OWNER/REPO.git
```

Never `echo` the value, never interpolate it into a URL, and never paste it into a report or chat message. Secret-redaction layers are a backstop, not the plan.

## 2. Browser credential vault — page logins only

`hermes vault add --kind {login,payment,address}`, listed/inspected via the `browser_vault_*` tools. Passwords are injected **server-side by `browser_vault_fill` on the exact origin the item was bound to**, and the agent only ever sees handles and identifiers.

**This channel cannot authenticate `git`, `curl`, or a CLI.** It exists for browser form fills. Proposing it for repository or API access is a wrong-channel error; use the `.env` channel instead. When a real login form *is* in play: `browser_vault_list` first, then type the identifier yourself and call `browser_vault_fill`; if nothing is saved for that origin, `browser_vault_save_login` asks the user through a masked prompt.

## 3. External secret managers

`hermes secrets {bitwarden,onepassword}` pulls keys from an external manager at process startup instead of storing them in `.env`. Only the manager's **bootstrap token** then lives in `.env`. A generic **command-helper** source lets any CLI vault (`pass`, `keepassxc-cli`, a custom script) supply `KEY=VALUE` lines.

Precedence, when several sources compose: your `.env`/shell wins unless a source sets `override_existing`; mapped sources beat bulk sources; first source wins within a shape. No source can overwrite another's bootstrap token.

Use this when the user already keeps secrets in a manager and wants central rotation — do not stand one up as a one-off to move a single token.

## 4. Egress credential injection (`hermes egress` / iron-proxy)

A disabled-by-default, TLS-intercepting egress firewall that **swaps proxy tokens for real API credentials before requests leave a sandbox**: the sandbox holds only a proxy token, never the real key. Managed via `hermes egress {install,setup,start,status,config}`.

This is the right shape when untrusted or **remote worker code** needs to reach an authenticated API and you would rather the real credential never sits on that worker. It is heavier than needed for a single credential on the main instance.

## 5. Logins that are not secrets

The half of a keypair that is public, a **deploy key's public key**, a public URL, and a repository `owner/name` are **not secrets** and travel fine in chat. Handing over only a public key is a legitimate way to grant access with no secret transfer at all — see `references/github-token-scopes.md`.
