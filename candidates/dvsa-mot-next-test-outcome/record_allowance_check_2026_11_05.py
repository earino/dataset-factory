"""Record the pre-completion artifact-allowance risk check for dvsa-mot-build-001.

Adds a dated measurement entry (clearly labelled ESTIMATE where it is one)
and leaves next_action unchanged (collect first). Idempotent by key.
"""
import json
from pathlib import Path

REC = Path("candidates/dvsa-mot-next-test-outcome/record.json")
KEY = "artifact_allowance_check_2026_11_05"

entry = (
    "PRE-COMPLETION CHECK (written 2026-11-05 19:2xZ, while dvsa-mot-build-001 was still "
    "running, BEFORE any outcome existed). The launched job declares max_artifact_mb = 8, "
    "and workers/upload.py refuses the WHOLE staging upload (reports included) when the "
    "bytes under /output plus source.tar plus container.log exceed that allowance. "
    "MEASURED inputs: 2024 source year = 7,667,648,876 B uncompressed (~64M rows at the "
    "prefix-measured ~120 B/row); first-4MB prefix of test_result_202408.csv = 34,924 rows "
    "with 19,328 distinct vehicle_ids; shipped extract = 21 plain-CSV columns. ESTIMATE "
    "(not a measurement): the md5 mod 1000 == 0 vehicle sample keeps ~0.1% of a "
    "multi-ten-million vehicle panel, so the pair panel plausibly lands in the "
    "hundreds-of-thousands of rows (~30-130 MB extract) - every other candidate in the "
    "catalog sized max_artifact_mb to its extract (austin 131 MB extract -> 400; msha "
    "3.38 GB -> 4200; za-cct 8.4 MB -> 24), while this job's 8 MiB supports only ~60k "
    "rows at ~128 B/row. PREDICTION, not a finding: if the extract exceeds the "
    "allowance, publish() raises UploadError('Artifacts exceed job allowance') and "
    "NOTHING uploads - but executor.py still embeds /output/summary.json (<= 64 KiB) "
    "in /opt/scout/result.json and `worker collect` is designed to fetch exactly that, "
    "so the measured row counts, per-file sizes and the 19-file vintage sha256 pins "
    "survive for a correctly-sized rebuild. RESPONSE PRE-REGISTERED: one corrected "
    "rebuild (dvsa-mot-build-002, new job ID per the immutable-bundle rule) with "
    "max_artifact_mb sized from the collected per-file bytes with >= 2.5x headroom; "
    "construction logic unchanged - this is a job-descriptor defect, not a build "
    "defect; the gate/triad then rerun deterministically on the rebuilt bytes. If "
    "collect instead shows a clean upload, this entry is void and the baseline "
    "proceeds as recorded."
)

r = json.loads(REC.read_text())
assert r["measurements"].get(KEY) is None, "entry already present"
r["measurements"][KEY] = entry
REC.write_text(json.dumps(r, indent=1) + "\n")
print("recorded", KEY, "- record now has", len(r["measurements"]), "measurement entries")
