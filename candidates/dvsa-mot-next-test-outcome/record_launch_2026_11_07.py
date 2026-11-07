"""Record the dvsa-mot-build-002 repair + launch (advancement 2026-11-07).

Appends the launch receipt to jobs[], a dated measurement describing the
pre-launch red/green dry run, and rewrites next_action to the running-state
handoff. No score has ever existed for this candidate; the pre-registered
triad and deciding rule are untouched.
"""
import json
from pathlib import Path

REC = Path("candidates/dvsa-mot-next-test-outcome/record.json")
r = json.loads(REC.read_text())

# --- jobs[]: the launch receipt ---
launch = {
    "job_id": "dvsa-mot-build-002",
    "server_id": 174936753,
    "server_type": "cpx32",
    "location": "hel1",
    "launched_at": "2026-11-07T06:13:46Z",
    "status_at_record_write": "running",
    "ipv4": "2.29.159.168",
    "reservation_eur": "0.32",
    "provider_hourly_eur": "0.0692400000000000",
    "budget_month": "2026-11",
    "what": (
        "Repair relaunch of dvsa-mot-build-001 per the recorded next_action: "
        "exactly two changes, both construction-side, before any score. "
        "(1) build.py treats any test_result outside {P, F, PRS} as a "
        "non-completed test - excluded from both sides of every pair "
        "(build_pairs now filters on not-in-COMPLETED_RESULTS, not on the "
        "ABR/ABA tuple), counted per year with a distinct-value inventory "
        "(non_completed_rows / non_completed_values in summary.json "
        "population.per_year), while the parse-time counters the "
        "deterministic 2005-2014 cross-check reads (rows_seen / class4 / "
        "sampled) are byte-for-byte unchanged in behaviour; the fail-loud "
        "assertion now covers schema-level unmappability only, and "
        "looks_like_data recognises headerless-era data rows by parseable "
        "date so an undocumented value cannot masquerade as a header. "
        "(2) max_artifact_mb 8 -> 200 in source/job.json + bundle.json "
        "overrides (measured extract estimate ~57-65 MB; 3x headroom). "
        "Label rule, pre-registered triad and deciding rule untouched."
    ),
}
assert r["jobs"], "record must carry prior jobs"
assert r["jobs"][-1].get("job_id") == "dvsa-mot-build-001", "unexpected tail job"
r["jobs"].append(launch)

# --- measurements: the pre-launch red/green dry run ---
r["measurements"]["repair_dryrun_2026_11_07"] = (
    "MEASURED on the coordinator before relaunch (probe/dryrun_abrve_2026_11_07.py, "
    "synthetic fixtures regenerated from the committed probe/dryrun_fixtures_2026_11_05.py "
    "with the exact 2015 ABRVE row from build_failure_2015_abrve_2026_11_05 injected "
    "verbatim plus an ABRVE and an ABR row for a real md5-bucket vehicle): RED - the "
    "pre-repair build.py (git HEAD, as launched for build-001) exits 1 on the ABRVE row "
    "with the exact recorded assertion, proving the dry run bites. GREEN - the repaired "
    "build.py exits 0; 2015 non_completed_rows >= 3 with non_completed_values carrying "
    "both ABRVE and ABR; the bucket vehicle's ABRVE/ABR tests are excluded from both "
    "sides of every pair (pairs.abandoned_rows counts them); result_histogram counts "
    "ABRVE. GATE 1.5.0 on the synthetic extract: 45/45 results PASS, failed_checks []; "
    "exact-byte --accept ACCEPTED; post-acceptance score.py triad machinery exit 0 "
    "(eval only). Fixture numbers are NOT findings and are never quoted as task "
    "evidence; this entry exists to show the repair changes construction behaviour "
    "only where the failure evidence said it must."
)

# --- next_action: the running-state handoff ---
r["next_action"] = (
    "dvsa-mot-build-002 RUNNING on worker 174936753 (cpx32, hel1, launched "
    "2026-11-07T06:13:46Z, reservation 0.32 EUR, budget month 2026-11; this is "
    "the ONE rebuild allowed for the value-assertion defect - a second "
    "value/schema refusal is a new finding requiring fresh diagnosis, not "
    "another retry). Expected upload: /output summary.json, "
    "qualification-dvsa-mot-next-test-outcome.json (+ .txt), acceptance .txt, "
    "references .json, container.log, source.tar. ON COMPLETION: "
    "(1) sh scripts/scout-factory worker collect dvsa-mot-build-002; "
    "(2) DETERMINISTIC CROSS-CHECK (required before any figure is quoted): the "
    "collected summary.json population.per_year rows_seen / class4_rows / "
    "sampled_rows for 2005-2014 must reproduce the values recorded in "
    "measurements.build_failure_2015_abrve_2026_11_05 EXACTLY, and read the "
    "2015-2024 non_completed_values inventories (new measurement, never "
    "previously observable); (3) require gate 1.5.0 PASSED on the FULL "
    "artifact + exact-byte --accept in the collected bytes BEFORE any AUC, "
    "base rate or headroom figure is quoted; (4) record the post-acceptance "
    "reference triad (persistence_prior_result / calendar_make_week / "
    "vehicle_train_rate + supplementary) beside the artifact identity, eval "
    "only, holdout sealed; (5) destroy the worker with provider 404 read-back; "
    "(6) then the dvsa-mot-baseline bundle (assembled from "
    "candidates/dvsa-mot-next-test-outcome/baseline): fetch the accepted "
    "extract from staging, RE-ACCEPT the collected qualification.json against "
    "the bytes before any score, harness runner verbatim, the pre-registered "
    "deciding check vs EVERY triad member, cluster = vehicle_id, eval "
    "2019-2021 only. A failed build or gate stops everything and is recorded "
    "as a finding with diagnosis before any further launch."
)

REC.write_text(json.dumps(r, indent=1) + "\n")
print("recorded dvsa-mot-build-002 launch; jobs:", len(r["jobs"]))
