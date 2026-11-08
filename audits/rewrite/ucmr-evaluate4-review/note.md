UCMR build-8 fresh semantic review (rw-2ce60e8ae8f7-evaluate-4, completed
20:17:34Z; observed end to end, no manual state edits).

Outcome: verdict "repair" - NARROWER than evaluate-2 (5 findings -> 2).
The reason affirms the core construction as largely consistent: target
direction and units, entry-point population, one-row-per-public-water-
system selection, exact event-key additional-data join, chronological
half-open windows, and the independent label audit.

Remaining findings:
0. Missing CollectionDate exclusions are not counted, contrary to the
   stated population rule.
1. The source construction recipe still specifies a three-key
   additional-data join, while the code uses the exact sample-event key
   join (recipe text stale; the code's join is the affirmed one).

Usage: 5 calls, 82,945 in / 64,485 out, 7 web tool results, 382.6 s.

Tick routed the candidate back to build (status "repair", stage build,
attempt rw-2ce60e8ae8f7-evaluate-4) with findings retained; the next
ordinary step is build-9's bounded repair construction. Both remaining
findings are documentation/recipe-consistency corrections, not
construction-code defects per the review's own affirmation.
