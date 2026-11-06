#!/usr/bin/env python3
"""Prepare cpcb-aqi-baseline-001 from cpcb-aqi-build-002's collected result.

Run AFTER `sh scripts/scout-factory worker collect cpcb-aqi-build-002` (the job is
expected to end FAILED at the reference stage, with the construction, gate and
acceptance evidence uploaded). This script:

  1. reads the collected result.json and the release's own manifest.json (fetched
     here, digest-verified against the collected asset list);
  2. fetches the gate report + acceptance log (small assets) and verifies them;
  3. requires gate 1.5.0 ok=true failed_checks=[] and an ACCEPTED line for the
     artifact digest, and that the report's artifact digest equals the manifest's;
  4. copies the gate report to baseline/qualification.json;
  5. fills baseline/job.json's fetch block with the five extract assets;
  6. writes baseline/expected_artifact.json.

No bulk CSV is downloaded here: the baseline worker re-fetches and verifies every
digest on arrival and re-accepts the bytes before any score. The staging token is
read in-process from its 0600 file and never printed or exported.
"""
import hashlib
import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "candidates" / "cpcb-aqi-exceedance"
REPO = "earino/dataset-factory-staging"
TOKEN_FILE = Path("/opt/data/.secrets/github-staging.token")
FIVE = {
    "output/extract/meta.json": "extract/meta.json",
    "output/extract/public/train.csv": "extract/public/train.csv",
    "output/extract/public/eval.csv": "extract/public/eval.csv",
    "output/extract/private/holdout.csv": "extract/private/holdout.csv",
    "output/extract/quality.json": "extract/quality.json",
}
REPORT_LOGICAL = "output/qualification-cpcb-aqi-exceedance.json"
ACCEPT_LOGICAL = "output/acceptance-cpcb-aqi-exceedance.txt"


class NoAuthOnHostChange(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
                new.remove_header("Authorization")
        return new


def api_json(url: str, token: str, tries: int = 4):
    last = None
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={
                "Authorization": "token " + token, "User-Agent": "scout-fill/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read())
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise SystemExit(f"api call failed: {url}: {last}")


def fetch_asset(asset_id: int, token: str) -> bytes:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}",
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/octet-stream",
                 "User-Agent": "scout-fill/1.0"})
    opener = urllib.request.build_opener(NoAuthOnHostChange())
    with opener.open(request, timeout=180) as response:
        return response.read()


def sha256_of(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def main() -> int:
    job_id = sys.argv[1] if len(sys.argv) > 1 else "cpcb-aqi-build-002"
    fact = ROOT / ".factory" / job_id
    result = json.loads((fact / "result.json").read_text())
    assert result.get("uploaded") is True, "the job uploaded nothing; collect it first"
    release = int(result["release_id"])
    by_id = {a["id"]: a for a in result["assets"]}
    token = TOKEN_FILE.read_text().strip()

    assets = api_json(f"https://api.github.com/repos/{REPO}/releases/{release}/assets?per_page=100",
                      token)
    api_by_name = {a["name"]: a for a in assets}

    # the release's own manifest (logical path -> part name/size/sha256)
    manifest_name = next((n for n in api_by_name if n.startswith("manifest")), None)
    assert manifest_name, "release has no manifest asset"
    manifest_asset = api_by_name[manifest_name]
    manifest_body = fetch_asset(manifest_asset["id"], token)
    manifest_sha = sha256_of(manifest_body)
    if manifest_asset["id"] in by_id:
        assert by_id[manifest_asset["id"]]["sha256"] == manifest_sha, "manifest digest"
    manifest = json.loads(manifest_body)
    by_logical = {e["file"]: e for e in manifest["assets"]}

    reports_dir = fact / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "manifest.json").write_bytes(manifest_body)

    def fetch_logical(logical: str, dest: Path) -> bytes:
        entry = by_logical.get(logical)
        if entry is None:
            raise SystemExit(f"the release manifest has no {logical!r} - the job did not "
                             f"reach that stage, so the artifact is not qualified this way")
        part = api_by_name.get(entry["name"])
        if part is None:
            raise SystemExit(f"the release has no asset named {entry['name']!r}")
        body = fetch_asset(part["id"], token)
        assert len(body) == entry["size"] == part["size"], logical
        assert sha256_of(body) == entry["sha256"], logical
        if part["id"] in by_id:
            assert by_id[part["id"]]["sha256"] == entry["sha256"], logical
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        return body

    report_body = fetch_logical(REPORT_LOGICAL, reports_dir / "gate_report.json")
    accept_body = fetch_logical(ACCEPT_LOGICAL, reports_dir / "acceptance.log")
    gate = json.loads(report_body)
    assert gate.get("ok") is True and gate.get("failed_checks") == [], \
        f"the gate did not pass: {gate.get('failed_checks')}"
    assert gate.get("gate_version") == "1.5.0", gate.get("gate_version")
    artifact = (gate.get("artifact") or {}).get("artifact_version", {}).get("digest")
    assert artifact, "the gate report carries no artifact digest"
    accept_text = accept_body.decode("utf-8", "replace")
    assert "ACCEPTED" in accept_text and artifact[:16] in accept_text, \
        "the acceptance log does not accept this artifact"

    shutil.copyfile(reports_dir / "gate_report.json", BASE / "baseline" / "qualification.json")

    fetch_assets, files_block = [], {}
    for logical, dest in FIVE.items():
        entry = by_logical.get(logical)
        if entry is None:
            raise SystemExit(f"the release manifest has no {logical!r}")
        part = api_by_name.get(entry["name"])
        if part is None:
            raise SystemExit(f"the release has no asset named {entry['name']!r}")
        fetch_assets.append({"asset_id": part["id"], "dest": dest,
                             "size": entry["size"], "sha256": entry["sha256"]})
        files_block[dest.split("extract/")[1]] = {"bytes": entry["size"],
                                                  "sha256": entry["sha256"]}
    assert len({a["asset_id"] for a in fetch_assets}) == 5

    job_path = BASE / "baseline" / "job.json"
    job = json.loads(job_path.read_text())
    job["fetch"] = {"repo": REPO, "release": release, "assets": fetch_assets}
    job_path.write_text(json.dumps(job, indent=2) + "\n")

    expected = {
        "source_job": job_id,
        "staging_release": release,
        "gate_version": gate.get("gate_version"),
        "artifact_version": artifact,
        "files": files_block,
        "verification": ("every digest is cross-checked against the collected result, the "
                         "release manifest and the live asset list before use; the gate "
                         "report (bundled as baseline/qualification.json) passed 1.5.0 with "
                         "no failed checks and the acceptance log accepted this artifact. "
                         "The baseline job re-fetches the five assets, verifies each sha256 "
                         "on arrival and re-accepts the bytes before any score."),
    }
    (BASE / "baseline" / "expected_artifact.json").write_text(
        json.dumps(expected, indent=2) + "\n")

    print(json.dumps({"release": release, "artifact_version": artifact,
                      "gate_ok": gate.get("ok"), "fetch_assets": fetch_assets}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
