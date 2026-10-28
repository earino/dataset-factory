# ec-state-aid-investigation-opening

Opened 2026-10-28, EU/EEA regional tick. Channel discovery only - no data downloaded yet.

## What was probed

- data.europa.eu search for state-aid sources (2026-10-28): the EC's own register is
  republished as "EU Competition: State Aid case publications"
  (https://data.europa.eu/data/datasets/fa8d67be-d050-42a4-97ff-9e849805acf9~~1),
  JSON distribution, access rights public, created 2025-03-13, modified 2026-10-11;
  landing page https://competition-cases.ec.europa.eu/search. The publisher's
  description: records carry "standard fields such as Title; notification/registration
  date; legal basis; Aid instrument", coverage "starts in June 1993 (some cases) but
  more systematic publication began in the early 2000".
- DG COMP's own documentation (State aid Scoreboard annex, EUR-Lex CELEX:52008DC0304):
  "The Commission's State aid Register has been online since 2001... detailed
  information on all State aid cases which have been the object of a final Commission
  decision since 1st January 2000... updated daily."

## Next probe (recorded in record.json next_action)

1. Pull the JSON distribution URL from the portal record; bounded sample to measure
   per-case schema, per-year counts, and the Article 108(2) opening share.
2. Read the publisher's own reuse notice; classify licence A/B/C/D.
3. Novelty sweep for state-aid decision prediction (merger-decision prediction prior
   art exists; this target must be shown distinct).
4. Timing: registration-date instant vs decision dates; live-database vintage policy.

## Decision

investigating (hold). No licence claim made; nothing measured beyond the channel.
