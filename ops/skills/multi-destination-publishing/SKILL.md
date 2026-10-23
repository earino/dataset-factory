---
name: multi-destination-publishing
description: "Use when publishing one artifact to several destinations."
version: 1.2.1
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [publishing, release, datasets, registries, huggingface, github, manifests, credentials, verification]
    category: devops
    related_skills: [ephemeral-worker-lifecycle, post-push-verification, validation-gate-design]
---

# Multi-destination publishing

## When to use

When one accepted artifact must be obtainable from more than one place: a release page and a dataset
registry, a package index and a mirror, a public store and an internal one. Also when adding a second
destination to a release procedure that already has one.

The failure this skill exists to prevent is drift: two destinations that slowly describe different
artifacts, or a release reported complete while one platform is empty.

## Procedure

1. **One manifest is the source of truth, and every destination's documentation is generated from
   it.** Version, checksums, split or partition definitions, labels, provenance, licence status and
   measurements all come from that one file. A card, README or listing written by hand for the second
   platform is a second description of the artifact, and the two will disagree.

   The same holds for every claim the documentation makes about its own **state** - visibility, a
   publication status line, "nothing here has been published". Derive those from the per-destination
   status record like any other fact. A generator that hardcodes them keeps asserting a status that
   has stopped being true, and the documented "regenerate the manifest from recorded evidence" step
   re-asserts it, so the stale claim survives exactly the operation meant to refresh it.

   The order of those two steps is part of the rule: write the state change into the per-destination
   record **first**, then regenerate. Regenerating from a record that still carries the old state
   re-emits the old state - and the document looks freshly generated while being wrong, which is
   harder to notice than one nobody touched.
2. **Plan before publishing.** A `--plan` path that builds the generated files and prints exactly
   what would be uploaded, per destination, with byte counts and digests, and needs no credential.
   It is the cheap checkpoint that catches a wrong layout or a stale manifest.
3. **Create private, and verify privacy from the service.** Create the destination private, then read
   the flag back and refuse to continue if it came back public. Public visibility is the owner's
   decision, taken separately, on both platforms at once - never a step in the procedure.
4. **Move the bulk on the worker, not the coordinator.** Small generated files can go from the
   control host; the artifact itself moves host-to-host, verified digest-by-digest, in units the
   worker can re-run. Budget and teardown follow `ephemeral-worker-lifecycle`. **Fan out from the one
   local copy: the machine that fetched the artifact pushes it to every destination in the same
   pass.** Copying destination-to-destination re-reads bytes out of the first platform to build a
   second copy - a second full transfer, a dependency on the first platform's bandwidth, with no
   gain in verification. The staging area is a transit buffer, not a home: once a destination
   verifies, the intermediate copy has no reader and should be released according to the cleanup
   policy rather than accumulating.
5. **Track completion per destination.** A small status record beside the release names each
   destination with its verified flag, timestamp, revision and what was checked. One platform being
   done while another is pending is a normal state to report; "the release is complete" is only true
   when every destination verifies, and a package check should refuse a manifest claiming published
   with a destination unverified.
6. **Verify by reading the destination, at three levels.** Presence and size; the digest, chosen for
   how that service stores the file (see pitfalls); and a **functional load** - actually fetch or
   load the artifact at the pinned revision and compare row counts, schema and label values against
   the manifest. A file that exists but does not load is not published.
7. **Tag or version last, and idempotently.** A version created before the content lands pins a
   commit that does not contain it, and every pinned fetch then comes back empty. Make the step
   preserve an existing tag: the same verified commit is a no-op; a different commit is a refusal
   requiring a new reviewed version. Create a missing tag at the exact verified commit, then read
   back the tag and branch. Never delete or move a published tag to make a repeat succeed.
8. **Make every upload idempotent and resumable.** Per unit: skip anything already present at the
   expected digest, retry a bounded number of times with backoff, and report the skipped count. A
   sequential publish that fails halfway should re-run by sending only what is missing.
9. **Sync at release time, deterministically - never by a model on a schedule.** Comparing or
   reconciling two copies is part of the release, with fixed steps and bounded retries. A recurring
   agent that polls two destinations and edits each independently is how they diverge.
