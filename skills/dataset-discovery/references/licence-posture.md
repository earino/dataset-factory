# Licence posture when the publisher states no terms

For a source that is openly published but carries no readable licence. The goal is a recorded
posture that is honest in both directions: it does not claim a grant that does not exist, and it
does not block a source the operator has decided to use.

## 1. Read every channel before saying "no terms"

Silence is a claim about the publisher, so it needs the same evidence as any other finding. Check,
in this order, and record URL + date + what was actually there:

1. The dataset API's own metadata (`metas.default.license`, `license_url`, CKAN `license_id`).
2. The dataset page as rendered, not only the JSON.
3. The portal's terms pages — try `/pages/terms`, `/pages/terms-of-use`, `/terms`; note any 404.
4. The publisher's open-data page and its copyright page. Open-data policies describe *intent*
   ("open by default", "five principles") and almost never name a deed; the copyright page
   usually addresses the website, not the datasets.
5. The national or state harvest catalogue (data.gov, DataVic, data.europa.eu). A harvest value
   like `other-open` with `license_url: null` is a **category, not terms** — record it as such.

**A blocked page is not an absent page.** Council and agency HTML surfaces frequently return 403
to a plain HTTP client while rendering fine in a real browser. Before recording "the publisher
states no terms", load the page in a browser and read it; a bot block recorded as publisher
silence is a fabricated finding that later gets quoted as evidence. See `blocked-page-recovery`.

## 2. When the publisher stays silent, ask once with a deadline

Draft a short enquiry: which licence applies, whether redistribution of the data *and derived
features* is permitted, and the preferred attribution wording. Send it, or hand it to the operator
to send. Pair the ask with a dated fall-off (e.g. reject if no written answer arrives by a named
date) — an enquiry with no deadline is a candidate parked forever.

## 3. When the operator accepts the risk instead

The decision is legitimate and it is the operator's to make. Record it as exactly what it is:

- **`basis`** — the channels checked and what each said, then the operator's instruction, quoted,
  and the sentence "that is a risk acceptance by the dataset owner, not a publisher grant".
- **`source.status`** — "no licence stated; not public domain; not a standard open licence",
  redistributed on the recorded risk acceptance.
- **`compilation.scope`** — the dedication covers *our contribution only* (target, selection,
  splits, features, packaging) and explicitly does not relicense the source rows.
- **`conditions`** — attribution shipped in README, dataset card and citation; a takedown route
  the publisher can actually use (the public repo's issue tracker or the operator's handle — never
  an invented address); the rule that no standard licence may be presented as the publisher's;
  and withdrawal or relicensing if terms appear.
- **Never inherit it.** One operator risk acceptance covers one candidate. A sibling dataset from
  the same publisher needs its own file, explicitly stating what it imports and from where.

## 4. Why the file matters more than the chat

`release-manifest.py` reads `candidates/<id>/license.json` into the public manifest, so this file
is what a reader, a lawyer and the publisher will each see years later. Write it so that none of
the three can mistake a risk acceptance for permission, and so the attribution and the way to ask
for removal are both in the artifact rather than in a conversation.

A related trap: the Hub card and the site page must state the posture in the same words —
"licence not stated by the publisher; our derived contribution is CC-BY-4.0" — never a bare SPDX
id that reads as the publisher's own licence.
