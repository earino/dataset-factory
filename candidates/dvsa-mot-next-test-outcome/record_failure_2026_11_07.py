"""Record the dvsa-mot-build-002 failure + Deflate64 diagnosis (2026-11-07).

The ABRVE repair WORKED on the real data (2015 parsed, 242 ABRVE rows counted;
2016: 27); the job then died at the 2017 DfT zip on a NEW, previously
unobservable defect: all members are compress_type 9 (Deflate64), unsupported
by Python's stdlib zipfile. build-001 never reached the zip era, and the
2026-11-05 dry run used Python-written (deflate) fixtures, so no earlier
evidence could exist. This script appends the failure receipt, the measured
diagnosis, and rewrites next_action to the precise repair plan.
"""
import json
from pathlib import Path

REC = Path("candidates/dvsa-mot-next-test-outcome/record.json")
r = json.loads(REC.read_text())

attempt = {
    "job_id": "dvsa-mot-build-002",
    "server_id": 174936753,
    "server_type": "cpx32",
    "location": "hel1",
    "launched_at": "2026-11-07T06:13:46Z",
    "terminal_state": "failed",
    "container_exit_code": 1,
    "elapsed_seconds": 2082.7,
    "staging_release_id": 437396758,
    "uploaded": True,
    "outcome": (
        "BUILD FAILED at the 2017 DfT zip, a NEW defect class distinct from "
        "the repaired value assertion: zipfile raises NotImplementedError "
        "because every member of dft_test_result_2017.zip is compress_type 9 "
        "(Deflate64). THE ABRVE REPAIR WORKED ON REAL DATA: 2015 parsed with "
        "result_histogram ABRVE=242 and 2016 with ABRVE=27 (both counted as "
        "non-completed, excluded from pairs); 2005-2016 receipts complete. "
        "No extract, no gate run, no acceptance, no score. Evidence: "
        "container.log (3,024 B) in staging release 437396758; the per-year "
        "lines re-verify the deterministic 2005-2014 cross-check EXACTLY."
    ),
}
assert r["jobs"][-1].get("job_id") == "dvsa-mot-build-002", "unexpected tail"
r["jobs"][-1].update(attempt)

r["measurements"]["build_failure_2017_deflate64_2026_11_07"] = (
    "MEASURED on the dvsa-mot-build-002 worker (still alive after the failure, "
    "server 174936753): (1) dft_test_result_2017.zip downloaded whole "
    "(data.dft.gov.uk ignores Range): 1,082,702,159 bytes, sha256 8b52a91e5392"
    "571d37cfa7aec99a92763282d8b663b70644820f4bc266ffc2ec, 17.2 s; central "
    "directory: 12 members (names test_result_31870.csv etc., NOT month-named "
    "like the 2024 zip), compress_type 9 for ALL members, each ~277-278 MB "
    "uncompressed / ~90 MB compressed; stdlib read of member 0 raises "
    "NotImplementedError, confirming the container.log traceback. (2) BOUNDED "
    "S3 tail probes (ranged reads, coordinator): the DVSA S3 origin does NOT "
    "host 2017-2021 (403 on every key), and its 2022/2023 mirrors "
    "(dft_test_result_2022.zip 1,164,809,596 B, 1 member test_result_2022.csv; "
    "dft_test_result_2023.zip 1,192,881,905 B, 1 member test_result.csv) are "
    "ALSO compress_type 9 - so switching URL sources cannot avoid Deflate64 "
    "for 2017-2023. The pinned 2024 zip was measured 2026-10-19 by ranged "
    "reads incl. partial member decompression, so it is standard deflate. "
    "(3) PACKAGE OPTIONS measured from PyPI metadata: zipfile-deflate64 0.2.0 "
    "has NO cp313 wheel (max cp310, specific ABI) and would need an sdist "
    "build (no gcc in python:3.13-slim) - NOT viable; inflate64 1.0.4 "
    "(miurahr, LGPL-2.1+, production-stable) ships cp313 manylinux x86_64 "
    "wheels and provides inflate64.Inflater().inflate(data), the raw "
    "Enhanced-Deflate decompressor, but no zipfile integration - the build "
    "must read members via explicit local-header parsing (30-byte fixed "
    "header + name/extra lengths, then compress_size bytes from the central-"
    "directory entry) and inflate them itself. (4) FIRST IN-CONTAINER "
    "VERIFICATION ATTEMPT of that path (python:3.13-slim + inflate64==1.0.4 "
    "on the worker) was OOM-KILLED (exit 137, oom=true) with no script "
    "output reaching the pipe - cause not yet isolated (buffered stdout lost "
    "the progress prints); the host shows 7.7 GB RAM total, 7.3 GB free "
    "after. The memory behaviour of a single-shot inflate of a ~90 MB member "
    "must be measured (RSS instrumentation, chunked feeding if supported) "
    "BEFORE any relaunch; a Deflate64 member decode that cannot run in "
    "~1 GB is a repair-design blocker, not a relaunch candidate."
)