10. **Publish corrections as a new version.** Prior versions are immutable and preserved; nothing is
    edited in place. **While nothing has been published, though, there is no version to preserve:** a
    correction made before any public visibility - and before any consumer holds the bytes - replaces
    the version in place, because leaving a wrong release beside the right one means two meanings for
    one tag. Re-issue rather than patch silently: cut the release and its tag at the corrected commit,
    keep the superseded destination record (and the digests it named) as evidence, delete it from the
    package so nothing derives state from bytes that are gone, and **re-run the verification that had
    passed on the old bytes** - a consumer check, a gate report or a load test belongs to the artifact
    it ran against, and a green result does not transfer to corrected data.
11. **A hosted website is a destination with its own provisioning order.** Creating the site,
    building it, and enforcing TLS are three states, and the host gates the last one on the second:
    GitHub's certificate exists only after the first **successful deployment**, and `https_enforced`
    is refused until then. Create the site, dispatch a deployment for an exact commit, wait for it to
    report success, and only then enforce HTTPS - and read the flag back instead of assuming it. A
    publish that tries to configure everything up front aborts at exactly the transition the host
    implies. Site and API shapes: `references/web-hosting-destinations.md`.

## A presentation layer is a destination, and it depends on the others

A site, catalogue or landing page describing the artifact is published material with a real
dependency: its links have to resolve for whoever reads it.

- **Refuse to publish the page while the artifact is private.** A public page whose download and
  repository links resolve to private resources is worse than no page - it advertises something the
  reader cannot obtain, and it reads as a broken release rather than an unpublished one. Make the
  presentation step require **public, verified** destinations and stop there; do not "fix" the
  refusal by publishing anyway or by degrading the links to private-only.
- **Hand over the artifact itself for review.** A self-contained rendered page opens standalone, so
  send the file rather than building an apparatus to re-render what the operator can already open -
  screenshots and preview servers are delay when the review is about the content. Lead with the
  decision being asked for and the buttons in front of it: what is prepared, what is still
  unpublished, and the single word that starts the publish. **Ask one thing at a time, in the
  conversation - never a batch of structured questions.** A form of four or five choices reads as
  interrogation, derails the review into filling in fields, and is worse than the delay it was meant
  to prevent; when several decisions exist, lead with the one that unblocks the work, state the
  default you will take on the rest, and let the operator object. When the operator has already
  approved the *outcome*, drive to it: preparation, re-issues, verification and publication are
  routine work inside that approval, not new decisions to put back to them. Report at the milestones
  they care about - what is live, what changed, what failed - rather than requesting permission for
  steps they have already authorised. This holds after an interruption too: when a restart cuts a
  run mid-way, resume the authorised queue and report at the next real checkpoint; asking whether to
  continue reads as having stopped, and the answer will be "why are you asking".
- **Approving the page is not approving the data.** Separate decisions, taken separately, on each
  platform; neither one implies the other, and the page's plan is reviewed on its own terms.
- **The reviewed plan is bound by its digest.** Publish from the exact digest that was reviewed, and
  treat a change to the plan's inputs as voiding the approval rather than as a detail: re-prepare and
  re-review. When the conflict is in the *destination's existing state* rather than in the plan - an
  occupied homepage slot, a site the tooling did not create - resolve it at the destination as a
  reviewed transition and leave the approved plan untouched, so what ran is what was approved.
- **Verify it the way a stranger would.** Fetch the page, its machine-readable records and the linked
  destinations with no credential at all, and confirm the required cross-links are present on each.
  A deployment job reporting success is not the site being live, and a pending run is not completion:
  resume the same bundle and read the live record.

## Adding a second artifact to a release generator

The generator that shipped the first artifact is usually one artifact wearing a general name: the
repository, the source attribution, the download layout, the flat asset names, the required-document
lists and the commands are all literals. Releasing a second artifact then edits the generator, which
is how two artifacts end up sharing one code path with two behaviours.

- **Audit for per-artifact literals before writing any of the second release** - repository and
  visibility, source block, layout, asset names, the required-document list, command strings. Each
  one is a place where the second artifact would otherwise inherit the first one's identity.
- **Move them into a small per-artifact descriptor, and refuse to guess when it is absent.** A
  generator that cannot find the descriptor should stop with a message naming it rather than falling
  back to the first artifact's values: a default here publishes another artifact's repository and
  attribution.
- **Keep the descriptor outside the package it describes.** Putting it in the release directory adds
  a file to the package, so the manifest gains an entry and the previously published bytes change -
  a "refactor" that silently mutates a shipped release. It belongs where the other per-artifact
  decisions live, not in the output tree.
