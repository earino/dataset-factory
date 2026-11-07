"""Record the dvsa-mot-build-003 outcome + dvsa-mot-build-004 launch (2026-11-07).

build-003 PROVED the Deflate64 repair on the real 2017 DfT zip (first zip-era
year ever parsed) and then failed at a NEW defect: the 2018 zip's macOS
__MACOSX/ AppleDouble junk members. This records the failure measurement,
the macOS-skip repair + extended dry run, and the build-004 launch. No score
has ever existed for this candidate; the pre-registered triad and deciding
rule are untouched.
"""
import json
from pathlib import Path

REC = Path("candidates/dvsa-mot-next-test-outcome/record.json")
r = json.loads(REC.read_text())

# --- jobs[]: the build-003 failure receipt + the build-004 launch receipt ---
failure = {
    "job_id": "dvsa-mot-build-003",
    "server_id": 174954439,
    "launched_at": "2026-11-07T09:02:28Z",
    "collected_at": "2026-11-07T09:45:23Z",
    "deleted_at": "2026-11-07T09:46:06Z",
    "status": "failed",
    "exit_code": 1,
    "staging_release_id": 437475493,
    "cleanup_verified": ("provider read-back: GET /servers/174954439 -> 404; "
                         "scripts/provider-inventory.py reports 0 servers, "
                         "0 primary_ips in the account"),
    "what": (
        "Deflate64 repair relaunch. OUTCOME: the repair is PROVEN on the "
        "real files - the build parsed the 2017 DfT zip (the member class "
        "that killed build-002) cleanly through the local-header + "
        "inflate64 route: 2017 rows_seen=38,056,161 / class4=35,983,938 / "
        "sampled=35,975, with 2015 (ABRVE=242) and 2016 (ABRVE=27) "
        "receipts reproduced EXACTLY as recorded. NEW DEFECT at 2018: the "
        "2018 zip's first member is "
        "__MACOSX/._dft_test_result-from-2018-01-01_00-00-01-to-2018-04-01_"
        "00-00-01.csv - a macOS AppleDouble resource fork whose bytes "
        "cannot map to the CSV schema (collected container.log). The real "
        "2018 members are quarterly-range named "
        "(dft_test_result-from-YYYY-MM-DD...-to-...csv), unlike 2017's "
        "monthly test_result_YYYYMM names - a measured source property. "
        "This is a distinct, smaller defect than the one the rebuild was "
        "spent on; no extract, no gate, no acceptance, no score exists."
    ),
}
launch = {
    "job_id": "dvsa-mot-build-004",
    "server_id": 174959633,
    "server_type": "cpx32",
    "location": "hel1",
    "launched_at": "2026-11-07T09:49:48Z",
    "status_at_record_write": "running",
    "ipv4": "2.29.159.168",
    "reservation_eur": "0.32",
    "provider_hourly_eur": "0.0692400000000000",
    "budget_month": "2026-11",
    "what": (
        "macOS junk-member repair relaunch: exactly one construction "
        "change vs build-003 - open_text_lines skips __MACOSX/ and "
        "._-prefixed members before any decode (documented macOS zip "
        "artifacts, measured in the real 2018 DfT zip); every other "
        "unexpected member still fails loudly at schema mapping. The "
        "Deflate64 route, ABRVE value rule, label rule, pre-registered "
        "triad and deciding rule unchanged. The dry run was extended with "
        "RED-M/GREEN-M legs and is fully green before this launch."
    ),
}
assert r["jobs"][-1].get("job_id") == "dvsa-mot-build-003", "unexpected tail job"
r["jobs"][-1].update(failure)
r["jobs"].append(launch)

# --- measurements: the 003 outcome (real-data proof + new defect) ---
r["measurements"]["build_failure_2018_macosx_2026_11_07"] = (
    "MEASURED on the dvsa-mot-build-003 worker (server 174954439; collected "
    "container.log digest-verified from staging release 437475493): (1) the "
    "DEFLATE64 REPAIR IS PROVEN ON REAL DATA - 2005-2016 receipts reproduce "
    "the recorded chain EXACTLY (2005-2014 == build-001's log 10/10; 2015 "
    "37,490,736/35,445,915/35,591 with ABRVE=242; 2016 "
    "37,693,380/35,637,088/35,626 with ABRVE=27 == build-002's log), and "
    "2017 - the Deflate64 zip that raised NotImplementedError and killed "
    "build-002 at this exact member class - parsed cleanly: rows_seen="
    "38,056,161 / class4=35,983,938 / sampled=35,975, results P=27,296,486 "
    "F=7,991,182 PRS=2,533,016 ABR=210,521 ABA=24,928 ABRVE=28 (the first "
    "zip-era year ever parsed; the first ABRVE rows ever observed in a "
    "zip-era year). Parse pace measured mid-run: ~141 s/year for the txt.gz "
    "era, 2005-2015 complete in ~34 min - the 100-minute job timeout was "
    "not the constraint. (2) NEW DEFECT AT 2018, a different and smaller "
    "one: the 2018 zip's first member is "
    "__MACOSX/._dft_test_result-from-2018-01-01_00-00-01-to-2018-04-01_"
    "00-00-01.csv - a macOS AppleDouble resource fork (header bytes shown "
    "verbatim in the failure message; contains a com.apple.quarantine "
    "bplist and an S3 opsteam-3613-temp-bucket URL) - whose bytes cannot "
    "map to the CSV schema, so the build fails loudly at schema mapping "
    "exactly as designed for unmappable members. The real 2018 members are "
    "quarterly-range named (dft_test_result-from-...-to-...csv), a measured "
    "naming change vs 2017's monthly test_result_YYYYMM.csv. No extract, "
    "gate, acceptance or score exists for build-003; the 2017 receipt is "
    "new evidence, never previously observable."
)