r["next_action"] = (
    "dvsa-mot-build-002 FAILED at the 2017 DfT zip: all members compress_type 9 "
    "(Deflate64), unsupported by stdlib zipfile (full diagnosis in "
    "measurements.build_failure_2017_deflate64_2026_11_07; the ABRVE value "
    "repair itself is PROVEN on real data - 2015 ABRVE=242 and 2016 ABRVE=27 "
    "counted as non-completed; 2005-2016 receipts reproduce build-001 exactly "
    "for the shared years). This is a NEW defect (container compression), "
    "freshly diagnosed, so one rebuild is allowed for it - but the repair is "
    "NOT yet verified: the first in-container inflate64 attempt OOM-killed "
    "with unbuffered output lost, so the next session must FIRST (1) collect "
    "dvsa-mot-build-002 (sh scripts/scout-factory worker collect "
    "dvsa-mot-build-002) and run probe/fetch_diagnostics_2026_11_07.py; (2) "
    "re-run the deterministic 2005-2014 EXACT cross-check from the collected "
    "summary.json (probe/verify_crosscheck_2026_11_07.py) - 2015/2016 are "
    "new evidence with the ABRVE inventory; (3) verify the Deflate64 member "
    "decode in a python:3.13-slim container on a worker with RSS "
    "instrumentation (python -u, /proc/self/status prints, docker --memory "
    "cap so a MemoryError surfaces instead of a host OOM kill): single-shot "
    "inflate64.Inflater().inflate(blob) on one 2017 member first; if RSS "
    "explodes, test chunked/repeated inflate() feeding and a streaming line "
    "splitter (never text.splitlines() on a 277 MB member); only a decode "
    "that runs comfortably inside the job's 8192 MB is acceptable; (4) patch "
    "source/build.py open_text_lines to read Deflate64 members via the "
    "explicit local-header path (stdlib zipfile still reads the central "
    "directory and any standard-deflate member like the pinned 2024 zip), "
    "add the pinned install (inflate64==1.0.4) to run.sh, new job id "
    "dvsa-mot-build-003 (bundles immutable), re-run the coordinator dry run "
    "(probe/dryrun_abrve_2026_11_07.py - synthetic fixtures exercise the "
    "stdlib path and the new code shape), assemble, plan, launch; (5) the "
    "worker 174936753 (build-002) must be destroyed with provider 404 "
    "read-back once collection is done - it is idle until its 140-min expiry "
    "(~08:33Z) and the sweep would otherwise handle it. NO score has ever "
    "existed; the triad, label rule and deciding rule are untouched. A "
    "failed build-003 at the same zip stage is a task-design question, not "
    "another retry."
)

REC.write_text(json.dumps(r, indent=1) + "\n")
print("recorded build-002 failure + Deflate64 diagnosis; jobs:", len(r["jobs"]))