- **Prove the generalisation by regenerating the first artifact and diffing bytes.** Rebuild its
  manifest through the new code path and require a byte-identical file, and no diff anywhere in that
  release tree. Semantic equivalence is not enough: the manifest and its asset mapping are what a
  reader checks against, so a reordered or reformatted one is a changed release even when every value
  matches. Do this before starting the second artifact, and again at the end.
- **Let the descriptor carry the parts-driven cases too.** Where an artifact's version or identity is
  composed from per-part gate outputs, read them from the record rather than composing a new value
  that resembles a tool output (`validation-gate-design`).

## Licensing and attribution

Terms are part of the artifact, declared before it is offered anywhere, and rendered on every
destination from one source.

- **Three fields, never one.** The licence of your code and documentation; the terms of your rights
  in whatever compilation or derived work you are publishing; and the source's own terms, preserved.
  These are different questions with different answers - a public-domain source says nothing about
  the code that derived from it, and a permissive licence on your compilation says nothing about the
  data underneath.
- **Dedicate your contribution, not the source's data, and say so in words.** A scope sentence
  belongs in the notice: what is covered, what is not, and that the source keeps its own
  designation. Relicensing someone else's data is not yours to do, and a notice that fails to draw
  the line reads as a claim over it.
- **Preserve the source's designation, attribution and suggested citation verbatim**, label derived
  data as derived, and never present it as the source organisation's official product.
- **A permissive default is not a blanket override of upstream terms.** Choose terms compatible with
  each source: attribution, share-alike and non-commercial requirements carry through unchanged, and
  a source whose licence cannot be read is not published at all. Say that in the policy text, or the
  next artifact inherits a permission nobody granted.
- **Redistributing third-party files needs the permission recorded and the contributor credits
  kept** - including files from a project you own. Record who confirmed what, and keep the credits
  intact in the shipped copy.
- **Declare terms in a small per-artifact file plus a standing policy, and generate them into the
  manifest.** A licence block edited into the manifest by hand is lost the next time the manifest is
  regenerated - which is exactly when it matters.
- **Refuse at the gate.** A package with no declared terms, or one naming a licence file it does not
  ship, should fail the check rather than be assumed permissive.
- **A licence change is a package change.** Editing a licence document changes its hash, so
  prepare a new reviewed package version, regenerate its manifest and re-verify. Data digests
  may stay identical, but package bytes changed. Preserve existing version tags and published
  manifests; do not re-point a historical version for a licence or documentation correction.

Depth, including the declaration shape and how one source renders on each destination:
`references/licensing-and-attribution.md`.

## Credentials

- **A publishing credential is not a read or inference credential.** They are separate values with
  separate scopes; publishing must not be "fixed" by reconfiguring the read path.
- **Least privilege, per destination.** Use the narrow credential for each direction and check both
  scopes at planning time, refusing the job before it is provisioned rather than on a paid worker.
- **The value never travels with the artifact.** Not in a bundle, an input mount, a container, a
  log, a manifest, a release asset or a command-line argument. Pass it in the child process's
  environment, or read it from a mode-0600 file the worker host owns - a client library that looks
  for its own variable will not authenticate an environment you deliberately stripped.
- **Never route a credential through a shell default or an echoed expansion.** Writing
  `${TOKEN:-fallback}` in a command prints the value into the transcript the moment the variable is
  set, and `set -x` or a copied command line does the same - a convenience default becomes the
  disclosure. Reference the mode-0600 file at the point of use, or read it into a variable with no
  default and no echo, and check the command for an expansion over a secret before running it.
- **Keep exported secrets out of the session's own scratch.** The agent harness snapshots the shell
  environment to plaintext files under the scratch/TMPDIR directory as a session starts, so a
  credential exported for convenience is written to disk by something other than you, outlives the
  session, and is not covered by any later cleanup of the release. Prefer the file at the point of
  use over exporting, and treat that directory as a place to inspect for snapshots and for clones
  made while a token was set.

## One record, or none

A release is described by several files written at different times - the manifest, the producer's
quality descriptor, a summary, the per-destination status file, the candidate record, the baseline
result. Each is written by different code and each consumer that reads them invents its own
fallback, so an absent or differently-shaped field does not fail at write time; it renders as "no
data" or a dash weeks later, and the artifact is fine the whole time.

