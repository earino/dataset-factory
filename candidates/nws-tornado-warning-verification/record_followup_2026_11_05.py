#!/usr/bin/env python3
"""Follow-up session 2026-11-05: record nws-tornado-build-001 outcome.

The watcher collected the failed build (exit 1 at 304.4 s); this session
fetched the bounded diagnostics (container.log, staging manifest) with
sha256 verification against the ledger, ran the discriminating source
probe for the refusal event, and records the diagnosis + handoff.
Construction changes stay with advancement.
"""
import json

REC = "candidates/nws-tornado-warning-verification/record.json"
STATE = "STATE.md"

d = json.load(open(REC))
j = next(x for x in d["jobs"] if x["id"] == "nws-tornado-build-001")
j["status"] = "failed"
j["exit_code"] = 1
j["collected_at"] = ("2026-11-05T15:18:50Z (collect verified the staging "
                     "release tag job-nws-tornado-build-001, asset "
                     "membership, sizes and digests)")
j["result"] = ("failed, exit 1, executor elapsed 304.4 s, oom_killed false; "
               "staging release 435325965 (source.tar 215,040 B sha256 "
               "98a9ec3f498dd3b7ac29ce10467844934a0395097fbfda84e77c105337eaaeb6, "
               "container.log 1,453 B sha256 f6d64b207a8739db5b78bbe3f00ecae7e29a7a65d5a39a00110c4cdf8bf7ad83, "
               "manifest.json 6,578 B sha256 "
               "daed327a047f671c4823ea273f1fca7a7ddf5c59d6170efce4504ed540777fc9). "
               "container.log + staging-manifest.json fetched to "
               ".factory/nws-tornado-build-001/ with sha256 verified "
               "2026-11-05T15:21:46Z")
j["outcome"] = (
    "the build's own pinned refusal fired 5.1 min in, exactly as designed: "
    "years 2008-2015 streamed cleanly (2013 anchor reproduced EXACTLY: "
    "1832 raw features / 441 verified / 1831 rows / dup_identical=1), then "
    "build.py raised 'DUPLICATE EVENT WITH DISAGREEING verify: 2016 GLD "
    "#38' and refused. No CSV, gate run, acceptance or score ever existed; "
    "nothing was scored and no performance metric exists on this artifact. "
    "Worker 174626604 destroyed after collection (provider read-back "
    "recorded in STATE.md).")

d["measurements"]["nws_tornado_build_001_failure_diagnosis"] = (
    "CONSTRUCTION defect (row-key grain), not infrastructure and not a "
    "source-corruption event. The two 'duplicates' behind the refusal are "
    "two DISTINCT tornado warnings sharing (year=2016, wfo=GLD, eventid=38): "
    "product 201605262355-KGLD-WFUS53-TORGLD (issued 2016-05-26 23:55Z, "
    "parea 656.58 km2, stormreports empty, verify=false) and product "
    "201605270019-KGLD-WFUS53-TORGLD (issued 2016-05-27 00:19Z, parea "
    "4878.67 km2, stormreports 124,125, verify=true), issued 24 minutes "
    "apart across the UTC day boundary. Measured 2026-11-05 by probe/"
    "followup_2016_GLD_38.py (cow api/1/cow.json, wfo=GLD year 2016, "
    "phenomena=TO significance=W; evidence in probe/out/"
    "followup_2016_GLD_38.json; run log .factory/nws-tornado-build-001/"
    "container.log). So cow's (year, wfo, eventid) is NOT a unique warning "
    "key: each warning's own verify is correct for its own polygon/window; "
    "the pre-registered disagreeing-verify refusal fired on a false "
    "positive (distinct warnings, not one corrupted warning). Consequence "
    "for the rebuild: (a) the row key must become unique per warning "
    "(product_id, or (year,wfo,eventid)+product_id) and row_id must "
    "disambiguate them; (b) the dup_kept_earliest branch (agreeing verify, "
    "differing bytes -> keep one) can silently DROP a distinct warning - "
    "the same measured event is the test case, both warnings must survive "
    "as rows; (c) keep the byte-identical-dup drop and the disagreeing-"
    "verify refusal for genuinely same-product duplicates; (d) per-year "
    "row deltas in the failed run exceeded dup_identical for several years "
    "(2008 -6 vs 3; 2009 -10 vs 5; 2011 -51 vs 41; 2012 -33 vs 6), "
    "consistent with kept-earliest merges and/or unparsable-window skips - "
    "the rebuild's ledger must attribute every dropped row per year before "
    "relaunch; the raw-feature anchors (2013 1832/441, 2023 2531/656) are "
    "key-independent and unchanged. Cheapest discriminating next check "
    "(done): the single-WFO year pull above; next cheapest before rebuild "
    "is a local re-key of the cached anchor years 2013/2023 asserting the "
    "new key is unique and counting eventid collisions per year.")

d["next_action"] = (
    "ADVANCEMENT OWNS THE REBUILD (construction change; follow-up session "
    "2026-11-05 diagnosed and preserved evidence only). nws-tornado-build-001 "
    "failed by its own pinned refusal at 2016 GLD #38; diagnosis complete in "
    "measurements.nws_tornado_build_001_failure_diagnosis: (year, wfo, "
    "eventid) is not a unique warning key in cow, so the ONE rebuild per "
    "structural defect class is nws-tornado-build-002 with (1) a unique "
    "per-warning row key (product_id or year+wfo+eventid+product_id) and "
    "row_ids that disambiguate the two 2016 GLD #38 warnings, (2) the "
    "dup_kept_earliest branch re-examined so distinct warnings sharing an "
    "eventid both become rows (measured test case: 201605262355 vs "
    "201605270019 TORGLD), (3) the byte-identical drop + same-product "
    "disagreeing-verify refusal retained, (4) a local pre-launch check on "
    "the cached anchor years 2013/2023: new key unique, per-year eventid-"
    "collision counts recorded, every dropped row attributed by the ledger "
    "(the failed run's deltas 2008 -6 vs 3 / 2009 -10 vs 5 / 2011 -51 vs 41 "
    "/ 2012 -33 vs 6 are unexplained until then), raw-feature anchors "
    "unchanged (1832/441, 2531/656). Then the unchanged run.sh ladder "
    "(construct -> full-artifact gate -> exact-byte --accept -> references) "
    "and the pre-registered deciding rule, exactly as recorded before "
    "build-001. Evidence paths: probe/out/followup_2016_GLD_38.json, "
    "probe/followup_2016_GLD_38.py, .factory/nws-tornado-build-001/"
    "container.log, staging release 435325965 (digests verified).")

json.dump(d, open(REC, "w"), indent=1)
print("record updated:", REC)
print("jobs[0] status:", j["status"], "exit:", j["exit_code"])
print("measurements now:", len(d["measurements"]), "entries")
