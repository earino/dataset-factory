# Installing a CLI on a rootless hosted instance

Preconditions: persistent path writable, no `sudo`, no package manager, outbound network. Confirm the arch first (`uname -m`) and the presence of `curl`, `tar`, `sha256sum`, `install`.

## 1. Verified download and install

Pin the version in anything you re-run; do not track "latest" in a script.

```sh
set -eu
VER=v2.101.0                     # vendor tag; strip the leading v for asset names
ASSET="gh_${VER#v}_linux_amd64"
OUT=$(mktemp -d)

mkdir -p "$PERSIST/.local/gh" "$PERSIST/.local/bin"
curl -sSLo "$OUT/asset.tar.gz" "https://github.com/cli/cli/releases/download/$VER/$ASSET.tar.gz"
curl -sSLo "$OUT/checksums.txt" "https://github.com/cli/cli/releases/download/$VER/gh_${VER#v}_checksums.txt"

EXPECT=$(grep "$ASSET.tar.gz\$" "$OUT/checksums.txt" | awk '{print $1}')
ACTUAL=$(sha256sum "$OUT/asset.tar.gz" | awk '{print $1}')
[ -n "$EXPECT" ] && [ "$EXPECT" = "$ACTUAL" ] || { echo "checksum mismatch - abort"; exit 1; }

tar -xzf "$OUT/asset.tar.gz" -C "$OUT"
install -m 755 "$OUT/$ASSET/bin/gh" "$PERSIST/.local/gh/gh"
ln -sfn "$PERSIST/.local/gh/gh" "$PERSIST/.local/bin/gh"
rm -rf "$OUT"
```

Notes:

- The release API (`https://api.github.com/repos/<owner>/<repo>/releases/latest`) is the way to discover the current asset names and sizes — useful to confirm a `linux_amd64` build exists before writing the script.
- `install -m 755` sets the mode explicitly; a tarball's modes are whatever the packager chose.
- Delete the download directory afterwards, and report the installed size to the user (a self-contained Go binary is tens of MB; a stale tarball doubles it).

## 2. PATH wiring on a persistent home

Both files, idempotently, then verify in a fresh terminal call:

```sh
case ":$PATH:" in
  *":$PERSIST/.local/bin:"*) ;;
  *) PATH="$PERSIST/.local/bin:$PATH" ;;
esac
export PATH
```

Terminal-tool shells on a hosted instance do source `~/.profile` / `~/.bashrc` from the persistent home, so this is durable across restarts — but it does **not** follow for cron or for other processes, which is why credentials get a launcher instead of an `export` here.

## 3. Authenticate from a secret that is already on disk

The value must never reach stdout. Parse it inside the command that consumes it:

```sh
TOK=$(sed -n 's/^\(export \)\{0,1\}GITHUB_TOKEN=//p' "$HERMES_HOME/.env" | tail -1 | tr -d '"'"'"' \r')
printf '%s' "$TOK" | gh auth login --hostname github.com --with-token
unset TOK
gh auth setup-git          # git then delegates to the CLI's helper
```

Then confirm: `gh auth status` (account and scopes), plus a real API call such as `gh api rate_limit --jq '.resources.core | "\(.remaining)/\(.limit)"'`. `gh auth status` alone proves the login exists, not that it authorises the operation you need.

## 4. Footguns

- **Duplicate copies of the secret.** The CLI store (`~/.config/gh/hosts.yml`, 0600) and the original `.env` entry both hold it. A rotation that updates one leaves the other live and working — tell the user both, and re-run the login after any rotation.
- **Stacked git helpers.** After `gh auth setup-git`, remove any hand-rolled credential helper configured earlier, so `git config --global --get-regexp credential` shows one path.
- **A symlink is fine for the binary, not for credentials.** Keep secret-bearing env wiring in the launcher; do not bake a token into a wrapper.
- **Per-repo vs global helper.** A `credential.https://github.com.helper` entry is scoped to that origin and overrides a generic `credential.helper`; check with `--get-regexp credential` rather than reading one value.
- **Unverified installs.** Never extract-and-run a download whose checksum you did not compare, and never `curl … | sh`.
