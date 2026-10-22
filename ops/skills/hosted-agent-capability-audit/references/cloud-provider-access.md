# Cloud provider access for disposable worker instances

Scope: the agent drives a cloud provider's REST API to create and delete the workers it treats as disposable, so it needs its own API credential, an SSH keypair the provider knows about, and a cost policy that will not overspend.

## Verify the provider token before anything else

1. Store the token in its own file: `0700` directory, `0600` file. Extract only the named line out of the delivery `.env` (`sed -n 's/^\(export \)\?NAME=//p' .env | tail -1`) straight into the file — never through a variable you might echo.
2. Test it with the variable **scrubbed** from the subprocess: `env -u NAME -u NAME_FILE python3 <script>`, and have the script assert the variable is absent before reading the file. Otherwise an environment copy lets the test pass without exercising the file path the real consumer uses.
3. Use the cheapest **read-only list** call the API offers (servers / instances / projects) and report exactly two things: whether authentication succeeded, and the resource count. Never an Authorization header, never a token fragment.
4. A clean list call proves reachability and authentication. It does **not** prove write scope — see the scope rule in SKILL.md and `github-token-scopes.md` for the pattern.

Print a length/prefix/whitespace check when you want to confirm what landed on disk; that is the most you should ever reveal about a stored secret.

## Register the SSH public key idempotently

1. **Reuse or generate, never overwrite.** If a dedicated worker key already exists, check whether it is suitable before making a new one; preserve any existing keys. Generate with `ssh-keygen -t ed25519 -N '' -C '<purpose>' -f <persistent-home>/.ssh/<name>`, `0700` directory, `0600` private key.
2. **Prove it suits unattended use.** `ssh-keygen -y -P '' -f <private>` must re-derive the public key without prompting, and the derived blob must equal the `.pub` file's blob (compare the base64 field only — the trailing comment is cosmetic). A passphrase-protected key fails right here, which is the cheapest place to discover it.
3. **List the provider's keys first.** If the intended name is free, create it. If the name exists, compare the stored public-key blob against yours: identical means reuse it; **different means stop and report** — never silently replace another key that happens to share a name.
4. **Verify by reading the key back**, not by trusting the create response. Compute the local fingerprint in the provider's own format before comparing: providers commonly report MD5 as colon-separated hex while `ssh-keygen` defaults to SHA256, so run `ssh-keygen -l -E md5 -f <pub>` and require an exact string match with the provider's field.
5. **Record the public half where a human can copy it** — the registered name, the provider-assigned id, the fingerprint and the verification result, in a committed note. A public key is not a secret and may be shared; the private key never leaves the coordinator and is never committed.
6. **Point the local policy at both halves** (the registered key *name* and the private-key *path*) as soon as they exist, and confirm the field actually matches what you registered — a placeholder name written earlier is a silent mismatch at launch time. Leave paid launches disabled.

## Cost ceilings: verify against live prices, through the launch path's own check

Before paid provisioning is enabled, prove the policy's hourly ceilings the way the product will:

1. **Read the pricing endpoint for the target location and take the gross figure** — the one including tax. A net price understates the ceiling, and the launch check usually compares against gross.
2. **Call the product's own ceiling-check function**, giving it a minimal stub client that returns the live payload. Reusing the shipped comparison is stronger evidence than redoing the arithmetic, and it exercises the fail-closed branch instead of only the happy path.
3. **Include every separately billed line item** for that instance. A primary IPv4 is commonly priced apart from the instance type; a ceiling derived from the instance price alone is short by exactly that amount at launch.
4. **Tabulate it**: type | ceiling | live gross (instance + add-ons) | pass/fail | headroom. Headroom is the operator's real decision input — a pass with a rounding error to spare will fail on the next price change.
5. **Check any config value you were handed against the code's own bounds**, and demonstrate the reject branch as well as the accepted one. A value that silently violates an internal range turns into a refusal during the first paid operation.

## The allowance is an admission estimate, not a cap

- A reservation is `ceil((lifetime + grace) / 60) × ceiling` hours, computed per job and retained; the budget check sums reservations in the month.
- **Raising the cleanup grace raises reserved hours** wherever the extra minutes cross an hour boundary — for short lifetimes it can double the reservation. Measure the effect across the lifetimes you allow and report the actual numbers instead of asserting the change is free.
- A resource left running is not bounded by its reservation: one mid-size instance can bill more per month than the whole allowance. Compute the monthly gross and say so alongside the budget.
- Use the wording "conservative admission estimate, not a provider billing cap" wherever the number appears — transfer overages and charges outside the reservation are not covered.

## Reporting the result

Give the registered key name, its provider id, its fingerprint, and the verification outcome as a short table, and state plainly whether anything was created or reused. `GET`-only probes for every other question: creating a server to "test" the keypair is a paid side effect nobody asked for.
