# Temporal availability: proving a feature existed at the prediction instant

Use when a dataset, model or report is built from a **statistical release** - a publisher that emits
a period's data after the period closes - and the task claims to predict at that period boundary.

The defect is silent, survives every leakage check, and is invisible in the artifact: the feature is
labelled month M, the label says "predict at the end of month M", and the values behind the feature
were published on day 10 of month M+1. Nothing in the rows contradicts the claim, because the claim
is about a calendar that the artifact does not carry.

## The declaration

A free-text or token field (`features_documented_at: "prediction_time"`) cannot express this and
grades vocabulary rather than fact. Require a structured block:

```json
"timing": {
  "prediction_instant": {"kind": "publication", "period": "M",
                         "days_after_period_end": 10, "citation": "<release calendar URL>"},
  "features": {"period": "M", "published_days_after_period_end": 10,
               "source_kind": "statistical_release"},
  "row_selection": {"latest_period_used": "M", "fields": ["..."], "basis": "..."},
  "observations": [{"period": "YYYY-MM", "period_end": "YYYY-MM-DD", "published": "YYYY-MM-DD"}]
}
```

- `kind` is `publication`, `period_end` or `event_time`.
- `observations` are **observed release dates**, not the schedule the producer assumed. One real
  `period_end -> published` pair is worth more than a paragraph of prose and is the only thing that
  can make an understated lag fail. Record at least three when you can: publication slips, so a
  source that landed 9, 13 and 10 days after three consecutive period ends has no single lag, and
  the **mean reads one of those months three days before it existed**. Set the lag to the largest
  observation and say in the record that the maximum, not the average, is what the instant uses.
- `latest_period_used` catches the second defect: eligibility computed over the whole snapshot
  (a total-history count, a target-month volume filter) conditions the population on the future even
  when every feature is clean. `M+1` here is a failure; `M` is a pass.

## The checks

| Check | Fails when |
| --- | --- |
| `instant_declared` | no block, no `kind`, or no citation - absence is the state that ships the defect |
| `publication_lag_measured` | a statistical release ships no usable observation, or an observation's `published` precedes `period_end` |
| `features_available_at_instant` | `features.published_days_after_period_end > instant.days_after_period_end` |
| `instant_accounts_for_publication_lag` | feature lag > 0 while `kind` is not `publication` |
| `selection_uses_only_available_data` | `latest_period_used` contains a forward offset (`M+1`, `+N`) or is empty |

The arithmetic is the point: a period-end instant has lag 0, so any late-published feature fails
without anyone having to judge intent. Report the measured lag from the observations in the check's
evidence so an auditor can see the number the verdict came from.

## Source kinds decide what evidence is required

| `source_kind` | Meaning | Observation rule |
| --- | --- | --- |
| `statistical_release` | published after the period closes: health statistics, labour figures, monthly regulator returns | at least one observed `period_end -> published` pair; lag normally > 0 |
| `administrative_record` | created at the event: a citation issued at an inspection, a call closed at dispatch | no observation needed; lag 0 is honest |
| `event_time` instant | each row is predicted at its own event date | pairs with `administrative_record` |

Without this distinction the rule is either vacuous (everything declares lag 0) or unusable
(administrative datasets must fabricate observations to pass). Encode the distinction in the
declaration, not in a comment.

## Migrating a gate that gains a required block

1. **Do not make it optional to keep old artifacts green.** An optional block reproduces exactly the
   defect the check exists for. Absence must fail.
2. **Update every producer in the same change**: each per-instance build script that writes the
descriptor, plus the offline fixtures, which get a synthetic block stating what is true of synthetic
data (lag 0, `administrative_record` or `event_time`).
3. **Expect the full suite to fail in ways that look unrelated.** A required field surfaces as gate
   failures inside build tests, and a test that formats its failure message can crash while reporting
   it (`AttributeError: 'Report' object has no attribute 'failed_checks'`) and hide the real reason.
   Give the result object the accessor its reporters expect before reading anything into the red.
4. **Leave old published artifacts alone.** Their bytes are fixed; record the gap where their
   verification lives and let a rebuild carry the block. Do not patch a published descriptor in
   place - that moves the artifact version and invalidates its acceptance.

## Proving a timing check is load-bearing

A new check that has only ever been run against a fixed artifact proves nothing. Keep the fixed gate
aside, restore the previous one from history, and run the new tests against it:

```bash
cp <gate>.py /tmp/gate_fixed.py
git checkout HEAD -- <gate>.py      # the version before the change
python -m unittest tests.test_timing_gate   # expect errors/failures naming the missing checks
cp /tmp/gate_fixed.py <gate>.py
python -m unittest tests.test_timing_gate   # expect green
```

On the pre-fix gate the tests fail with a missing check name (the check does not exist), which is the
correct evidence: the tests bind to the check by name, so an absent check cannot pass silently.

## What this does not prove

The gate reads declarations; it does not read the producer's code. A build that declares
`latest_period_used: M` while filtering on `M+1` passes every check above. Pair the declaration with
an audit that reads the selection code (see `references/auditing-a-released-benchmark.md`) - the
declaration makes lying explicit and auditable, and the audit is what converts auditable into true.

Two code shapes to look for when you read that selection, because both pass every declaration
check while conditioning the population on the future:

- **The pair loop.** `for i, key in enumerate(keys): target = keys[i + 1]` builds membership from
  consecutive *qualifying* periods, so a later period below the volume gate deletes the earlier row.
  Fix it by iterating the periods and looking the target up afterwards, solely for the label; count
  an absent target separately (`unobserved_target`) instead of letting it decide membership.
- **The whole-snapshot aggregate.** A provider-level count over the entire panel ("at least N months
  of history") awards early months history that only exists later. Count at or before the instant.

Prove both with one counterfactual rather than a description: take a shipped row, change **only** a
future-period value, re-run the selection, and assert the row survives; then change a history-period
value and assert it disappears. A test that only asserts the corrected output proves the arithmetic,
not the order of operations.
