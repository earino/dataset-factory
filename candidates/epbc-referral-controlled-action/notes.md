# epbc-referral-controlled-action — discovery notes

Opened 2026-10-28 (Oceania regional tick). Second-lead record: the AusTender
lead is this tick's primary verdict; this one carries a precise unpark/open
path rather than a finished one.

## Why it is interesting

The EPBC referral decision is a real, consequential screening outcome: a
"controlled action" declaration commits the proponent to a full assessment
(approved the ~20-business-day decision window after validation). The decision
is made on referral documents that are public, and the register is a per-project
panel with dates — a clean instant/label separation. No EPBC referral-outcome
benchmark exists on this bench, and no bulk register was found in the bounded
data.gov.au sweep.

## What was measured (2026-10-28, coordinator + real browser session)

- Portal list `https://epbcpublicportal.environment.gov.au/all-referrals/`:
  JS-rendered Power Apps PCF data grid. Plain urllib fetches the page (336 KB)
  but rows load via XHR; direct guesses at
  `/_services/entity-grid-data.json/2ab10dab-...` with page/skip/top params all
  404. In the real browser the grid renders 10 rows/page and the page reports
  "5000 records".
- List columns (browser-verified): EPBC Number, Project, Proposer/Approval
  Holder, Location, Industry Type, Valid Date, Project Status, Primary
  Jurisdiction. Observed Project Status value on live rows:
  "Referral Decision - Open for Public Comment".
- Per-project summary pages fetch anonymously with a plain client:
  `.../all-referrals/project-referral-summary/?id=<guid>` returns ~236 KB
  static HTML carrying EPBC number, project status, and the stage timeline
  (Lodgement → Validation → Referral Decision → Assessment → Final Decision →
  Post Approval → Completed). Verified on EPBC 2024/10023 (Princes Highway
  upgrade program - Milton Ulladulla bypass, status "Assessment Approach
  Determined") and EPBC 2026/10600 (High Sea Wind offshore wind farm, status
  "Referral Decision Made").
- The pages expose their Dynamics FetchXML in a "Debug Information" block —
  the portal is running in debug mode, which may make the grid's exact query
  replayable; that is part of the named next probe, not a measurement yet.

## Blockers / unknowns (in cheapest-first order)

1. Licence: unread. dcceew.gov.au/about/copyright and
   nationalepa.gov.au/copyright-information time out from this coordinator
   (three bounded attempts; socket timeouts, not HTTP refusals — the same
   host-side pattern as other past timeouts recorded in this repo).
   /terms-conditions/ on the portal 404s. The supported browser passes walls
   that plain clients do not, so the browser is the named next probe for the
   licence read. The sibling "Referrals Spatial Database" catalogue record is
   cc-by-4.0 — suggestive of the department's default posture but NOT the
   register's own instrument; no classification is made from it.
2. True population: "5000 records" may be the grid's cap rather than the full
   referral history (EPBC referrals since 2000 are plausibly ~10k+). Grid XHR
   replay (browser) measures it.
3. Label channel: is the terminal referral decision visible in the list's
   Project Status (cheap) or only per-project pages (~5000+ HTML fetches,
   worker job)?
4. Outcome vocabulary: the exact status strings for controlled-action /
   not-controlled / particular-manner decisions, and the per-year outcome mix —
   unmeasured.
5. Novelty: unsearched. No benchmark is known on this bench; the mechanical
   catalog/literature check (check-novelty.py) runs before any ready claim.

## What would close it

- Class C licence posture → closed under standing policy (no unsolicited
  permission email, no indefinite wait).
- Licence A/B + list carries terminal decision statuses + measured outcome mix
  with both classes over enough years → novelty check → ready review.
- Licence A/B + list does NOT carry outcomes → cost re-estimate (per-project
  fetch on a worker) before further investment.


## 2026-10-29 - licence decisive: portal's own terms prohibit redistribution; candidate DROPPED (class D)

All probes anonymous (supported browser + plain-client fetches), coordinator only.

### Licence chain (decisive)

