# Hosted web destinations

Depth for publishing a generated site as a destination: the calls, their preconditions, and the
ordering the host actually enforces. Examples use GitHub Pages because it is the common case; the
shape (create, deploy, configure, verify) is what transfers.

## The site is a repository-scoped resource with three separate states

- **Absent.** `GET /repos/{owner}/{repo}/pages` returns not-found. That is a normal answer, not a
  permissions failure - and it is the signal to *create*. Distinguish it from "no access" by reading
  the repository itself: if the repo is readable and the site is not, the site does not exist.
- **Present.** The response carries `build_type`, `source`, `public`, `cname`, `html_url` and
  `https_enforced`. Assert what you require of it (a workflow build type, no unexpected custom
  domain) before touching it, so an existing site configured by someone else is a reviewable conflict
  rather than something you silently adopt.
- **Built.** Nothing serves until a deployment has run. `html_url` existing is not the page being
  live.

Creating and updating are **different methods**: `POST /repos/{owner}/{repo}/pages` creates (with
`{"build_type": "workflow"}`), `PUT` updates an existing site. A `PUT` on a repository that has no
site answers not-found, which reads like an access problem and is really a wrong-verb problem.

## Order the calls: create, deploy, then enforce

1. `GET` the site; if absent, `POST` to create it with a workflow build type, then `GET` again and
   assert what you require.
2. Ensure the deployment environment exists (workflow builds publish through a `github-pages`
   environment, created with an empty `PUT` when missing). Existing protection rules stay intact -
   they can legitimately make a deployment wait for review, which is a pending state, not a failure.
3. Dispatch a deployment for an **exact commit SHA** and read the run back until it reports success.
4. **Only now** set HTTPS enforcement.

**The certificate is issued by the first successful deployment**, so `PUT` with `https_enforced: true`
before one exists is refused - GitHub answers `404 "The certificate does not exist yet"`. Treat that
specific refusal as a recorded *deferred* state and retry after a deployment succeeds; any other
failure on that call still propagates. Note that the read-back field can report enforced while the
write is still refused, so drive the retry off the write and the verdict off the read.

## Deployments are dispatched, not implied

- A workflow run triggered by a push builds a **preview**; it is not a deployment. Dispatch the
  deployment explicitly, against the commit that contains the content, and check the run is on the
  default branch.
- Dispatch is asynchronous: a first read may report nothing deployed. Record the intent (commit,
  timestamp, attempt count) *before* the API call so an uncertain response cannot cause an immediate
  duplicate, wait a couple of minutes before re-attempting the same commit, and cap the attempts -
  three is plenty, after which the correct move is to read the Actions runs rather than dispatch again.
- Completion is a successful run for that exact commit, verified against the deployment's own record.

## Content updates must be idempotent against someone else's edits

- Commit through the git data API with a base tree, so files the pipeline does not manage survive;
  a whole-tree replacement silently deletes unrelated work.
- Update refs **fast-forward only**. A rejected ref is a concurrent edit and must be a refusal, not a
  force-push: the whole point is to notice.
- Write an ownership marker into each managed repository on first contact, and require it on later
  runs. A repository that already occupies the pipeline's reserved paths without the marker is an
  adoption decision for the operator - refuse it instead of overwriting.
- Skipping unchanged files makes a resume a no-op, which is what makes "re-run the same bundle" a
  safe instruction.

## Conflicts in destination state are reviewed transitions

A repository often has slots already occupied before the site exists - a homepage pointing at the
upstream data portal, a description, an existing Pages site. Tooling must not overwrite them, but the
refusal has to be diagnosable and the resolution has to be reachable.

- Name **both** the existing value and the intended one in the refusal; an operator cannot review a
  conflict they cannot see.
- Check whether the intended value is genuinely better before adopting it - the site usually links
  the same upstream source, so replacing a homepage with the site URL may lose nothing. Verify that by
  reading the rendered page, not by assuming.
- Resolve it as a one-time reviewed transition at the destination (clear the slot and let the pipeline
  set it, or set it explicitly) so the **approved plan is not modified**. Changing the plan's inputs
  to route around a destination conflict invalidates the review that authorises the publish.

## Verifying a live site

- **No credentials at all.** Fetch the page, its machine-readable records and any linked destination
  anonymously; a publication verified with the publishing credential proves nothing about readers.
- Use ranged requests (`-r 0-99`) for large assets: proving the bytes are served does not require
  moving them, and a full download on every release is data movement with no extra evidence.
- Compare the live record's digest against the record that was reviewed, and check the required
  cross-links are actually present in the HTML on both the site and the thing it links.
- Read the HTTPS flag back on every site rather than assuming the earlier call took effect.

## Recovery rules

- A pending deployment is not completion: exit pending, resume the same bundle, and read the live
  record. Do not report a release complete on an uploaded preview or a green-looking build.
- On failure, resolve the reported condition and re-run the same approved bundle. **Do not delete
  resources or move tags to unstick a publish** - the data identity is not the thing that is broken.
- Keep a receipt beside the bundle recording observed steps, commits, run URLs, the error and the next
  action, and refuse to continue when the receipt's plan digest differs from the bundle's.
