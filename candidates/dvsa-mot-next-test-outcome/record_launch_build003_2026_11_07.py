"""Record the dvsa-mot-build-003 Deflate64 repair + launch (advancement 2026-11-07).

Appends the launch receipt to jobs[], a dated measurement describing the
pre-launch red/green dry run on REAL Deflate64 bytes, and rewrites
next_action to the running-state handoff. No score has ever existed for
this candidate; the pre-registered triad and deciding rule are untouched.
"""
import json
from pathlib import Path

REC = Path("candidates/dvsa-mot-next-test-outcome/record.json")
r = json.loads(REC.read_text())

# --- jobs[]: the launch receipt ---
launch = {
    "job_id": "dvsa-mot-build-003",
    "server_id": 174954439,
    "server_type": "cpx32",
    "location": "hel1",
    "launched_at": "2026-11-07T09:02:28Z",
    "status_at_record_write": "running",
    "ipv4": "2.29.159.168",
    "reservation_eur": "0.32",
    "provider_hourly_eur": "0.0692400000000000",
    "budget_month": "2026-11",
    "what": (
        "Repair relaunch of the failed dvsa-mot-build-002 per the recorded "
        "next_action: exactly two changes, both construction-side, before "
        "any score. (1) build.py open_text_lines routes compress_type 9 "
        "(Deflate64) zip members through the explicit local-header read "
        "(_member_blob) + inflate64.Inflater().inflate decode verified "
        "in-container on the real 2017 file (measurements."
        "deflate64_decode_verified_2026_11_07), streaming lines through "
        "TextIOWrapper one at a time - never splitlines on a full member "
        "(the first verification attempt's OOM was the probe's own "
        "splitlines, not the decode); stdlib zipfile still reads the "
        "central directories and standard-deflate members like the pinned "
        "2024 zip; the import is conditional so the coordinator dry run "
        "runs without the package, and main() fails fast in non-test mode "
        "BEFORE any download if inflate64 is missing. (2) run.sh installs "
        "the pinned inflate64==1.0.4 and verifies the import before "
        "build.py. The ABRVE value-rule repair from build-002 is unchanged; "
        "label rule, pre-registered triad and deciding rule untouched. "
        "max_artifact_mb stays 200."
    ),
}
assert r["jobs"], "record must carry prior jobs"
assert r["jobs"][-1].get("job_id") == "dvsa-mot-build-002", "unexpected tail job"
r["jobs"].append(launch)

# --- measurements: the pre-launch red/green dry run on real Deflate64 bytes ---
r["measurements"]["deflate64_dryrun_2026_11_07"] = (
    "MEASURED on the coordinator before relaunch (probe/"
    "dryrun_deflate64_2026_11_07.py, committed; scratch venv "
    "python3.13 + the pinned inflate64==1.0.4, the same version run.sh "
    "installs): RED-A - the build-001 source (git be68bfd) exits 1 on the "
    "injected ABRVE row with the recorded assertion, so the value-rule "
    "repair is intact. RED-D - the build-002 source (git 5dc4b61) raises "
    "stdlib zipfile's NotImplementedError on a compress_type 9 member, "
    "the exact failure class that killed build-002 at 2017. GREEN-D - the "
    "patched open_text_lines round-trips a known-plaintext zip built with "
    "inflate64's own Deflater in the measured 2017 member shape "
    "(pipe-delimited header, \\r\\n ends, two members) EXACTLY, and on the "
    "inflate64 project's own tests/data/test-file.zip (another producer's "
    "container, downloaded from its PyPI sdist at dry-run time) every "
    "member's blob read equals the central directory's compress_size and "
    "its one-shot inflate equals file_size. GREEN-S - the patched build on "
    "the stdlib fixtures exits 0 with all ABRVE checks holding. "
    "GREEN-FULL - with fixture years 2017-2023 re-encoded as real "
    "Deflate64 zips (byte-identical member content), the full build "
    "reproduces the stdlib-route extract byte-for-byte (train/eval/holdout "
    "CSVs, meta.json, quality.json) with equal per-year population "
    "counters and pair counters. GATE - qualify_dataset.py gate 1.5.0 "
    "passes on BOTH synthetic extracts and exact-byte --accept accepts "
    "both, with the post-acceptance triad machinery exit 0 (eval only), "
    "in the run.sh stage order. Fixture numbers are NOT findings and are "
    "never quoted as task evidence; this entry exists to show the repair "
    "changes construction behaviour only where the failure evidence said "
    "it must, and that the route works on real Deflate64 bytes produced "
    "by an implementation other than the one that will decode the real "
    "DfT files (cross-implementation: Deflater-written, Inflater-read)."
)

# --- next_action: the running-state handoff ---
r["next_action"] = (
    "dvsa-mot-build-003 RUNNING on worker 174954439 (cpx32, hel1, launched "
    "2026-11-07T09:02:28Z, reservation 0.32 EUR, budget month 2026-11; this "
    "is the relaunch for the Deflate64 container defect that killed "
    "build-002 at the 2017 zip - the ABRVE value repair is already PROVEN "
    "on real data and the Deflate64 route is verified in-container AND "
    "dry-run verified on real Deflate64 bytes; a failed build-003 at the "
    "same zip stage is a task-design question, not another retry). "
    "Expected upload: /output summary.json, "
    "qualification-dvsa-mot-next-test-outcome.json (+ .txt), acceptance "
    ".txt, references .json, container.log, source.tar. ON COMPLETION: "
    "(1) sh scripts/scout-factory worker collect dvsa-mot-build-003; "
    "(2) DETERMINISTIC CROSS-CHECK (required before any figure is "
    "quoted): run probe/fetch_diagnostics_build003_2026_11_07.py "
    "(bounded staged diagnostics fetch, never the bulk extract), then "
    "probe/verify_crosscheck_build003_2026_11_07.py - the collected "
    "summary.json population.per_year rows_seen / class4_rows / "
    "sampled_rows for 2005-2014 must reproduce build-001's recorded "
    "receipts EXACTLY (10/10) and 2015-2016 build-002's recorded "
    "receipts EXACTLY (2015 37,490,736/35,445,915/35,591; 2016 "
    "37,693,380/35,637,088/35,626), and the 2017-2024 zip-era receipts + "
    "non-completed inventories are read as NEW evidence (never previously "
    "observable); (3) require gate 1.5.0 PASSED on the FULL artifact + "
    "exact-byte --accept in the collected bytes BEFORE any AUC, base "
    "rate or headroom figure is quoted; (4) record the post-acceptance "
    "reference triad (persistence_prior_result / calendar_make_week / "
    "vehicle_train_rate + supplementary) beside the artifact identity, "
    "eval only, holdout sealed; (5) destroy the worker with provider 404 "
    "read-back; (6) then the dvsa-mot-baseline bundle (assembled from "
    "candidates/dvsa-mot-next-test-outcome/baseline; fill its fetch block "
    "with baseline/make_fetch_2026_11_07.py): fetch the accepted extract "
    "from staging, RE-ACCEPT the collected qualification.json against the "
    "bytes before any score, harness runner verbatim, the pre-registered "
    "deciding check vs EVERY triad member, cluster = vehicle_id, eval "
    "2019-2021 only. A failed build or gate stops everything and is "
    "recorded as a finding with diagnosis before any further launch."
)

REC.write_text(json.dumps(r, indent=1) + "\n")
print("recorded dvsa-mot-build-003 launch; jobs:", len(r["jobs"]))
