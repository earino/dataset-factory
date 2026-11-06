#!/usr/bin/env python3
"""Acceptance verification for cpcb-aqi-hf-002 (worker-status follow-up, 2026-11-06).

Read-only: asserts the collected job result satisfies every element of the
recorded ACCEPTANCE list (record.next_action) against the job spec
hf/job.json and the frozen release/cpcb-aqi-exceedance/MANIFEST.json:
the four already-uploaded assets skipped at their manifest digests,
public-eval.csv fetched at the manifest digest and uploaded with the
Hub-reported digest verified, host cleanup complete, and the load_dataset
check green (splits/positives/columns/labels equal to verify_loading).
Also prints the context the follow-up still needs (full next_action,
record status fields, DESTINATIONS.json precedent)."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
CAND = BASE / "candidates" / "cpcb-aqi-exceedance"


def load(p):
    return json.loads(Path(p).read_text())


ledger = load(BASE / "jobs" / "cpcb-aqi-hf-002.json")
r = load(BASE / ".factory" / "cpcb-aqi-hf-002" / "result.json")
spec = load(CAND / "hf" / "job.json")
spec_job = spec.get("job", spec)
assert spec_job == ledger["job"], "hf/job.json != ledger job block"
record = load(CAND / "record.json")
manifest = load(BASE / "release" / "cpcb-aqi-exceedance" / "MANIFEST.json")

ok = []


def check(name, cond, detail=""):
    assert cond, f"FAIL: {name} {detail}"
    ok.append(name)


# 0. collected evidence consistency
check("ledger.result == .factory result.json", ledger["result"] == r)
check("ledger status collected", ledger["status"] == "collected")
check("job status succeeded", r["status"] == "succeeded")
check("uploaded true", r["uploaded"] is True)
check("failures empty", r["hf_publish"]["failures"] == [])
check("host cleanup complete", r.get("host_cleanup_complete") is True)

# 1. uploads: exactly eval, at the spec/manifest digest
assets = {a["target"]: a for a in spec_job["hf_publish"]["assets"]}
ups = r["hf_publish"]["uploads"]
check("one upload (eval)", [u["target"] for u in ups] == ["data/public-eval.csv"])
up = ups[0]
check("eval bytes", up["bytes"] == assets["data/public-eval.csv"]["size"] == 20210392)
check("eval digest == spec", up["sha256"] == assets["data/public-eval.csv"]["sha256"])

# 2. skipped: the other four, each already at the manifest digest
skipped = {s["target"]: s["reason"] for s in r["hf_publish"]["skipped"]}
expect_skip = set(assets) - {"data/public-eval.csv"}
check("skipped set", set(skipped) == expect_skip, f"{sorted(skipped)}")
check("skip reason", set(skipped.values()) == {"already at the manifest digest"})

# 3. manifest digest mapping (flat asset target -> logical manifest path)
def manifest_path(target):
    name = target[len("data/"):] if target.startswith("data/") else target
    if name.startswith("public-") or name.startswith("private-"):
        name = name.replace("-", "/", 1)
    return name


files = manifest.get("files")
if isinstance(files, dict):
    mmap = {k: (v.get("sha256") if isinstance(v, dict) else v) for k, v in files.items()}
else:
    mmap = {e.get("path") or e.get("name"): e.get("sha256") for e in files or []}
print("manifest paths:", sorted(mmap))
for target, a in assets.items():
    mp = manifest_path(target)
    check(f"manifest has {mp}", mp in mmap)
    check(f"{target} digest == manifest", a["sha256"] == mmap.get(mp))
check("eval digest == manifest", up["sha256"] == mmap.get(manifest_path("data/public-eval.csv")))

# 4. Hub-side read-back block (hf_-prefixed result key)
hub = None
for k, v in r.items():
    if isinstance(v, dict) and v.get("schema_version") == 1 and "files" in v:
        hub = v
        break
check("hub read-back present", hub is not None)
check("hub ok, no errors", hub["ok"] is True and hub["errors"] == [])
print("hub commit:", hub["commit"])
check("hub commit is 40-hex", len(hub["commit"]) == 40)
check("hub file set", set(hub["files"]) == set(assets))
for target, a in assets.items():
    hf = hub["files"][target]
    check(f"hub {target} digest", hf["sha256"] == a["sha256"])
    check(f"hub {target} bytes", hf["bytes"] == a["size"])

# 5. load_dataset check equal to the spec's verify_loading
vl = spec_job["hf_publish"]["verify_loading"]
ld = r["hf_loading"]
check("loading ok, no problems", ld["ok"] is True and ld["problems"] == [])
check("splits", sorted(ld["splits"]) == sorted(vl["splits"]))
for split, exp in vl["splits"].items():
    got = ld["checked"][split]
    check(f"{split} rows", got["rows"] == exp["rows"])
    check(f"{split} positives", got["positives"] == exp["positives"])
    check(f"{split} columns", sorted(got["columns"]) == sorted(vl["columns"]))
    check(f"{split} label values", sorted(got["label_values"]) == sorted(str(x) for x in vl["label_values"]))

# 6. staging evidence pointers
check("staging release 436695608", r["release_id"] == 436695608)
check("two staging assets", len(r["assets"]) == 2)
src = [a for a in r["assets"] if a["size"] == ledger["source_bytes"]]
check("source bundle at ledger digest", bool(src) and src[0]["sha256"] == ledger["source_sha256"])

print(f"ALL {len(ok)} ACCEPTANCE CHECKS PASS")
print()
print("=== record.next_action (full) ===")
print(record["next_action"])
print()
print("=== record status-shaped fields ===")
for key in sorted(record):
    if any(s in key.lower() for s in ("status", "packag", "await", "flip")):
        print(f"{key}: {json.dumps(record[key])[:400]}")
print()
print("=== DESTINATIONS.json precedent ===")
for name in ("eutl-installation-net-short", "austin-911-response"):
    d = BASE / "release" / name / "DESTINATIONS.json"
    m = BASE / "release" / name / "MANIFEST.json"
    listed = "DESTINATIONS.json" in m.read_text() if m.is_file() else "n/a"
    print(f"-- {name}: DESTINATIONS exists={d.is_file()}; MANIFEST mentions it={listed}")
    if d.is_file():
        print(d.read_text())
