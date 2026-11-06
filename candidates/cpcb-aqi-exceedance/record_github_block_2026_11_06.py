"""Record the github destination block of release/cpcb-aqi-exceedance/DESTINATIONS.json.

Pre-flip state: repository private, bytes verified. Every fact re-read from the
GitHub API and MANIFEST.json at run time; no digest hand-copied. Adds the
planner-required top-level artifact_version (equal to the manifest's), the same
omission the cqc close-out corrected.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from factory.release_schema import record_destination  # noqa: E402

GH = "/opt/data/.local/bin/gh"
REPO_ID = "earino/cpcb-aqi-exceedance"
RELEASE_ID = 436366305
TAG = "v2026.11"
PACKAGE = REPO_ROOT / "release" / "cpcb-aqi-exceedance"
DESTINATIONS = PACKAGE / "DESTINATIONS.json"


def gh_api(endpoint):
    out = subprocess.run(
        [GH, "api", endpoint], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def main():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = json.loads((PACKAGE / "MANIFEST.json").read_text())
    artifact_version = manifest["artifact_version"]

    repo = gh_api(f"repos/{REPO_ID}")
    assert repo["private"] is True, "repository must still be private pre-flip"
    release = gh_api(f"repos/{REPO_ID}/releases/{RELEASE_ID}")
    assert release["draft"] is False and release["tag_name"] == TAG
    tag_ref = gh_api(f"repos/{REPO_ID}/git/ref/tags/{TAG}")["object"]["sha"]
    main_sha = gh_api(f"repos/{REPO_ID}/branches/main")["commit"]["sha"]
    assert tag_ref == main_sha, f"tag {tag_ref} != main {main_sha}"
    target_commit = main_sha

    # asset names are flat; map them back to the logical manifest paths
    flat_to_logical = {}
    for logical, entry in (manifest.get("assets") or {}).items():
        flat = logical.replace("/", "-")  # GitHub rejects '/' in asset names
        flat_to_logical[flat] = (logical, entry)
    live = {}
    for asset in release["assets"]:
        logical, entry = flat_to_logical[asset["name"]]
        assert asset["size"] == entry["bytes"], f"size mismatch {asset['name']}"
        assert asset["digest"] == f"sha256:{entry['sha256']}", f"digest mismatch {asset['name']}"
        live[logical] = asset["digest"]
    assert len(live) == 5 and len(release["assets"]) == 5, "expected exactly five assets"

    fields = {
        "repo": REPO_ID,
        "release_id": RELEASE_ID,
        "release_tag": TAG,
        "target_commit": target_commit,
        "private": True,
        "verified": True,
        "verified_at": now,
        "files_verified": [
            "public/train.csv",
            "public/eval.csv",
            "private/holdout.csv",
            "meta.json",
            "quality.json",
        ],
        "checks": [
            "private repository created 2026-11-06 by the release session (publish-dataset.py) "
            f"with the package documents on main at initial commit {target_commit}; release "
            f"v2026.11 ({RELEASE_ID}) created non-draft at main; live API read-back {now}: repo "
            f"private:true, tag {TAG} == main == {target_commit}, exactly the five flat assets",
            "worker job cpcb-aqi-publish-001 (server 174785899, destroyed with provider 404 "
            "read-back: 0 servers, 0 IPs) copied the five accepted "
            f"{artifact_version[:12]} assets from private staging release 436180445 into "
            f"release {RELEASE_ID} under the flat asset names, 5/5 transferred, failures [], "
            "asset 716782178 arrival sha256 == manifest digest; bytes never through the coordinator",
            "live server-side read-back 2026-11-06 (~13:04Z): all five assets of release "
            f"{RELEASE_ID} report server digests equal to MANIFEST.json (meta.json 1f59e74e..., "
            "private-holdout.csv 2dae0040..., public-eval.csv e187f645..., public-train.csv "
            "24b03a70..., quality.json 98250e9d...); re-verified at close-out "
            f"{now} by this script against the API: all five sizes and digests equal the manifest",
            "fresh-consumer worker job cpcb-aqi-consumer-002 (destroyed with provider 404 "
            f"read-back): every published REPRODUCE.md step green on the released bytes of "
            f"release {RELEASE_ID} - package-vs-MANIFEST 24 files OK, 5/5 assets "
            "digest-verified, get_dataset.py OK, sha256sum -c 5/5 OK, gate 1.5.0 PASSED, "
            f"exact-byte --accept {artifact_version[:12]} ACCEPTED, both AUC prints 0.9734 "
            "CONTRACT OK with the holdout never copied, 15 references recomputed equal "
            "measurements.json, deciding check reproduced model AUC CI [0.9713,0.9753] above "
            "0.5, verdict headroom_demonstrated",
        ],
        "anonymous_access": False,
        "note": "private release v2026.11 staged and verified 2026-11-06; NOT published - the "
            "flip (the operator's single approval, preceded by the independent pre-flip audit) "
            "makes it public. Evidence: jobs/cpcb-aqi-publish-001.json, "
            "jobs/cpcb-aqi-consumer-002.json, .factory/cpcb-aqi-consumer-002/reports/.",
    }
    record_destination(DESTINATIONS, "github", fields, release_tag=TAG)

    # planner-required top-level artifact_version, equal to the manifest's
    data = json.loads(DESTINATIONS.read_text())
    data["artifact_version"] = artifact_version
    DESTINATIONS.write_text(json.dumps(data, indent=2) + "\n")

    final = json.loads(DESTINATIONS.read_text())
    assert final["artifact_version"] == manifest["artifact_version"]
    assert set(final["destinations"]) == {"github", "huggingface"}
    print(f"recorded github block at {DESTINATIONS} ({now}); "
          f"tag == main == {target_commit[:12]}, 5/5 assets verified, private, "
          f"artifact_version {artifact_version[:12]}")
    print(json.dumps(final, indent=1))


if __name__ == "__main__":
    main()
