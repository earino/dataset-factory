# Evidence findings — first pass (2026-11-07)

Source: `STATE.md` (290 session entries, 2026-09-17 to 2026-11-07), `audits/`, GitHub
issues and PRs, candidate records, and `jobs/*.json`. Six LLM extraction passes produced
the event records; `merge_defects.py` merges and tiers them; `tables.py` computes
`TABLES.md`. All counts below come from those files. They are extractions, not
hand-verified ground truth: each event has a `confidence` field and cites its evidence.

## Counts

- 567 extracted events -> 514 after merging duplicates. 491 analysed after excluding
  15 false alarms, 7 routine licence-triage drops and 1 umbrella record.
- 175 of 491 defects were detected only after qualification (private-staged or public);
  58 after the dataset was public.
- Worker jobs: 220 jobs, 144 succeeded / 69 failed / 7 no result; about 132 worker-hours;
  about EUR 7 of server time (estimate, `jobs_summary.txt`). Model cost: Hermes is a flat
  20/month on Nous cloud, shared with other agents (`../OPERATOR-NOTES.md`). Codex cost unknown.

## Finding 1 — the layers catch different defects at different stages

Validity defects (leakage, prediction timing, label definition, splits, units; n=85):

| caught by | before build | built | qualified | staged private | public |
|---|---|---|---|---|---|
| agent self-check | 29 | 2 | 1 | 2 | 0 |
| Codex audit | 2 | 3 | 2 | 14 | 11 |
| qualification gate | 1 | 1 | 0 | 0 | 1 |
| worker guard | 0 | 3 | 0 | 0 | 0 |
| CI | 0 | 0 | 0 | 0 | 1 |
| unknown | 1 | 2 | 2 | 5 | 2 |

- The agent catches its own validity defects early (29 of 34 before any build).
- The independent auditor caught 25 of the 36 validity defects detected after
  qualification (columns "staged private" + "public"; the other 11: 7 unknown,
  2 agent self-check, 1 gate, 1 CI).
- The mechanical qualification gate caught 3. It checks structure; the escaped defects were
  semantic (reverse-history joins, row presence, outcome-conditioned selection,
  publication lag).
- Validity defects reached the public in 10 datasets: abs, austin, chicago-doah,
  chicago-food, eutl, msha, my-pricecatcher, noaa, pins, who-flunet.

## Finding 2 — "every prior gate check passes on broken data"

The 2026-10-24 static leakage audit (`audits/2026-10-24-static-benchmark-leakage-audit.md`)
found 7 of 10 public releases fail as unrestricted static benchmarks; in six, a blind join
recovers labels exactly. All had passed the gate. Same pattern later: nz-ea (eval AUC 1.0,
gate 34/34), chilecompra (outcome-conditioned selection, gate 38/38), ocha-fts (gate green,
auditor recovers 120/139 eval labels), ns-bwa (gate measured 56 eval rows exposed; auditor
recovered 196/372). The gate was strengthened after each (1.3 -> 1.4 timing block -> 1.5
cross-row probes), and the auditor still found more.

## Finding 3 — checks that agree with each other can all be wrong

- chicago-food: the wrong `materialize.py` was hashed into the manifest; every byte check
  passed; only the fresh-environment consumer job caught it.
- ec-merger: after corrections, MANIFEST still described superseded files; `check-package`
  passed because it does not re-hash them; an ad-hoc `sha256sum -c` caught it.
- unhcr: the gate measured the exact exposure the auditor later found, and the package still
  claimed an "enforced isolated-rows protocol" that `validate.py` does not enforce.

## Finding 4 — the agent's statements about its own process are not reliable

Repeated hand-copied sha256 errors (nz-ea 2026-10-23, cpcb 2026-11-06) after the agent
recorded that digests were "never hand-copied"; false close-out claims ("release
non-draft", "worker destroyed"); a resumed probe that miscounted rows into a "ready" record
(cpcb). Each was caught by a mechanical check on the worker, not by the agent.

## Finding 5 — real sources break in stacked, unforeseeable ways

dvsa-mot: undocumented ABRVE values (2015), Deflate64 zips (2017), macOS `__MACOSX/` junk
members (2018) — each visible only after the previous fix. cqc: README sheet -> leap-year
off-by-one -> untested fixture path. Synthetic dry runs passed in both and caught none of
these. Fail-loud construction on real data caught all of them.

## Finding 6 — the human gate as practised

- Operator-held decisions: the private-to-public flip, licence risk acceptance,
  drop/reopen, commissioning audits, scope corrections, budget limits.
- Operator's stated reason for keeping audit review manual: learning where the agent fails
  in order to fix it (`../OPERATOR-NOTES.md`).
- The operator directly detected 11 defects but was involved in 115 of 491 events.
- Approval did not always precede the act:
  - msha went public on 2026-10-19 with no prior approval; ratified 2026-10-20 ("it stays
    public") together with a standing publication authority. `docs/OPERATIONS.md` says
    that authority does not cover the flip — the rules disagree.
  - who-flunet: the agent blocked the flip on WHO's licence terms; the operator said
    "ship it" (2026-10-21), recorded as risk acceptance with NOASSERTION and a takedown route.
  - "flip it when it was ready" (ec-merger) and "flip everything you can based on this"
    (ipo, pins) were read by the agent as waivers of the audit verdict.
- Scope drift: the operator stopped Codex-led remediation from expanding into adapter
  infrastructure ("going off the rails"); deferred to issue #25.

Flip timeline: `audit_verdicts.jsonl` and `operator-events.jsonl`.

## Auditor accuracy — not yet measurable

34 verdict rows (`audit_verdicts.jsonl`). Later confirmation with cited evidence exists for
the nhs-ae, unhcr, ipo, pins and tw-typhoon findings. The catalog FAIL rows, nz-ea, ns-bwa
and ocha-fts were adopted and acted on but never independently reproduced. Disputed:
tw-typhoon novelty (agent maintains the prior repo is a different task); pins leakage
(auditor: bounded PASS; gate probe: `recovery_demonstrated`).

## Open items

1. Reproduce the auditor's blind-join recoveries on the public bytes (a worker job), so the
   auditor's precision is measured rather than assumed.
2. cpcb-aqi-exceedance is staged with `awaiting_operator=true` while its suitability record
   says `cross_row_audit.status = recovery_demonstrated`. The pre-flip audit prompt says a
   demonstrated recovery on shipped bytes is an automatic DO NOT PUBLISH. Unruled conflict.
3. RESOLVED 2026-11-07: commits on 2026-10-22..24 under the operator's git identity were authored by Codex, directed and approved by the operator (`../OPERATOR-NOTES.md`). Still open: the 6 commits on
   2026-09-17..19 under the same identity, including the Austin `response_time` leak fix
   (the "builder review") and its revert.
4. Deduplication across chunks is approximate (exact candidate + class + detector match
   for audit events; an explicit list for STATE.md chunks). Some nhs-ae timing events
   still appear twice under different detectors.
5. 39 events have `detected_by = unknown`, mostly the 2026-09-18 "builder review" and
   2026-10-22..24 hardening work.
6. Record the date Codex audit checks become automated (see `../OPERATOR-NOTES.md`).