- **One canonical shape, defined once.** A small schema module with a `load_release()` that
  normalises the known legacy shapes on read (flat splits, level-nested splits, path maps with the
  counts in a sibling file, an AUC under any of its historical key names) and raises a named error
  naming the file and field otherwise. Every consumer - dashboard, site builder, registry card,
  package check - reads through it instead of reaching into raw dicts.
- **Writers fail closed.** A generator that cannot find a required field stops, rather than emitting
  `{}` or `null` and letting a reader decide what that means. Freshness at read time is not a
  substitute: the writer is the only place that knows the value was supposed to exist.
- **Normalise on read, never rewrite published artifacts to fit.** Legacy releases stay
  byte-identical; the schema adapts to them, not the other way round.
- **Pin the shape with a conformance test over every release on disk**, so drift is caught on the
  commit that introduces it rather than by an operator noticing a missing number.

## Pitfalls

- **A receipt is not a destination record.** The publish step usually writes two things: a run
  receipt for the job, and an entry in the release's per-destination status file. Downstream
  consumers - a catalogue, a website builder, a status page - read only the second. When a new
  destination (a hosted site is the common case) is added by a code path that writes the receipt but
  not the entry, the artifact is genuinely live and every downstream surface reports it missing; the
  bug looks like a display defect and is really a missing write. Add the entry in the same step that
  declares success, idempotently, and backfill existing releases by measuring the destination
  (anonymous fetch of the URL, then record `verified` with a timestamp) rather than assuming it.
- **Assuming one digest identifies a file everywhere.** Large-object storage reports a content
  sha256, while a small file stored as a plain repository blob reports a different id over different
  bytes - comparing them reports a mismatch on a perfect upload. Check the digest the service
  actually exposes for that storage class, and hash what you download for the small ones.
- **Letting the destination's naming rules dictate the layout.** Many artifact hosts reject `/` in
  asset names, so files arrive flat; the download helper must restore the layout consumers expect,
  and the placement rule (which files sit at the root, which in a subdirectory) belongs to the
  artifact, not to the upload code.
- **Trusting a client call's success instead of the service's record.** Re-read the destination
  after each upload and compare the digest it reports; "the client returned" is the same class of
  evidence as "the job record says ok".
- **Verifying labels from the loader's declared feature type.** A CSV or table column is inferred as
  a plain numeric type with no class names, so a check written for a labelled-vector type reports a
  mismatch on a perfect dataset. Read the label's distinct values out of the loaded data and compare
  the positive count per partition against the manifest.
- **Calling a client method from memory.** Signatures differ between versions - a `create_tag` may
  take a message in one and reject the keyword in another. Check the installed client's help or
  source before wiring a step, and keep a re-runnable step idempotent so a fixed signature can be
  re-tried without duplicating content.
- **Declaring privacy instead of demonstrating it.** The strongest evidence a private destination is
  private is that the same documented fetch **without** a credential fails, while the pinned,
  credentialed one succeeds. Record both outcomes. The same technique proves the opposite transition:
  to show a destination is public, read its visibility field anonymously and range-fetch every asset
  with no credential - a bounded range, not the whole file, since proving the bytes are served does
  not require moving them.
