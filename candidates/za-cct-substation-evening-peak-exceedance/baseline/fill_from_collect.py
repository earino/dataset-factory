#!/usr/bin/env python3
"""Fill the za-cct-baseline bundle from za-cct-001's collected result (one-shot).

Repo-relative; run from the dataset-factory root. Candidate-scoped session mechanics
for the runner-contract baseline job, kept beside the bundle it fills (the same
discipline as the ocha-fts baseline's fill script).

Reads .factory/za-cct-001/result.json + the staging release's own manifest.json
(already collected, digest-verified, at .factory/za-cct-001/reports/manifest.json),
queries the release asset list read-only for the part-name -> asset-id mapping, and
cross-checks every digest in THREE independent records before writing anything:

  A. the collected result.json assets (written by the collector at collect time),
  B. the release's own manifest.json (written by the worker at upload time),
  C. the GitHub release asset list (name, id, size - read live, read-only).

Then:
  1. copies the collected gate report -> baseline/qualification.json (its sha256
     must equal the digest recorded in BOTH A and B for that logical file);
  2. asserts the report is a clean gate 1.5.0 pass for artifact 9f2e10ce...;
  3. fills baseline/job.json's fetch block (5 extract assets: ids/sizes/sha256);
  4. writes baseline/expected_artifact.json.
No bulk CSV is downloaded by this script; the worker re-downloads and verifies on
arrival. Fails loudly on any mismatch. The staging token is read from its 0600
file at the point of use and is never printed, exported or written anywhere.
"""
import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # candidates/<id>/baseline/ -> repo root
BL = ROOT / "candidates/za-cct-substation-evening-peak-exceedance/baseline"
FACT = ROOT / ".factory/za-cct-001"
TOKEN_FILE = Path("/opt/data/.secrets/github-staging.token")
REPO = "earino/dataset-factory-staging"
RELEASE_ID = 432591871
FIVE = {
    "output/extract/meta.json": "extract/meta.json",
    "output/extract/public/train.csv": "extract/public/train.csv",
    "output/extract/public/eval.csv": "extract/public/eval.csv",
    "output/extract/private/holdout.csv": "extract/private/holdout.csv",
    "output/extract/quality.json": "extract/quality.json",
}
REPORT_LOGICAL = "output/qualification-za-cct-substation-evening-peak-exceedance.json"
ARTIFACT_VERSION = "9f2e10ce485635f65e695072e2bbd904024ebf58b1465d12fb969f8bb0692180"


def api_json(url: str, token: str, tries: int = 4):
    last = None
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={
                "Authorization": f"token {token}", "User-Agent": "scout-fill/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read())
        except Exception as exc:  # noqa: BLE001 - retried transport errors
            last = exc
            time.sleep(2 ** attempt)
    raise SystemExit(f"api call failed: {url}: {last}")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    # --- record A: the collected result ------------------------------------
    result = json.loads((FACT / "result.json").read_text())
    assert result["status"] == "succeeded" and result["uploaded"] is True, result.get("status")
    assert int(result["release_id"]) == RELEASE_ID, result.get("release_id")
    by_id = {a["id"]: a for a in result["assets"]}

    # --- record B: the release's own manifest (collected, digest-verified) ---
    manifest = json.loads((FACT / "reports/manifest.json").read_text())
    by_logical = {e["file"]: e for e in manifest["assets"]}
    assert set(FIVE) <= set(by_logical), "manifest lacks one of the five extract files"

    # --- record C: the live release asset list (read-only) ------------------
    token = TOKEN_FILE.read_text().strip()
    assets = api_json(
        f"https://api.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets"
        "?per_page=100", token)
    api_by_name = {a["name"]: a for a in assets}

    fetch_assets = []
    files_block = {}
    for logical, dest in FIVE.items():
        entry = by_logical[logical]                       # B: logical -> part name/size/sha
        part = api_by_name.get(entry["name"])             # C: part name -> asset id/size
        assert part is not None, f"release has no asset named {entry['name']!r}"
        collected = by_id[part["id"]]                     # A: collected id -> size/sha
        assert collected["size"] == entry["size"] == part["size"], logical
        assert collected["sha256"] == entry["sha256"], logical
        fetch_assets.append({"asset_id": part["id"], "dest": dest,
                             "size": entry["size"], "sha256": entry["sha256"]})
        files_block[dest.split("extract/")[1]] = {"bytes": entry["size"],
                                                  "sha256": entry["sha256"]}
    assert len({a["asset_id"] for a in fetch_assets}) == 5, "extract assets not five distinct ids"

    # --- worker-written summary digests are a fourth cross-check -----------
    summary_digests = result["summary"]["artifact_sha256"]
    for dest, expected in files_block.items():
        assert summary_digests[dest] == expected["sha256"], dest

    # --- 1. the gate report itself ------------------------------------------
    report_collected = (FACT / "reports/output" /
                        "qualification-za-cct-substation-evening-peak-exceedance.json")
    report_digest = sha256_of(report_collected)
    assert report_digest == by_logical[REPORT_LOGICAL]["sha256"], "collected gate report digest"
    assert report_digest == by_id[api_by_name[by_logical[REPORT_LOGICAL]["name"]]["id"]]["sha256"], \
        "gate report digest vs collected asset"
    shutil.copyfile(report_collected, BL / "qualification.json")
    gate = json.loads((BL / "qualification.json").read_text())
    assert gate.get("ok") is True and gate.get("failed_checks") == [], "gate not clean"
    assert gate.get("gate_version") == "1.5.0", gate.get("gate_version")
    digest = (gate.get("artifact") or {}).get("artifact_version", {}).get("digest")
    assert digest == ARTIFACT_VERSION, digest

    # --- 3. the fetch block --------------------------------------------------
    job_path = BL / "job.json"
    job = json.loads(job_path.read_text())
    assert job["fetch"]["release"] == RELEASE_ID and job["fetch"]["assets"] == [], \
        "job.json fetch block is not the empty placeholder this script fills"
    job["fetch"]["assets"] = fetch_assets
    job_path.write_text(json.dumps(job, indent=2) + "\n")

    # --- 4. expected artifact -------------------------------------------------
    expected = {
        "job": "za-cct-001",
        "staging_release": RELEASE_ID,
        "gate_version": "1.5.0",
        "artifact_version": ARTIFACT_VERSION,
        "files": files_block,
        "verification": "the five artifact digests are cross-checked in three records before "
                        "use: the worker-written staging manifest for release 432591871 "
                        "(collected digest-verified at .factory/za-cct-001/reports/manifest.json), "
                        "the collector's result.json asset list, and the live release asset list "
                        "read read-only. Job za-cct-001's gate 1.5.0 report (bundled as "
                        "baseline/qualification.json, sha256 " + report_digest[:16] + "...) "
                        "accepted exactly these bytes on the worker (artifact "
                        + ARTIFACT_VERSION[:16] + "...). The baseline job re-fetches the same "
                        "five assets with every sha256 verified on arrival and re-accepts them "
                        "against that report before any score exists. The extract stays in "
                        "staging; the CSVs are never held in the factory repository.",
    }
    (BL / "expected_artifact.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(json.dumps({"fetch_assets": fetch_assets,
                      "gate_report_sha256": report_digest,
                      "artifact_version": ARTIFACT_VERSION}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
