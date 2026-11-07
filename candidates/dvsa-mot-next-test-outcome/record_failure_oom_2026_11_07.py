"""Record the dvsa-mot-build-004 failure: evidence, diagnosis, operator handoff.

Appends the failed-attempt receipt to jobs[], a dated measurement with the
collected evidence, and rewrites next_action to the pre-registered operator
decision: build-005 would be the FOURTH rebuild of this construction, and the
recorded boundary says the task-design question goes to the operator instead of
another automatic retry. No score has ever existed for this candidate; the
pre-registered triad and deciding rule are untouched; nothing was qualified.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
REC = ROOT / "candidates" / "dvsa-mot-next-test-outcome" / "record.json"
LOG = ROOT / ".factory" / "dvsa-mot-build-004" / "staged-container.log"
LEDGER = ROOT / "jobs" / "dvsa-mot-build-004.json"

ledger = json.loads(LEDGER.read_text())
collected_at = ledger["collected_at"]
deleted_at = ledger["deleted_at"]
result = ledger["result"]
assert result["exit_code"] == 137 and result["oom_killed"] is True, result
assert result["release_id"] == 437508692, result["release_id"]

log = LOG.read_bytes()
assert hashlib.sha256(log).hexdigest() == "631da26b8c3b81264bc2ff1292a567387f3aef65de633dbed40a5cee93d917aa"
text = log.decode()
LINE_RE = re.compile(
    r"^(\d{4}): rows_seen=(\d+) class4=(\d+) sampled=(\d+) results=(\{.*\})\s*$")
receipts, hists = {}, {}
for line in text.splitlines():
    m = LINE_RE.match(line)
    if m:
        year, rows, class4, sampled, hist = m.groups()
        receipts[int(year)] = (int(rows), int(class4), int(sampled))
        hists[int(year)] = json.loads(hist)
assert sorted(receipts) == list(range(2005, 2022)), sorted(receipts)
assert "Killed" in text and "build failed; the extract is incomplete" in text

# chain values (from the collected logs of builds 001/002/003, verified EXACT
# by verify_crosscheck_build004_2026_11_07.py, rc=0)
sampled_2005_2017 = sum(receipts[y][2] for y in range(2005, 2018))
sampled_2005_2021 = sum(receipts[y][2] for y in range(2005, 2022))
non_completed = {y: sum(v for k, v in hists[y].items()
                         if k not in ("P", "F", "PRS"))
                 for y in range(2018, 2022)}
for y in (2018, 2019, 2020, 2021):
    assert non_completed[y] > 0, y
r = json.loads(REC.read_text())

attempt = {
    "job_id": "dvsa-mot-build-004",
    "server_id": 174959633,
    "server_type": "cpx32",
    "location": "hel1",
    "launched_at": "2026-11-07T09:49:48Z",
    "terminal_state": "failed",
    "container_exit_code": 137,
    "oom_killed": True,
    "elapsed_seconds": 3123.2,
    "staging_release_id": 437508692,
    "uploaded": True,
    "collected_at": collected_at,
    "worker_deleted_at": (
        f"{deleted_at} (provider read-back 2026-11-07T10:51:03Z: "
        "GET /v1/servers/174959633 -> 404 'server not found'; GET /servers -> "
        "0 entries; GET /primary_ips -> 0 entries)"),
    "cost_note": ("52.1 min actual run of the 140-min reservation on "
                  "0.06924 EUR/h cpx32; reservation 0.32 EUR retained per "
                  "policy, budget month 2026-11"),
    "outcome": (
        "BUILD FAILED BY HOST-LEVEL OOM at the start of 2022 processing, "
        "after 17 years parsed cleanly (2005-2021) and AFTER the macOS "
        "junk-member repair was PROVEN on the real 2018-2021 zips. Kernel "
        "dmesg (read on the worker before destroy): 'Out of memory: Killed "
        "process 2659 (python3) total-vm:9959464kB, anon-rss:7548860kB', "
        "constraint=CONSTRAINT_NONE, global_oom - the whole 7.564 GiB host "
        "was exhausted, not a container cap. No extract (/output/extract "
        "empty), no summary.json, no gate run, no acceptance, no triad, no "
        "score. Evidence preserved: staging release 437508692 (source.tar "
        "53805191, container.log 631da26b, manifest.json c6a95cbe at the "
        "ledger digests); container.log fetched digest-verified to "
        ".factory/dvsa-mot-build-004/staged-container.log."),
}
assert r["jobs"][-1]["job_id"] == "dvsa-mot-build-004"
assert "terminal_state" not in r["jobs"][-1]
r["jobs"].append(attempt)

r["measurements"]["build_failure_2022_oom_2026_11_07"] = (
    "MEASURED on the dvsa-mot-build-004 worker (server 174959633; collected "
    f"container.log digest-verified from staging release 437508692; kernel "
    "dmesg read directly on the worker at 10:42:48Z). (1) THE macOS "
    "JUNK-MEMBER SKIP REPAIR IS PROVEN ON REAL DATA - the first four zip-era "
    "years no previous build ever reached all parsed cleanly, with receipts "
    "rows_seen/class4/sampled: 2018 38,681,801/36,597,485/36,609 (ABRVE=30); "
    "2019 39,310,698/37,203,595/37,224 (ABRVE=53); 2020 38,594,013/"
    "36,607,155/36,792 (ABRVE=31); 2021 40,380,646/38,155,866/38,353 "
    "(ABRVE=57). Non-completed inventories (outside {P,F,PRS}) derived from "
    f"the same collected histograms: 2018 {non_completed[2018]:,} / 2019 "
    f"{non_completed[2019]:,} / 2020 {non_completed[2020]:,} / 2021 "
    f"{non_completed[2021]:,}, values [ABA, ABR, ABRVE] every year - the "
    "ABRVE value rule keeps biting in the zip era exactly as designed. "
    "(2) THE DETERMINISTIC CROSS-CHECK PASSED (probe/"
    "verify_crosscheck_build004_2026_11_07.py, rc=0): 2005-2017 reproduce the "
    "recorded chain EXACTLY, 13/13 years (2005-2014 == build-001's log, "
    "2015-2016 == build-002's log, 2017 == build-003's log; every year also "
    f"checked against every earlier log). Sampled rows: 2005-2017 = "
    f"{sampled_2005_2017:,}; 2005-2021 = {sampled_2005_2021:,}. (3) FAILURE: "
    "kernel global OOM at 10:42:48Z, ~50 s after the 2021 receipt printed, "
    "i.e. at the start of 2022 processing (the 2022 zip was already "
    "prefetched to disk): 'Out of memory: Killed process 2659 (python3) "
    "total-vm:9959464kB anon-rss:7548860kB' - anon RSS ~7.2 GB of a 7.564 "
    "GiB host, CONSTRAINT_NONE global_oom, task_memcg=docker scope: the "
    "HOST ran out of memory; no docker --memory cap was reached. (4) STATIC "
    "CODE WALK of the shipped build.py (bundle 275b8729): the only structure "
    "designed to grow across years is all_rows (slim 14-field tuples of "
    "sampled class-4 tests; 2005-2021 = "
    f"{sampled_2005_2021:,} rows), estimated well under ~1 GB of Python "
    "object overhead; the Deflate64 member decode is a ~350-400 MB "
    "per-member transient (277 MB decompressed held whole + the compressed "
    "blob, freed per member); downloads stream to disk in chunks. The "
    "designed footprint at the 2022 boundary is therefore roughly 1.5 GB - "
    "the measured ~7.5 GB anon RSS is ~6 GB BEYOND the designed "
    "accumulation and is NOT explained by static reading: the candidate "
    "mechanisms are CPython allocator/arena retention under the ~38M "
    "rows/year parse churn, or an unlocated leak; distinguishing them "
    "requires a bounded instrumented run (per-year RSS prints), not more "
    "static reading. No extract, gate, acceptance, triad or score exists "
    "for build-004; the holdout was never reached."
)

r["next_action"] = (
    "OPERATOR DECISION REQUIRED (pre-registered boundary): build-005 would be "
    "the FOURTH rebuild of the same construction (002 ABRVE value rule, 003 "
    "Deflate64, 004 macOS junk members, each a different real defect - and "
    "004 then failed on a fifth, distinct defect: host-level OOM at 2022, see "
    "build_failure_2022_oom_2026_11_07), and this record's standing rule says "
    "the task-design question goes to the operator instead of another "
    "automatic retry. The measured evidence for the decision: every repair so "
    "far is PROVEN on real data (2018-2021 receipts are new evidence; the "
    "2005-2017 chain reproduces EXACTLY), the OOM is a memory-growth defect "
    "~6 GB beyond the designed accumulation (mechanism unresolved: allocator "
    "retention vs leak), and the un-run remainder is 2022-2024 + extract + "
    "gate + accept + triad. OPTIONS: (a) approve ONE diagnostic-instrumented "
    "relaunch dvsa-mot-build-005 on cpx42 (16 GB, 0.15 EUR/h, reservation "
    "~0.60 EUR, budget month 2026-11): the only change is an additive "
    "per-year RSS print (+ optional per-year gc.collect()) in build.py's "
    "year loop - construction/qualification logic untouched, and the run is "
    "simultaneously the cheapest discriminating measurement (per-year RSS "
    "series separates churn retention from a leak) and, if 16 GB suffices, "
    "the completing construct->qualify->accept->triad job; (b) approve a "
    "bounded redesign of the accumulation (per-vehicle incremental pairing "
    "is NOT possible without a censoring rule because a vehicle's later "
    "tests can arrive in any later year; the realistic repair is a compact "
    "row store or per-year intermediate files re-streamed at pair time - a "
    "real construction change with dry-run cost); (c) drop or re-scope the "
    "candidate. Scout does not launch build-005 without the operator's "
    "recorded choice. If (a) is approved: assemble with the RSS-print "
    "change, dry-run legs, assemble-job, plan, launch; on completion "
    "collect + verify_crosscheck_build004 (2005-2017 EXACT chain, 2018-2021 "
    "== build-004's receipts EXACT, 2022-2024 new), require gate 1.5.0 "
    "PASSED + exact-byte --accept BEFORE any figure, record the "
    "post-acceptance triad (eval only, holdout sealed), destroy with "
    "provider read-back, then the dvsa-mot-baseline bundle "
    "(baseline/make_fetch_build004_2026_11_07.py fills its fetch block) "
    "with re-accept before any score."
)

REC.write_text(json.dumps(r, indent=2) + "\n")
print("record updated: jobs[-1] terminal receipt appended for build-004")
print("measurements.build_failure_2022_oom_2026_11_07 written")
print(f"sampled 2005-2017 = {sampled_2005_2017:,}, 2005-2021 = {sampled_2005_2021:,}")
print("next_action -> operator decision (4th-rebuild boundary)")