- **A destination record that downstream tooling validates has a shape of its own.** The status file
  is not only a note for humans: the next consumer of the release - a website builder, a catalogue, an
  index - reads it and refuses when it disagrees with the manifest. Discover its required fields from
  the consumer, not by iterating one refusal at a time, and record them together: the release tag, the
  artifact version, each destination's verified flag, the version key that destination uses (one
  platform may want `release_tag`, another `revision`, and a wrong or absent key reads as "this release
  has not been verified"), and the **list of files verified per destination** - joined on the key the
  record defines, and expressed in the paths that destination actually serves. A qualification entry
  naming the exact artifact version with a passing result is usually required too, and a record left
  over from a superseded re-issue will make the consumer refuse correctly. Enumerate the whole shape
  once and re-verify it after every re-issue. Two details cost a whole run each: the version in that
  block must be the **full** digest, not the short form your own tooling prints (a truncated hash is
  a different string, and the consumer compares equality, so it refuses with "a passing qualification
  for this exact artifact is required" while the artifact is in fact qualified), and the block needs
  its **result string** as well as its boolean - a record carrying only `ok: true` reads as no result
  at all. Normalise that block from the gate report once, in the code that writes it, rather than
  hand-writing it per candidate.
- **A manifest that hashes the record of its own publication.** A per-destination status file cannot
  be listed in the manifest's own file table if writing it changes the manifest - it is circular.
  Keep it outside the hashed set and say so in the check.
- **Describing a destination from a separate set of notes.** A second platform's card or listing
  written by hand is a second description of the artifact, and the two drift. Generate every
  destination's documentation from the manifest - including its licence field and scope sentence -
  and keep only the platform's own formatting in the generator.
- **Reading "no licence file upstream" as "nothing to do".** It means the permission is unrecorded,
  not that it is unneeded: get it confirmed by whoever owns the work, record the confirmation beside
  the files, and preserve the credits - or leave the files out of the release.
- **Pushing the second destination from the first.** The obvious implementation of "the same files on
  both platforms" is to download from platform A and upload to platform B, which doubles the transfer
  and makes each release read through the other platform for no benefit. Have the process that holds
  the accepted bytes push it to all destinations, and re-read the *service* - not the other
  destination - to verify each one.
- **Leaving the transit copy behind.** A staging area that is never cleaned grows a private copy of
  every release ever shipped. Make its release part of the completed release, not a tidying task
  someone remembers later.
- **Enforcing a web destination's TLS before anything has been deployed there.** The certificate is
  issued by the first successful deployment, so a policy call that sets it earlier is refused with a
  not-found that reads convincingly like a permissions problem - and aborting a nearly complete
  publication on it is the expensive version of the mistake. Order the calls create, deploy, enforce,
  tolerate the pre-deployment refusal as a recorded *deferred* state, and retry it once a deployment
  reports success.
- **A refusal that does not say what it compared.** A guard declining to overwrite an existing value
  ("an existing homepage differs") is unactionable until it names both the existing value and the
  intended one. Print them: the operator cannot review a conflict they cannot see, and the guard's
  whole purpose is to hand that decision over.
- **Assuming a web destination's API verb is create-or-update.** Creating and updating are usually
  different methods with different preconditions - on GitHub Pages a `PUT` updates and fails with
  not-found where a `POST` would have created. Read a site that is absent and a site you cannot reach
  as different outcomes, and branch on that rather than on one endpoint's error text.
- **A template placeholder that survives into the published document.** A substitution token written
  with doubled braces inside a formatted string renders to a single-brace string, so replacing the
  doubled form matches nothing, silently, and the literal placeholder ships in the documentation -
  producing a published example that cannot run (`load_dataset("{repo_id}")`). Use a token no
  formatting pass can rewrite (a sentinel like `__REPO_ID__`), and assert on the **built** output: zero
  placeholders and the real value present. A substitution nobody verified is a substitution nobody
  performed.
- **A test that asserts on the generator's source text instead of its output.** Grepping the
  generator for a marker it used to emit passes for exactly as long as that string survives, and
  fails the day dead code is deleted - reporting a defect where the behaviour is unchanged and
  hiding real ones. Same rule as the placeholder above: exercise the callable and assert on the
  produced artifact, so the check survives refactors and fails on behaviour.
- **A published example that the intended reader cannot run.** The documented command has to work
  under the artifact's *current* visibility: a credential argument left in a loading example makes it
  fail for an anonymous reader of a public artifact, and the reader has no way to know the argument is
  stale. Emit the credential argument only while the destination is private, and check the example as
  a stranger would. The same check exposes the opposite omission - an argument the artifact
  *requires* and the example leaves out. An artifact published under more than one configuration or
  partition refuses a config-less invocation at load time, so the example has to name one; defaulting
  the choice for the reader is the same defect with a quieter message, since they silently get the
  partition they did not ask for. Derive the example from the artifact's declared structure through
  **one shared rule that every generator calls** - the card, the landing page and any how-to-load
  document are three copies of one command, and three hand-written copies drift into three different
  commands of which only the one you happened to run is correct. Then load the pinned revision exactly
  as the example prints it, with no credential.
- **Editing documentation whose digest is pinned by another record.** If a destination's manifest
  table pins a digest of its own README or listing, a prose correction has to land **in one commit
  with the manifest entry describing it** - the tools that own that record recompute it, and until
  they do, the next run refuses with "the README already disagrees with its manifest". Build the tree
  and the commit together rather than pushing the document alone.
- **A documents-only licence change is a new package version when terms are pinned.**
  A downstream consumer reads the manifest at the existing tag, not the working tree. If
  terms differ, preserve the old tag and inspect both records. Prepare a new reviewed version
  for changed package bytes; never move each destination's pin to suppress the refusal. Re-read
  every new pin and review the resulting plan. Document changes can change its digest too.
- **Changing the licence in the manifest does not change a card whose frontmatter is a literal.**
  `license:` and `license_name:` usually live in a hand-written card template, so the manifest, the
  licence file and the notice can all say "no licence asserted" while the destination still
  advertises the old CC identifier - and every digest check passes, because the file matches its
  hash. After any licence edit, read the destination's **parsed** metadata back (`cardData` on a
  registry API, the repository's licence field on a git host) and assert it in a test; uploading the
  corrected file is not evidence that the platform re-read it.
- **Deferring a correction by saying so in chat.** "Table that for later" schedules the work; it does
  not shelve it. Write the deferred item into the record that owns the artifact - the release or
  candidate record's own next-action field, plus the project's running log - naming the exact edit, its
  refresh consequences, and what it does **not** change. A documentation-only correction changes no data
  digest and needs no new version, but it does move every rendered surface (the generated site page and
  its revision counter, the catalogue, the registry card), so enumerate those in the same line. Deferred
  work recorded only in the conversation is lost at the next context boundary, and a deferred item with
  no consequences attached is skipped when someone finally gets to it.
- **Re-running a publish tool whose create step asserts privacy.** A "create the destination"
  argument frequently hardcodes private, so invoking it again to refresh documentation on an already
  published artifact can re-privatise it. Use the upload-only path after publication, and read the
  visibility field back before and after to confirm nothing moved.
- **Comparing two records by a name that is not the join key.** A manifest may key an entry by the
  artifact's internal path while carrying the published name as a field inside it. Comparing the flat
  published names against those outer keys finds nothing and reports a mismatch on three perfectly
  correct files. Join on the key the record defines, and when a comparison reports a discrepancy,
  read the matched entry in context before believing it - a wrong key and a real mismatch look
  identical from the diff.
- **A published manifest whose metadata is wrong, and a writer that refuses to rewrite it.**
  Preserve the existing bytes, checksums and tags. If the metadata records valid legacy facts,
  correct their shared read normalisation. For an editorial website correction, use site_revision
  and the reviewed website plan. If the artifact or canonical manifest must change, issue a new
  reviewed version and new tags on both destinations, retaining the old version for reproduction.
  A no-op preserves bytes; it does not claim a known defect was corrected. The refusal must name
  the applicable correction path. Never "repair in place" by moving old pins.
- **Two readers of one record, each normalising it its own way.** When a builder writes a record in
  one shape and a later check reads it through a second, hand-written accessor, the two can disagree
  about a *correct* artifact - a partitioned record flattened for display and read flat again for
  verification refuses the release and the refusal names the data rather than the duplication. Put
  the normalisation in one shared function both call, so agreement is structural instead of
  maintained by hand, and keep a synthetic input of the awkward shape as the test case. A figure
  quoted in the documentation is one of those readers: a total computed by flattening a partitioned
  record is short by every nested part, so a document built that way misstates the artifact - compute
  the number through the shared reader and let it be the figure's only source.
- **Hashing a file that the same run then rewrites.** A generator that emits a checksum file from an
  artifact and records that file's own digest must write it *before* hashing the package; the other
  order records the previous file's digest, which stays invisible while the artifact never changes
  and fails the package check on the first release that does. Order: write every derived file, then
  hash, then emit the manifest.
- **Verifying against a value the platform cannot report, and "fixing" it by writing one anyway.**
  Some services expose a content digest only for files their large-object storage holds, and a
  tracking rule added later neither moves files already stored nor applies to uploads through the
  API - so a small file stays a plain blob with no comparable digest no matter what the repository
  declares. Never satisfy such a check by recording a path or digest the destination does not
  actually serve: a page then links to files that 404. Verify what the service genuinely reports
  (size always; digest when offered), fetch and hash the small ones under a cap **per call** - a
  metadata cap reused for an artifact is how a verification step tries to download the whole release
  - and name the gap in the output rather than dropping the check.
- **A helper whose stdout is parsed, printing anything else.** When a component's contract is a
  JSON (or otherwise structured) response on stdout, a diagnostic print - even a helpful note -
  corrupts the response and surfaces at the caller as an unexplained parse failure. Return such notes
  as a field of the response, and keep stderr or a receipt for anything human-facing.

- **A verification line written from the plan instead of from the check's own verdict.** The
  per-destination record is evidence, so every claim in it - verified, loaded, published, the revision
  it names - is copied from the check's own field in the job result. A job can upload every file
  correctly and still record `ok: false` with the missing partitions named beside it, and prose that
  says a check passed while the record says otherwise is a false claim in published documentation.
  Repair it in two parts, in this order: fix what the check objected to, then **run the documented
  path again against the published revision** - a correction is not a verification, and the earlier
  failure is recorded as it happened beside the later pass rather than overwritten by it.
  Keep existing version pins fixed. If the package changes, prepare a new reviewed version;
  distinguish its package digest from unchanged data digests. Read the pinned revision, tag and commit ids back
  from the service; a hash transcribed by hand can carry a corrupted tail that nothing resolves until
  a consumer tries to fetch it.
 - **Answering "what is still unpublished?" from an artifact's own record.** A published artifact's
 record carries hand-written review and next-action fields asserting the state *before*
 publication ("nothing is public"), and nothing regenerates them - they are the same staleness the
 generated documents are protected against, sitting in the one field no generator reads. Sweep
 those narrative fields as part of the publication, and answer status questions from the record
 cross-checked against the live service (visibility, release tags, a load or fetch of the pinned
 revision), never from remembered prose: the queue a session carries forward is a claim about now,
 and it is the field most likely to have gone out of date. Read the pinned revision, tag and commit
 ids back from the service too - a hash transcribed by hand can carry a corrupted tail that nothing
 resolves until a consumer tries to fetch it.
 - **Sweeping the prose and leaving the structured fields alone.** The staleness is not confined to
 narrative fields: a record can still read `packaged` - or carry no publication block whatsoever -
 while the artifact has been live for days, because the stage vocabulary treats a
 pre-publication stage as released, so a check that accepts it reports OK on a record which never
 claims publication. Compare the asserted stage against the destination's live visibility, and
 **mirror the publication block from the per-destination status record the publish step wrote**
 (release tag, release id, revision commit, verified flags, the files verified per destination)
 rather than re-deriving it from memory: that file is the evidence, and a second hand-written copy
 of it is a second description that drifts. Correcting one record is also the moment to sweep its
 siblings for the same staleness - they were written by the same pass and go stale together.
 - **Reporting a suspected defect in a published surface before reading what defines it.** A
 convenience URL or alias that answers with content byte-identical to its parent looks like a
 broken pin, and an established design may specify it exactly that way (an immutable edition path
 plus an alias that legitimately coincides with it until a revision is cut). Read the document that
 specifies the surface, or the consumer that validates it, before writing the finding down: a defect
 report the design already accounts for spends the operator's attention on noise and devalues the
 findings that are real. When it does not check out, say so in one line - dismissed, and why -
 rather than quietly dropping it.
 - **Rewriting a machine-readable record without matching its serialisation.** Records on disk carry
 a fixed escaping and indentation, so re-dumping one from a parser with different settings (encoding
 non-ASCII the file escapes, or reformatting) rewrites every affected line and buries the one field
 that changed - a diff nobody can review, in a file whose review is the point. Detect the existing
 convention before writing (escaped `\uXXXX` versus raw UTF-8, indent width, trailing newline),
 write with it, confirm with a diff that only the intended lines moved, and check the file still
 parses. Inspect the raw bytes rather than the decoded text: decoded text never contains an escape,
 so a check for non-ASCII characters reports "no escaping" on a file that is escaped throughout.

 ## References

- `references/huggingface-datasets.md` - Hugging Face specifics: repository creation, changing
  visibility without re-privatising a published dataset, what the generated card may claim about
  itself, the dataset card's split configuration, version-pinned loading, upload from a worker venv,
  and the storage and loader quirks that make naive verification report false failures.
- `references/web-hosting-destinations.md` - publishing a hosted site as a destination: the GitHub
  Pages create/update/verify calls and their ordering, certificate and environment prerequisites,
  ownership markers, homepage conflicts, and how to verify a live site without credentials.
- `references/licensing-and-attribution.md` - declaring and rendering terms: the three-field split,
  the per-artifact declaration beside a standing policy, the refusal cases a package check should
  catch, and the scope wording that keeps a derived release honest about what it does not own.
