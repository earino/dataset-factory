"""Record the dvsa-mot-build-001 failure: evidence, diagnosis, repair plan.

Appends the failed-attempt receipt to jobs[], a dated measurement with the
collected evidence, and rewrites next_action to the measured repair. No score
has ever existed for this candidate; the pre-registered triad and deciding
rule are untouched.
"""
import json
from pathlib import Path

REC = Path("candidates/dvsa-mot-next-test-outcome/record.json")
r = json.loads(REC.read_text())

# --- jobs[]: the failed attempt receipt ---
attempt = {
    "job_id": "dvsa-mot-build-001",
    "server_id": 174661065,
    "server_type": "cpx32",
    "location": "hel1",
    "launched_at": "2026-11-05T18:33:02Z",
    "terminal_state": "failed",
    "container_exit_code": 1,
    "elapsed_seconds": 1737.9,
    "staging_release_id": 435609197,
    "uploaded": True,
    "collected_at": "2026-11-05T19:45:48Z",
    "worker_deleted_at": "2026-11-05T19:52:54Z (provider read-back: status=deleted via worker status reconcile)",
    "cost_note": "29 min of the 140-min reservation on 0.06924 EUR/h provider-measured cpx32; reservation 0.32 EUR retained per policy",
    "outcome": (
        "BUILD FAILED at the 2015 source file, exactly by the pre-registered "
        "fail-loud rule: unexpected test_result 'ABRVE' at seq 18757 (build.py "
        "asserts test_result in {P,F,PRS,ABR,ABA}). No extract, no gate run, no "
        "acceptance, no reference triad, no score. Evidence preserved: container.log "
        "collected (1,896 B) with per-year receipts 2005-2014 and the exact failing "
        "row; source.tar (the launch bundle) preserved in the staging release."
    ),
}
assert r["jobs"], "record must already carry the launch receipt"
if r["jobs"][-1].get("job_id") != "dvsa-mot-build-001" or "terminal_state" in r["jobs"][-1]:
    r["jobs"].append(attempt)
else:
    r["jobs"].append(attempt)

# --- measurements: the failure evidence ---
r["measurements"]["build_failure_2015_abrve_2026_11_05"] = (
    "MEASURED on the worker (dvsa-mot-build-001, container.log collected to "
    ".factory/dvsa-mot-build-001/ and preserved in staging release 435609197): "
    "the build fetched and parsed 2005-2014 cleanly - per-year rows_seen / "
    "class4 / sampled (md5 mod 1000 == 0): 2005 7,499,744/7,113,089/7,101; "
    "2006 32,014,080/30,302,568/30,572; 2007 33,591,238/31,803,974/31,948; "
    "2008 34,439,132/32,591,753/32,500; 2009 35,436,943/33,529,083/33,506; "
    "2010 36,134,920/34,179,326/34,097; 2011 36,849,154/34,790,696/35,074; "
    "2012 36,846,342/34,831,846/34,872; 2013 37,361,925/35,346,508/35,295; "
    "2014 37,493,825/35,458,346/35,635. Per-year result histograms for "
    "P/F/PRS/ABR/ABA recorded in the log; ABR+ABA stays ~0.55-0.7% (the "
    "<0.6% pre-launch estimate was correct in scale). FAILURE at "
    "source_2015.txt.gz seq 18757: test_result='ABRVE' (row: test_id "
    "1574076421, vehicle_id 192184530, test_date 2015-07-03, class 4, NT, "
    "test_mileage empty, postcode SK, VOLKSWAGEN GOLF PLUS, RED, DI, 1896, "
    "first_use 2006-07-07, completed_date empty). All other fields are "
    "well-formed, so this is a source VALUE anomaly, not a delimiter/parse "
    "shift; the empty mileage and completed_date match the abandoned-row "
    "shape. 'ABRVE' is not in the documented result-code set. CONSEQUENCES, "
    "both measured/derived: (1) the sampled panel is ~34-35k completed "
    "class-4 tests per year, so priors 2009-2023 is ~500k tests -> "
    "~450-490k pair rows -> ~57-65 MB extract at the 21-column ~128 B/row - "
    "the launch's max_artifact_mb=8 would ALSO have refused the upload "
    "(see artifact_allowance_check_2026_11_05, directionally confirmed); "
    "(2) 2015-2024 result-value inventories remain unmeasured because the "
    "build died at 2015 (Range is ignored at data.dft.gov.uk, so a bounded "
    "coordinator-side probe is impossible - the repair must inventory them "
    "on the worker)."
)

# --- next_action: the measured repair, for the next advancement session ---
r["next_action"] = (
    "Repair dvsa-mot construction from the measured build_failure_2015_abrve_2026_11_05 "
    "evidence, then relaunch as dvsa-mot-build-002 (new job ID; bundles are immutable). "
    "Exactly two changes, both construction-side, both BEFORE any score has ever existed: "
    "(1) build.py treats any test_result outside {P,F,PRS} as a non-completed test: "
    "excluded from both sides of every pair AND counted per year, with a per-year "
    "distinct-value inventory written into summary.json (this stays inside the "
    "population pre-registration - target_definition reserves ABR/ABA handling 'to be "
    "decided and documented at construction'; the label rule and the pre-registered "
    "triad/deciding rule are untouched). Keep the fail-loud assertion for schema-level "
    "unmappability (missing/misnamed columns), not for result values. (2) raise "
    "max_artifact_mb to 200 in source/job.json (measured extract ~57-65 MB; 3x headroom, "
    "matching the austin 131->400 pattern). Then assemble, plan, launch dvsa-mot-build-002; "
    "require the deterministic cross-check that 2005-2014 per-year rows_seen/class4/"
    "sampled reproduce the recorded values exactly; gate 1.5.0 exit 0 on the FULL "
    "artifact + exact-byte --accept BEFORE any number is quoted; references triad "
    "post-acceptance; then the dvsa-mot-baseline-001 bundle (fetch block + collected "
    "qualification.json, re-accept before any score, harness runner verbatim, deciding "
    "check vs every triad member, cluster = vehicle_id). One rebuild per structural "
    "defect: this relaunch is the one allowed for the value-assertion defect; a second "
    "value/schema refusal after the inventory repair is a new finding requiring a fresh "
    "diagnosis, not another blind retry."
)

REC.write_text(json.dumps(r, indent=1) + "\n")
print("record updated: jobs =", len(r["jobs"]), "measurements =", len(r["measurements"]))