# --- measurements: extend the dry-run entry for the macOS leg ---
r["measurements"]["deflate64_dryrun_2026_11_07"] = (
    r["measurements"]["deflate64_dryrun_2026_11_07"].rstrip()[:-1]
    + " EXTENDED for the macOS defect before build-004 (same script, "
    "committed at the 004 repair): RED-M - the build-003 source (git "
    "2efdf50) exits 1 on a fixture zip whose first member is "
    "__MACOSX/._<real-member-name> with AppleDouble bytes, with the exact "
    "'cannot map columns' failure, so the leg bites. GREEN-M - the patched "
    "build (skip __MACOSX/ and ._-prefixed members before any decode) "
    "exits 0 on the same junk-carrying tree and reproduces the stdlib "
    "extract byte-for-byte (train/eval/holdout CSVs, meta.json, "
    "quality.json) - the junk member contributes nothing. All earlier "
    "legs (RED-A, RED-D, GREEN-D, GREEN-S, GREEN-FULL, gate/accept/triad) "
    "remain green in the same run. Fixture numbers are NOT findings."
)

# --- next_action: the running-state handoff for build-004 ---
r["next_action"] = (
    "dvsa-mot-build-004 RUNNING on worker 174959633 (cpx32, hel1, launched "
    "2026-11-07T09:49:48Z, reservation 0.32 EUR, budget month 2026-11; the "
    "macOS junk-member skip is the only change vs build-003, whose 2017 "
    "receipt PROVED the Deflate64 route on the real DfT zip - 38,056,161 "
    "rows parsed, 2015/2016 reproduced EXACTLY; a failed build-004 at "
    "2018's junk-member stage would mean the skip rule is wrong - diagnose "
    "the collected container.log; a failure at a LATER year is a NEW "
    "source-shape finding, and the qualification budget rule applies: one "
    "rebuild per structural defect, and a fourth rebuild of the same "
    "construction means the task design question gets raised with the "
    "operator instead of another retry). Expected upload: /output "
    "summary.json, qualification-dvsa-mot-next-test-outcome.json (+ .txt), "
    "acceptance .txt, references .json, container.log, source.tar. ON "
    "COMPLETION: (1) sh scripts/scout-factory worker collect "
    "dvsa-mot-build-004; (2) DETERMINISTIC CROSS-CHECK (required before "
    "any figure is quoted): run probe/fetch_diagnostics_build003_2026_"
    "11_07.py with the job directory adjusted to dvsa-mot-build-004 (or a "
    "copy), then probe/verify_crosscheck_build003_2026_11_07.py adjusted "
    "likewise - 2005-2014 must reproduce build-001's receipts EXACTLY, "
    "2015-2016 build-002's EXACTLY, 2017 build-003's EXACTLY (38,056,161/"
    "35,983,938/35,975), and the 2018-2024 receipts + non-completed "
    "inventories are read as NEW evidence; (3) require gate 1.5.0 PASSED "
    "on the FULL artifact + exact-byte --accept in the collected bytes "
    "BEFORE any AUC, base rate or headroom figure is quoted; (4) record "
    "the post-acceptance reference triad (persistence_prior_result / "
    "calendar_make_week / vehicle_train_rate + supplementary) beside the "
    "artifact identity, eval only, holdout sealed; (5) destroy the worker "
    "with provider 404 read-back; (6) then the dvsa-mot-baseline bundle "
    "(assembled from candidates/dvsa-mot-next-test-outcome/baseline; fill "
    "its fetch block with baseline/make_fetch_2026_11_07.py): fetch the "
    "accepted extract from staging, RE-ACCEPT the collected "
    "qualification.json against the bytes before any score, harness "
    "runner verbatim, the pre-registered deciding check vs EVERY triad "
    "member, cluster = vehicle_id, eval 2019-2021 only. A failed build or "
    "gate stops everything and is recorded as a finding with diagnosis "
    "before any further launch."
)

REC.write_text(json.dumps(r, indent=1) + "\n")
print("recorded build-003 failure + build-004 launch; jobs:", len(r["jobs"]))
