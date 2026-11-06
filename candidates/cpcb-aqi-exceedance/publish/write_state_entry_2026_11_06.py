#!/usr/bin/env python3
"""Prepend the 2026-11-06 10:45Z advancement-session entry to STATE.md."""
from pathlib import Path

ENTRY = """## 2026-11-06 (10:45Z) - advancement session: cpcb-aqi-exceedance PACKAGED (release/ assembled from digest-verified evidence, MANIFEST + check-package green first pass, ladder leading every document) and the GitHub destination of private staging COMPLETED AND VERIFIED (private repo earino/cpcb-aqi-exceedance, release 436366305 tag v2026.11, 5/5 assets server-side digest-equal to the MANIFEST, worker destroyed with 404 read-back); the consumer job, the Hub destination, DESTINATIONS.json and packaged_at/awaiting_operator remain

Scheduled advancement session. Release work first: no packaged candidate is
actionable (cqc, za-cct-substation, ns-bwa all awaiting_operator: true -
human waits, untouched). Zero non-terminal jobs in the ledger. Candidate
chosen from the operator's actionable list per its recorded next_action:
cpcb-aqi-exceedance, whose baseline verdict (HEADROOM DEMONSTRATED,
pre-registered rule, 2026-11-06 08:28Z entry) makes packaging the recorded
next step. No remediation hold is active.

- PACKAGING (dataset-release skill; commit 1222db7, CI green run 42202811159):
  release/cpcb-aqi-exceedance/ assembled by
  candidates/cpcb-aqi-exceedance/package/build_release_2026_11_06.py from
  digest-verified recorded bytes only - construction code copied after
  re-verifying the cpcb-aqi-build-004 bundle digests (build.py 4c10003f,
  run.sh 7f1e04e3, score.py 1ffefa53, all equal to the bytes worker job
  cpcb-aqi-build-004 executed at commit 75652fb, verified by git show);
  byte-pinned meta.json/quality.json equal to the accepted artifact
  a749f0df's five gate digests; qualification.json = the gate report itself
  (d2d367b6, 45/45 checks, failed_checks empty); the canonical gate 1.5.0
  (4fab8a34); benchmark runner files verbatim (bundled sha256 ==
  runner_files.json, unmodified: true); baseline_result.json = the collected
  cpcb-aqi-baseline-001 result (29eb43eb). measurements.json + all documents
  GENERATED from the record, the gate report, the baseline result and the
  references report - no figure retyped. The comparison ladder leads every
  document, README first: model 0.9734 beats station_persistence 0.9689
  (station-clustered paired bootstrap +0.0045, CI [+0.0038, +0.0052]),
  state_season_climatology 0.8617 (+0.1118, CI [+0.1002, +0.1252]) and the
  degenerate constant member (model AUC CI [0.9713, 0.9753] entirely above
  0.5) -> HEADROOM DEMONSTRATED under the pre-registered rule, eval 2023
  only, holdout sealed - with the persistence-carried structure of the label
  stated beside the number (persistence dominates climatology by +0.1073,
  CI [+0.0959, +0.1208]; the model's edge over persistence is real but
  small). Retrospective-research contract everywhere: current_snapshot
  vintage pin (exported_at 2026-09-30T11:25:11+00:00 + 196,521,834 rows
  asserted by the build), intraday latency unmeasured = declared assumption,
  D+1 observability rule never reads the label value, label source excluded
  from every shipped column, Delhi 2024-11-18 known-event fixture (36/36
  complete exceed, registry 39 matching the bulletin's own 36/39
  denominator) + monsoon 2023-08-15 negative control (389/1).
- LICENCE decision written (license.json, class A): GODL-India for the CPCB
  CAAQM measurements (data.gov.in platform instrument, Wayback-read
  2026-11-04 + AIKosh live corroboration; attribution template,
  non-endorsement, no warranty, no share-alike) and CC BY 4.0 for the XKDR
  compilation (requested credits carried verbatim: India Air Quality
  Database, XKDR Forum + CPCB CAAQM network + US DoS via AirNow); our code
  MIT, our derived compilation CC0-1.0, source terms preserved never
  relicensed, derived-data labelling throughout, the XKDR as-reported/no-gap-
  filling/preliminary caveat carried. release.json descriptor written
  (repository earino/cpcb-aqi-exceedance, v2026.11, construction commit
  75652fb). record.qualification + construction_output.splits (gate-report
  values cross-checked vs meta.json and baseline_result.json) +
  measurements.packaging_2026_11_06 recorded; status -> qualified.
  Checks: release-manifest.py wrote MANIFEST+SHA256SUMS (5 files, 88.8 MB,
  baseline present, licenses generated from license.json); check-package OK
  first pass; publish-dataset dry-run rc=0 with the standing caution recorded
  (--execute is the old public path); get_dataset.py compiles and its
  EXPECTED block equals expected_artifact.json exactly; reproduce_baseline.sh
  sh -n OK; no unreplaced template token in any document. meta.json fetched
  from staging as compact metadata (1,197 B, digest-verified); no bulk data
  through the coordinator.
- PRIVATE STAGING, GitHub destination (this session, after the packaging
  commit): private repo earino/cpcb-aqi-exceedance created; 25 package
  files pushed as the initial commit cb3b251; release v2026.11 (436366305)
  created non-draft at main; cpcb-aqi-publish-001 (release: true transfer
  job, server 174785899, cx23/hel1, EUR 0.04 reservation) copied the five
  accepted assets from staging release 436180445 into 436366305 under flat
  names - 5/5 transferred, failures [], every sha256 verified on arrival
  and server-side (asset ids resolved via publish-dataset.py --stream-test).
  Live authenticated read-back: repo private=true, release non-draft, tag
  v2026.11, exactly the five assets, every GitHub-reported digest equal to
  the MANIFEST (meta 1f59e74e, holdout 2dae0040, eval e187f645, train
  24b03a70, quality 98250e9d); anonymous API read-back correctly 404s
  (private). Worker destroyed 10:36:21Z, provider read-back 404. Job
  reports durable at staging release 436368409. EUR: 0.04 this job (~2.1 of
  the 15 EUR construction allowance in November; release reserve untouched,
  release jobs may draw on it).
- Hygiene: check-candidate cpcb OK after every record update; check-candidate
  --all rc=0; suite 723/723 OK (34.1 s); CI for the packaging commit 1222db7
  completed/success. candidates/fenz-incident-data/ left untracked for its
  owner. No release byte of any PUBLISHED package, no tag move, no
  destination visibility change anywhere; the holdout stays sealed; nothing
  public.

Next action (a fresh session can carry it out; also in record.next_action):
finish private staging - (1) the fresh-consumer worker job on the released
bytes (cqc consumer/source pattern, fetch block from release 436366305):
gate 1.5.0 re-run, exact-byte --accept a749f0df, baseline reproduce (both
AUC prints 0.9734, CONTRACT OK, quoted beside the triad), references
recomputed equal to measurements.json; (2) hf-publish.py --plan,
--create --upload-small, the hf_publish worker job, --verify, --tag LAST;
(3) release/cpcb-aqi-exceedance/DESTINATIONS.json both blocks (github done:
release 436366305, tag v2026.11, files_verified as a list; hub pending);
(4) record -> packaged with packaged_at + the structured artifacts[0] release
identity, awaiting_operator TRUE only after the pre-flip adversarial audit
prompt is generated from the frozen manifest; then check-candidate --all,
check-package, check-suitability, suite. The flip is the operator's single
approval and waits for the independent auditor's verdict unless waived. The
dvsa-mot-build-002 repair remains the next construction item on the
actionable list.

"""

path = Path("/opt/data/dataset-factory/STATE.md")
current = path.read_text()
assert "2026-11-06 (10:45Z)" not in current, "entry already present"
path.write_text(ENTRY + current)
print("STATE.md: 10:45Z advancement entry prepended "
      f"(now {len(current.splitlines()) + len(ENTRY.splitlines())} lines)")
