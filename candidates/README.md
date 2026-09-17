# Candidate records

Create a record with `python3 -m factory candidate create <short-id>`.
Each candidate has `record.json`, dated research notes, and eventually a
construction script. Keep data and large logs out of this repository.

For each source, record its URL, access date, license evidence, publication date
where known, and raw download checksum once acquired. Record a concrete prediction
time and target definition before evaluating the candidate.

Suggested states: `investigating`, `constructing`, `screened`, `awaiting_review`,
`rejected`, `published`. State changes need supporting notes and measurements;
the tracking helper does not qualify datasets or approve publication.
