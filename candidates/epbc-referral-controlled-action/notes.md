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
