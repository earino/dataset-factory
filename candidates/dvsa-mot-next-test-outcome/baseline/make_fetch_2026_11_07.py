#!/usr/bin/env python3
"""Fill the dvsa-mot-baseline-001 fetch block from the collected build evidence.

Digests and asset ids are copied programmatically from the collected staging
manifest (never hand-typed: cpcb-aqi-consumer-001 died pre-container on a
one-character digest transcription error). Asset ids are re-resolved live from
the staging release API by name AND digest match, so the fetch spec can only
name assets that are server-side digest-equal to the collected manifest.
Also copies the collected qualification report to baseline/qualification.json
(the baseline bundle ships it as /workspace/qualification.json for re-accept).

Run AFTER `worker collect dvsa-mot-build-002` and the bounded diagnostics
fetch (which writes .factory/dvsa-mot-build-002/staged-manifest.json).
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
STAGED = ROOT / ".factory" / "dvsa-mot-build-002" / "staged-manifest.json"
JOB = ROOT / "candidates" / "dvsa-mot-next-test-outcome" / "baseline" / "job.json"
QUAL_DEST = ROOT / "candidates" / "dvsa-mot-next-test-outcome" / "baseline" / "qualification.json"
GH = "/opt/data/.local/bin/gh"

EXPECTED = {
    "extract/meta.json",
    "extract/public/train.csv",
    "extract/public/eval.csv",
    "extract/private/holdout.csv",
    "extract/quality.json",
}


def api(path, accept=None):
    cmd = [GH, "api", path]
    if accept:
        cmd += ["-H", f"Accept: {accept}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        raise SystemExit(f"gh api {path} failed: {res.stderr[:300]}")
    return res.stdout


def main() -> int:
    manifest = json.loads(STAGED.read_text())
    repo = manifest.get("repo") or json.loads(
        (ROOT / ".factory" / "dvsa-mot-build-002" / "result.json").read_text()
    )["repo"]
    ledger = json.loads((ROOT / "jobs" / "dvsa-mot-build-002.json").read_text())
    release_id = ledger["result"]["release_id"]

    logical = {entry["file"]: entry for entry in manifest["assets"]}
    missing = EXPECTED - set(logical)
    if missing:
        raise SystemExit(f"staging manifest is missing artifact files: {sorted(missing)}")

    live = {a["name"]: a for a in json.loads(
        api(f"repos/{repo}/releases/{release_id}/assets?per_page=100"))}

    fetch_assets = []
    for path in sorted(EXPECTED):
        entry = logical[path]
        asset = live.get(entry["name"])
        if asset is None:
            raise SystemExit(f"{path}: asset {entry['name']} not in the live release")
        digest = (asset.get("digest") or "").removeprefix("sha256:")
        if asset["size"] != entry["size"] or digest != entry["sha256"]:
            raise SystemExit(f"{path}: live size/digest != collected manifest")
        fetch_assets.append({"asset_id": asset["id"], "dest": path,
                             "size": entry["size"], "sha256": entry["sha256"]})

    # the qualification report for re-accept: fetched bounded, digest-verified
    qual_entry = logical.get("qualification-dvsa-mot-next-test-outcome.json")
    if qual_entry is None:
        raise SystemExit("qualification report missing from the staging manifest")
    if qual_entry["size"] > 2 * 1024 * 1024:
        raise SystemExit("qualification report larger than the bounded-fetch cap")
    blob = api(f"repos/{repo}/releases/assets/{live[qual_entry['name']]['id']}",
               accept="application/octet-stream").encode()
    if hashlib.sha256(blob).hexdigest() != qual_entry["sha256"]:
        raise SystemExit("fetched qualification report digest mismatch")
    QUAL_DEST.write_bytes(blob)

    job = json.loads(JOB.read_text())
    old_what = job["what"]
    job["fetch"] = {"repo": repo, "release": release_id, "assets": fetch_assets}
    filled = (
        f"(FETCH BLOCK generated programmatically from the collected staging "
        f"manifest of dvsa-mot-build-002 release {release_id}; asset ids "
        f"resolved live by name+digest match)"
    )
    job["what"] = job["what"].replace(
        "(FILL release id + asset digests from the staging manifest after "
        "collection; the launcher refuses a null release)",
        filled,
    ).replace("the private staging release created by dvsa-mot-build-001",
              "the private staging release created by dvsa-mot-build-002")
    assert job["what"] != old_what, "the what-text placeholders were not found"
    JOB.write_text(json.dumps(job, indent=2) + "\n")
    print(json.dumps(job["fetch"], indent=1)[:1200])
    print("baseline/qualification.json written:", len(blob), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
