# Ephemeral worker cycle report

Every value below must come from a tool call. Leave nothing inferred.

## Required fields

- **Job / server / resource IDs** - the project's job id, then the provider's ids for every
  resource created (server, IP, volume, snapshot).
- **Artifact links** - the durable URL(s) where the artifacts landed, plus how many there were and
  what was actually verified about them (size and digest against the producer's own manifest).
- **Reservation** - the planned figure and the rate ceiling it came from, exactly as the plan
  reported it.
- **Estimated cost** - the real figure: how long the machine actually lived, and the provider's
  rounding (usually whole hours). Give both and label which one is the ceiling.
- **Deletion confirmation** - the method (provider API, not the project ledger), the counts observed
  before and after, and the timestamp.

## Shape

Labelled lines or bullets per step, in execution order, each carrying its evidence. Then two short
closing notes:

1. what is now enabled or disabled, with the flag read back;
2. what this cycle did **not** verify - named plainly.

## Do not

- Do not lead with the verdict ahead of the identifiers; the reader checks the ids first.
- Do not present the project ledger's word for deletion as confirmation.
- Do not call the cycle complete while any step was inferred rather than observed.
- Do not soften a limitation into a closing aside; an open item belongs at the same level of detail
  as the successes.
