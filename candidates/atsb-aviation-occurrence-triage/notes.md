# atsb-aviation-occurrence-triage - row-level notes

Session: scheduled discovery, 2026-10-22 (Oceania tick). Verdict: **reject - access-blocked
+ purpose limitation** (licence class C, unopened; access vetoes first).

## Triage order

Access/terms triaged before any schema or volume probing. Total cost: one search, one
failed scripted HTTP fetch, one clean-page read.

## Commands and results

1. Discovery (search, 2026-10-22): surfaced
   https://www.atsb.gov.au/national-aviation-occurrence-database and the ATSB
   "downloading occurrence data instructions" page, quoting the 200-row export cap and
   "you cannot download the whole database".

2. Scripted fetch attempt (2026-10-22):
   `curl -sS -A "Mozilla/5.0 ..." https://www.atsb.gov.au/national-aviation-occurrence-database`
   -> `curl: (92) HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR`; zero bytes.
   Diagnosed as a scripted-client block; did not re-run unchanged.

3. Clean-client read of the same URL (web_extract, 2026-10-22) succeeded. Publisher's own
   words, first-hand:
   - "The ATSB dashboard allows for up to 200 rows of data to be downloaded from the
     database."
   - "Can I download the whole database? No, unfortunately you cannot download the entire
     database. The ATSB limits the full export of the National Aviation Occurrence
     Database, which has been made available for general statistical purposes only."
   - "The ATSB also does not endorse the use of its aviation occurrence data for any
     commercial purposes."
   - "The ATSB does not endorse, and disclaims any responsibility for, use of the data
     beyond general statistical purposes."
   - Coverage: occurrences reported since 1 July 2003. The ATSB also documents that
     ingestion lags weeks, data is "subject to change", and the Oct-2014 taxonomy change
     reclassified some incident types.
   - The dashboard itself is at https://dashboards.atsb.gov.au/ behind a
     click-through acknowledgement of the above limitations.

## Why this is a rejection

- No bulk channel: a panel of reported occurrences (~two decades, tens of thousands of
  rows) cannot be assembled from 200-row manual exports.
- Purpose limitation: the publisher states availability "for general statistical purposes
  only" and disclaims use beyond that - a published ML benchmark is not what the terms
  permit, and republishing derived rows is the bulk export the cap prevents.
- Under the standing policy (2026-10-21: only build on sources that are already clean),
  a source that must be negotiated with is closed, not parked.

## Task it would have supported (recorded so the lead is not re-derived)

Notification-time triage classification: predict whether a reported occurrence will be
classified accident/serious-incident vs incident, using only notification-era fields.
The bench's closest existing family is faa-wildlife-strike-damage (US, different label
and data). The ATSB taxonomy change (Oct 2014) would have been a documented structural
break to respect in splits. Never probed - access veto came first.

## What would reopen it

A bulk occurrence extract under an open licence, e.g. a CC BY dataset on data.gov.au.
data.gov.au was searched only via the general web index this session; no ATSB bulk
dataset surfaced there. If one appears, re-vet as a new source with its own licence
evidence.
