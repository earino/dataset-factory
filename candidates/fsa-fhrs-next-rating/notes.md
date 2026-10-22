# fsa-fhrs-next-rating — probe notes

Discovery session 2026-10-22 (UK-regional tick). Scratch probes
(`.factory/probe_fsa_fhrs*.py`, `.factory/probe_fsa_defra*.py` shared with the
Defra candidate) deleted after the session.

## Licence triage (first)

- `ratings.food.gov.uk/terms-and-conditions` (HTTP 200, 2026-10-22): FHRS data
  is under the **Open Government Licence (OGL)** with the
  `nationalarchives.gov.uk/doc/open-government-licence/version/3/` link.
  `food.gov.uk/terms-and-conditions`: "under the Open Government Licence v3.0,
  except where otherwise stated."
- API help (`api.ratings.food.gov.uk/Help`): "no registration requirements ...
  No sign-up process, API keys, or login details are required."
- Class **A**. The reject below is on target derivability, not licence.

## Commands and results

1. `probe_fsa_fhrs1.py` — `ratings.food.gov.uk/open-data` lists **385
   per-authority XML files** (`OpenDataFiles/FHRS<id>en-GB.xml`); API
   `/Authorities` returns 363 authorities anonymously.
2. `probe_fsa_fhrs2.py` —
   - API help text: free programmatic access, no registration.
   - Working query `api.ratings.food.gov.uk/Establishments?name=cafe&pageSize=5`
     → establishment schema keys: AddressLine1-4, BusinessName, BusinessType,
     BusinessTypeID, ChangesByServerID, Distance, FHRSID,
     LocalAuthorityBusinessID, LocalAuthorityCode/Email/Name/WebSite,
     NewRatingPending, Phone, PostCode, RatingDate, RatingKey, RatingValue,
     RightToReply, SchemeType, geocode, scores. **No history fields.**
   - `FHRS760en-GB.xml` (Aberdeen City, FHIS): 2,062,982 bytes; Header
     `ExtractDate 2026-10-21`, `ItemCount 2222`; occurrences of
     `PreviousRating`: 0, `RatingHistory`: 0, `History`: 0, `Previous`: 0,
     `Scores`: 2222. Current-state snapshot only.
3. `probe_fsa_defra4.py` (FSA part) — terms-and-conditions page carries the OGL
   statement (OGL at char 38,337); `/terms` 404s; FSA has no dedicated open-data
   policy page (404).

## Verdict: reject (dropped)

The publisher exposes exactly **one current rating per establishment**. No
history in the API schema, no history elements in the XML extracts, and no
dated historical vintages of the extracts anywhere on the publisher's
instruments. Every prospective task on this stream needs ≥2 inspections per
establishment from obtainable data; only self-collection over years could
produce it, and self-collected labels cannot be verified against the
publisher's record. Secondary note: with history, the task would still be a
shape sibling of the published `chicago-food-inspections` dataset.

What would reopen: the FSA publishing per-establishment rating history or
dated snapshot vintages of the extracts. Recorded 2026-10-22.
