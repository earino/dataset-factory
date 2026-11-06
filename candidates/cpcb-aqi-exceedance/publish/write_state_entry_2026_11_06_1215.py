#!/usr/bin/env python3
"""Prepend the 2026-11-06 12:15Z advancement-session entry to STATE.md."""
from pathlib import Path

ENTRY = """## 2026-11-06 (12:15Z) - advancement session: cpcb-aqi-exceedance fresh-consumer job LAUNCHED and RUNNING on the released bytes (with the deciding check recomputed beyond the cqc pattern), and the whole Hugging Face destination PREPARED and PLANNED (card.md + cpcb-aqi-hf-001 job source); Hub upload waits for the consumer green

Scheduled advancement session, release work first. cqc, za-cct-substation
and ns-bwa all carry awaiting_operator: true (human waits, untouched); the
operator's actionable list named cpcb-aqi-exceedance at stage (package) and
its record's next_action had the consumer job as step (1) of the remaining
release sequence. No remediation hold is active. Nothing public was touched.

- CONSUMER JOB (the session's primary step, per the record's next_action):
  candidates/cpcb-aqi-exceedance/consumer/source/ written and assembled as
  bundle cpcb-aqi-consumer -> .factory/jobs/cpcb-aqi-consumer-001. The fetch
  block names the five assets of the private release 436366305 by asset id
  resolved through the live release API with sizes equal to MANIFEST.json
  (716781985/716782078/716782178/716782327/716782494; digests from the
  manifest, never hand-copied). Scope = every published REPRODUCE.md step
  against the released bytes - package-vs-MANIFEST (24 files),
  get_dataset.py re-verification, sha256sum -c, gate 1.5.0 re-run on the
  FULL artifact, exact-byte --accept (a749f0df), declared imports, baseline
  reproduce (both AUC prints 0.9734, CONTRACT OK, holdout-never-copied
  marker), score.py references recomputed equal to measurements.json - PLUS
  one step beyond the cqc pattern the package itself demands: REPRODUCE.md
  states "recomputation must reproduce model-minus-persistence [0.0038,
  0.0052] and model-minus-climatology [0.1002, 0.1252]", so the job also
  recomputes the pre-registered deciding check on the released bytes through
  the SHIPPED baseline/train.py + code/score.py (seeded bootstraps,
  deterministic), checking the model-minus-member CIs, the model AUC CI
  above 0.5 and the headroom_demonstrated verdict. The optional
  rebuild-from-export step is not run (build.py refuses any changed export;
  REPRODUCE.md documents it as optional). Gate runs BEFORE any figure;
  score.py refuses to run without the accepted report; holdout fetched for
  hashing only, never scored.
- The two comparison scripts were self-tested locally BEFORE launch:
  check_references.py positive (15 figures/row counts equal) and negative
  (a perturbed AUC is caught) both behave; decide_check.py is
  worker-container-only (score.py/pandas imports) and its comparison logic
  was reviewed against the recorded comparison block.
- LAUNCHED 2026-11-06T11:54:20Z: worker 174799070 (cpx32/hel1, 4 vCPU,
  8192 MB, reservation EUR 0.32, release: true so it may spend the reserve;
  construction ledger untouched at ~2.1/15). Status running at the run-time
  budget stop (~12:10Z, ~16 min in; the same work took 1043 s in
  cpcb-aqi-baseline-001, so ~25-40 min expected with the extra bootstraps).
  THE RUNNING JOB IS THE HANDOFF: acceptance = collect, exit 0, and
  consumer.txt showing every step green (details in record.next_action);
  on failure keep the reports and diagnose before any retry.
- HF DESTINATION PREPARED AND PLANNED (executed: nothing): card.md written
  for cpcb (front matter license_name
  godl-india-1.0-and-cc-by-4.0-source-plus-cc0-compilation; the ladder and
  the persistence-carried-structure limitation lead the card; placeholders
  only from hf-publish's substitution set) - hf-publish.py --plan --candidate
  cpcb-aqi-exceedance green and tests/test_hf_card.py 7/7 OK.
  candidates/cpcb-aqi-exceedance/hf/job.json (cpcb-aqi-hf-001) written with
  the hf_publish block (same five assets, data/ targets, verify_loading =
  the manifest's splits/rows/positives/columns/label) and planned OK:
  reservation EUR 0.04, FACTORY_HF_WRITE_TOKEN_FILE resolved at plan time
  (credential read as a file, never echoed, never in a bundle/mount), 0
  cloud calls. NOT launched: one worker at a time, and the recorded order is
  consumer-green first.
- Hygiene: check-candidate cpcb-aqi-exceedance OK after the record update;
  untracked candidates/fenz-incident-data/ is another session's work and was
  not touched or committed; no bulk data through the coordinator (asset
  metadata only); no token exposure; holdout sealed; no tag moved; nothing
  public. November worker ledger after this session: ~4.68 EUR reserved of
  the 20 EUR ceiling, the 5 EUR release reserve untouched by construction.

Next action (a fresh session can carry it out): the record's next_action is
authoritative and carries the full sequence with acceptance criteria:
(1) collect cpcb-aqi-consumer-001 (running, worker 174799070), verify
consumer.txt green, destroy the worker, provider 404 read-back;
(2) hf-publish.py --create --upload-small, then plan+launch
cpcb-aqi-hf-001 (already written and planned), collect + destroy;
(3) hf-publish.py --verify (exit 0, --worker-job cpcb-aqi-hf-001) then
--tag LAST (v2026.11 == main);
(4) release/cpcb-aqi-exceedance/DESTINATIONS.json both blocks;
(5) record -> packaged (packaged_at + structured release identity),
generate the pre-flip adversarial audit prompt from the frozen manifest,
then awaiting_operator true;
(6) check-candidate --all, check-package, check-suitability, suite,
commit/push, CI for that exact commit. The flip remains the operator's
single approval and waits for the independent auditor's verdict unless
waived.
"""

path = Path("STATE.md")
text = path.read_text()
path.write_text(ENTRY + "\n" + text)
print("STATE.md entry prepended:", len(ENTRY), "chars")