- Supported browser (plain clients time out on dcceew/nationalepa): https://www.dcceew.gov.au/about/copyright
  -> "Unless otherwise specified, you can use our material under a Creative Commons
  Attribution (CC-BY) 4.0 International licence." Exclusions include "content that is
  specified as being subject to third party copyright limitations or some other licence terms".
  Its "No circumvention of terms" clause: "You must check and comply with the licensing
  information for each set of material you wish to use."
- https://www.nationalepa.gov.au/about/copyright -> identical CC BY 4.0 default (National EPA,
  administering agency since 1 July 2026).
- environment.gov.au/about/copyright redirects into dcceew.gov.au (observed in browser), so
  the portal's domain is covered by the DCCEEW instrument.
- DECISIVE: the register's own pages link their terms in the footer. Verified by fetching:
  - all-referrals list: `curl -A 'Mozilla/5.0' https://epbcpublicportal.environment.gov.au/all-referrals/`
    (336,501 bytes) contains `href="https://onlineservices.environment.gov.au/terms-and-conditions"`.
  - per-project page (2019/8566): `/all-referrals/project-referral-summary/?id=780a25c3-02ef-e911-b26f-005056842ad1`
    (223,247 bytes, 3.23 s, anonymous) carries the same footer link. (The 2026-10-28 session
    probed /terms-conditions/ on the portal host - 404 - and missed the footer link.)
- https://onlineservices.environment.gov.au/terms-and-conditions (44,808 bytes, plain fetch):
  "Subject to paragraph 2(b), you are prohibited from: reproducing Our Material; reselling or
  distributing Our Material; re-transmitting the Our Material by any medium of communication;
  uploading and/or reposting Our Material to any other site on the Internet" and
  "You may access and download Our Material from the Portal solely for your own use".
  Text search of the full page: no "Creative Commons" anywhere; the only IP licence section
  ("Licence to use Intellectual Property") is the Department's licence OVER USER-SUBMITTED
  material, not a grant to users.
- Verdict: both scope readings of the linked terms fail the redistribution contract - governed
  -> prohibited; not governed -> the register has no licence instrument at all. Class D with
  the clause quoted; see record.json licence_note/rejection_reason for reopen conditions.

### Population measurements (preserved for any reopening)

- Grid mechanics: rows load via `POST /_services/entity-grid-data.json/2ab10dab-d681-4911-b881-cc99413f07b6`
  with an opaque `base64SecureConfiguration` body (captured by hooking XHR in page context);
  offsets are inside the encrypted blob, so no plain-client pagination replay. Date filters +
  Apply Filter drive the same grid server-side and report true counts.
- Valid Date From/To + Apply Filter, reading the rendered "N records found":
  - 2000-01-01..2009-12-31 -> 3,403
  - 2010-01-01..2019-12-31 -> 3,067
  - 2020-01-01..2026-12-31 -> 1,826
  - 2019-01-01..2019-12-31 -> 177
  - unfiltered -> "5000 records found", pager 1..500 at 10 rows/page -> 5,000 is a display cap.
  - True register: 3,403 + 3,067 + 1,826 = 8,296 referrals since 2000.
- Filtered-row samples show the list's Project Status vocabulary: 'Referral Decision - Open
  for Public Comment' (open), 'Referral Decision Made', 'Advice Not Required', 'Approval
  Decision made', 'Condition variation being considered', 'Project Withdrawn'. The list says
  whether a decision exists / the referral was withdrawn (censoring flag), but NOT the
  controlled-action outcome; that lives in per-project 'Decision notices' XHR grids / PDFs.
- Per-project static page fetch: project 2019/8566 -> 223,247 bytes in 3.23 s, anonymous;
  renders stage timeline; the decisions grid itself is XHR.
- Export button on the list produced no download in one bounded attempt.

Scratch copies of fetched evidence (24h-pruned scratch, recipes above reproduce them):
/opt/data/cache/scratch/epbc/{all_referrals.html, botany_2019_8566.html, terms.html}.
