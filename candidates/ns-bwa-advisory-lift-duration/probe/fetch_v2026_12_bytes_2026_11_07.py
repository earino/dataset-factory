#!/usr/bin/env python3
"""Fetch the v2026.12 byte-pinned artifact metadata + commit the -002 evidence.

Bounded, digest-asserted: only three small extract files (meta.json 1,360 B,
quality.json 18,643 B, summary.json 5,873 B) are fetched from private staging
release 437529809 (job ns-bwa-002), each verified against the worker-written
staged manifest before use. The bulk CSVs stay in staging for the transfer
job; nothing over 2 MB is ever downloaded.

Side effects (all digest-verified against .factory/ns-bwa-002/staged-manifest.json):
  * release/ns-bwa-advisory-lift-duration/meta.json     <- output/extract/meta.json
  * release/ns-bwa-advisory-lift-duration/quality.json  <- output/extract/quality.json
  * .factory/ns-bwa-002/summary.json                    <- output/extract/summary.json (doc source)
  * candidates/<id>/reports/qualification-ns-bwa-002.json, references-ns-bwa-002.json,
    acceptance-ns-bwa-002.txt                           <- already-collected local parts
  * candidates/<id>/baseline/baseline_result.json        <- ns-bwa-baseline-002 collected result
    (the committed copy still described the v2026.10 baseline job ns-bwa-baseline-001;
    release-manifest.py reads this file, so it must describe v2026.12)

Run from the repo root after `worker collect ns-bwa-002` + `ns-bwa-baseline-002`.
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
GH = "/opt/data/.local/bin/gh"
MAX_BYTES = 2 * 1024 * 1024
CAND = ROOT / "candidates" / "ns-bwa-advisory-lift-duration"
RELEASE_DIR = ROOT / "release" / "ns-bwa-advisory-lift-duration"


def api(path, accept=None, binary=False):
    cmd = [GH, "api", path]
    if accept:
        cmd += ["-H", f"Accept: {accept}"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode:
        raise SystemExit(f"api failed {path}: {res.stderr.decode()[:300]}")
    return res.stdout if binary else res.stdout.decode()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_extract_file(logical: str, dest: Path, entry: dict, by_name: dict, repo: str):
    asset = by_name.get(entry["name"])
    if asset is None:
        raise SystemExit(f"{logical}: asset {entry['name']} missing in staging")
    if entry["size"] > MAX_BYTES:
        raise SystemExit(f"{logical}: {entry['size']} B exceeds the bounded-fetch cap")
    blob = api(f"repos/{repo}/releases/assets/{asset['id']}",
               accept="application/octet-stream", binary=True)
    digest = hashlib.sha256(blob).hexdigest()
    if digest != entry["sha256"]:
        raise SystemExit(f"{logical}: digest mismatch {digest} vs {entry['sha256']}")
    dest.write_bytes(blob)
    print(f"  fetched {logical} -> {dest} ({entry['size']} B, sha256 {digest[:16]}... verified)")


def copy_verified(src: Path, dest: Path, expected_sha: str, label: str):
    digest = sha256_of(src)
    if digest != expected_sha:
        raise SystemExit(f"{label}: local part digest mismatch {digest} vs {expected_sha}")
    if dest.is_file() and sha256_of(dest) == expected_sha:
        print(f"  {label}: already at the -002 digest ({digest[:16]}...)")
        return
    dest.write_bytes(src.read_bytes())
    print(f"  {label}: {src} -> {dest} (sha256 {digest[:16]}... verified)")


manifest = json.loads((ROOT / ".factory/ns-bwa-002/staged-manifest.json").read_text())
result = json.loads((ROOT / ".factory/ns-bwa-002/result.json").read_text())
repo = result["repo"]
entries = {e["file"]: e for e in manifest["assets"]}
release = result["release_id"]
assets = json.loads(api(f"repos/{repo}/releases/{release}/assets?per_page=100"))
by_name = {a["name"]: a for a in assets}
print(f"staging release {release}: {len(assets)} assets listed")

print("byte-pinned artifact files (v2026.12, artifact 49bf4cfa427375c6...):")
fetch_extract_file("output/extract/meta.json", RELEASE_DIR / "meta.json",
                   entries["output/extract/meta.json"], by_name, repo)
fetch_extract_file("output/extract/quality.json", RELEASE_DIR / "quality.json",
                   entries["output/extract/quality.json"], by_name, repo)
fetch_extract_file("output/extract/summary.json", ROOT / ".factory/ns-bwa-002/summary.json",
                   entries["output/extract/summary.json"], by_name, repo)

print("collected -002 evidence -> candidate dir (digest-verified local parts):")
copy_verified(ROOT / ".factory/ns-bwa-002/file-0007-part-0000",
              CAND / "reports/qualification-ns-bwa-002.json",
              entries["output/qualification-ns-bwa-advisory-lift-duration.json"]["sha256"],
              "gate report (v2026.12)")
copy_verified(ROOT / ".factory/ns-bwa-002/file-0009-part-0000",
              CAND / "reports/references-ns-bwa-002.json",
              entries["output/references-ns-bwa-advisory-lift-duration.json"]["sha256"],
              "references (v2026.12)")
copy_verified(ROOT / ".factory/ns-bwa-002/file-0000-part-0000",
              CAND / "reports/acceptance-ns-bwa-002.txt",
              entries["output/acceptance-ns-bwa-advisory-lift-duration.txt"]["sha256"],
              "acceptance (v2026.12)")

bmanifest = json.loads((ROOT / ".factory/ns-bwa-baseline-002/staged-manifest.json").read_text())
bentries = {e["file"]: e for e in bmanifest["assets"]}
copy_verified(ROOT / ".factory/ns-bwa-baseline-002/file-0001-part-0000",
              CAND / "baseline/baseline_result.json",
              bentries["output/baseline_result.json"]["sha256"],
              "baseline result (ns-bwa-baseline-002)")

# guard: the release-dir gate report must be the v2026.12 report before the manifest is built
gate_report = CAND / "baseline/qualification.json"
gate_sha = sha256_of(gate_report)
want = entries["output/qualification-ns-bwa-advisory-lift-duration.json"]["sha256"]
if gate_sha != want:
    raise SystemExit(f"baseline/qualification.json is not the v2026.12 gate report "
                     f"({gate_sha[:16]} vs {want[:16]})")
copy_verified(gate_report, RELEASE_DIR / "qualification.json", want,
              "release/qualification.json")
print("OK: release package now carries the v2026.12 meta/quality/gate-report bytes")
