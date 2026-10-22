# GitHub access for a hosted agent

## Name the variable what Hermes already reads

Hermes resolves HTTPS git credentials for its own internal clones in this order (`hermes_cli/git_credentials.py`):

1. `GITHUB_TOKEN`
2. `GH_TOKEN`
3. `gh auth token`
4. `git credential fill` against the user's configured helpers (any host, prompting disabled)

The resolved value is passed to git as a one-shot **`http.<origin>.extraheader`** in the environment — never embedded in the clone URL and never written to `.git/config`, so nothing is persisted into the checkout.

Practical upshot: setting **`GITHUB_TOKEN`** serves three consumers at once — Hermes' internal clones, the `gh` CLI, and your own `git`/`curl` commands. Prefer it over inventing a provider-specific name.

## Fine-grained PAT permissions, by operation

| Operation | Required permission |
|---|---|
| Clone / pull / push a private repo | **Contents: Read and write** |
| Create a release | **Contents: Read and write** |
| Upload or update a release **asset** | **Contents: Read and write** |
| Edit `.github/workflows` | add **Workflows: Read and write** |
| **Create a repository** (`POST /user/repos`) | **Administration: Write** |

`Metadata: Read` is always granted with any repository permission.

### The scope trap worth flagging to the user up front

A token restricted to **selected repositories** cannot create new repositories — the new repo is by definition not in its selected set. So for a workflow that mints a repository per artifact:

- **Narrow (recommended default):** token scoped to the existing repo(s) with Contents RW, and the **user creates each empty repo in the UI** (a few clicks); the agent pushes into it afterwards. Least privilege, no breadth to reason about.
- **Broad:** add Administration: Write and set repository access to *all repositories*. This trades away least privilege, and whether selected-repo tokens can create repos is reported inconsistently in the wild — treat it as unverified rather than promising it works.

### Rate limit as a reason to ask for a token at all

Unauthenticated GitHub API access is **60 requests/hour**; authenticated is **5,000/hour**. Even read-only research work over many repositories exhausts the anonymous budget, so a token is worth having independent of any write workflow.

## Alternatives, and when each is better

| Option | Gains | Costs |
|---|---|---|
| **Fine-grained PAT** in `.env` | One credential covers clone, push, repo creation (with Administration), and release-asset upload; scoped per repo | A secret sits on the instance |
| **Deploy key** (SSH) | No secret transfer — the **public** key is handed over in chat and pasted into the repo's Deploy keys | Per-repo only; cannot create repos; **SSH cannot upload release assets** (that path is REST + token) |
| **`gh auth login` device flow** | Best user experience — approve in a browser, no copy/paste | Needs the `gh` CLI present; classic OAuth scopes are broader (all private repos) than a fine-grained PAT |
| **Classic PAT (`repo` scope)** | Simplest to create; can create repos | Grants access to **every** private repo the user owns — not recommended |

## Verifying a delivered token: three tests, in this order

A credential that authenticates proves the least interesting thing about it. Run all three.

**1. It works, and it works through the file the consumer will read.** Store it with `umask 077`, file mode `0600` inside a `0700` directory, then verify by **length and mode only** — never echo, hash, or prefix-print the value. Run the test with the variable removed from the test environment:

```bash
env -u GITHUB_TOKEN -u GITHUB_TOKEN_FILE python3 /path/to/verify.py
```

and make the script's first act an assertion, so a stray environment copy fails loudly instead of silently passing:

```python
assert "GITHUB_TOKEN" not in os.environ, "env var still present - file path not under test"
token = Path("/path/to/token.file").read_text().strip()
```

Include the prefix of the token `type` in the report (a fine-grained `github_pat_…` versus a classic `ghp_…`) — the length and prefix are not secrets and immediately tell the user whether the *shape* they intended is what arrived.

**2. It is scoped.** A token you asked the user to narrow must be probed for breadth:

- `GET /repos/<owner>/<target>` → **200**, and read `private` / `visibility` from the payload rather than assuming.
- `GET /repos/<owner>/<some-other-private-repo>` → **expect 404**. A 200 here means the credential reaches beyond its intended repo and the isolation design is void.
- Enumerate `GET /user/repos?per_page=100&page=N` and count the **private** entries: public repos are listed for anyone, so a large total proves nothing. The private set should be exactly the repos intended (e.g. one staging repo), not the account's collection.

**3. It can do the load-bearing write, leaving no residue.** For release workflows the operation that fails late is the asset upload:

- Create a **draft** release with a unique tag (`draft: true`, unpublished throughout).
- Upload a tiny asset: `POST https://uploads.github.com/repos/<owner>/<repo>/releases/<id>/assets?name=<name>` with `Content-Type: application/octet-stream` and the bytes as the body.
- Read the asset back with `GET /repos/<owner>/<repo>/releases/assets/<asset_id>` and compare `size` and `digest` (`sha256:<hex>`) against the values computed locally. The digest field is the server's own hash — the cheapest real integrity check available.
- Delete the asset, then the release, then `GET` each once more and expect **404**; confirm the repo's release list contains neither the release nor a leftover tag.

Each API response for a create/delete returns 200/201 and 204 respectively — treat anything else as a failure to report, not a warning to note in passing.

## Remote workers get their own token

When remote machines upload artifacts, provision a **separate, upload-only** token for them rather than reusing the main one, and keep it off any machine that also runs untrusted code (see the egress-injection option in `references/credential-delivery.md`). Release-asset uploads are plain HTTPS `POST`s, so a worker needs `curl`/a Python HTTP call plus that token — no `gh` install required.

Verify the separation rather than trusting the naming: the worker token's private-repo enumeration should show only its own repo, and a probe of the coordinator's repo must 404. Keep the worker token out of the coordinator's git helper and out of any CLI login store on the instance.

Be aware of the platform's per-asset ceiling (2 GiB) when planning a release as an artifact-transfer path, and check for `git-lfs` availability before designing around it.
