#!/usr/bin/env python3
"""Verify the Hugging Face copy of the Chicago DOAH release.

Two independent checks:
  1. structural - datasets.load_dataset() on the published repo returns exactly the
     three declared splits with the declared rows, columns and label value set.
  2. byte-level - each published file is re-downloaded and hashed, and the digest is
     compared with the digest recorded in the release's SHA256SUMS.

Run with the local HF venv python. Reads the token from the dashboard .env file.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import hf_hub_download

REPO = "earino/chicago-doah-adjudication"
RELEASE_TAG = "v2026.09"
ROOT = Path(__file__).resolve().parents[2]
RELEASE_DIR = ROOT / "release" / "chicago-doah-adjudication"
SCRATCH = Path("/opt/data/cache/scratch/hf-verify")

EXPECTED_SPLITS = {
    "train": 47414,
    "eval": 3436,
    "holdout": 2913,
}
EXPECTED_NEW_NAMES = {
    "train": ["charge_count", "distinct_code_count", "docket_number", "latitude",
              "longitude", "outcome", "street_direction", "street_type",
              "violation_code", "violation_date", "ward"],
    "eval": ["charge_count", "distinct_code_count", "docket_number", "latitude",
             "longitude", "outcome", "street_direction", "street_type",
             "violation_code", "violation_date", "ward"],
    "holdout": ["charge_count", "distinct_code_count", "docket_number", "latitude",
                "longitude", "outcome", "street_direction", "street_type",
                "violation_code", "violation_date", "ward"],
}
EXPECTED_LABEL_VALUES = ["Liable", "Not Liable"]


def token():
    path = Path("/opt/data/.secrets/huggingface-write.token")
    if path.exists():
        return path.read_text().strip()
    raise SystemExit("no HF token at %s" % path)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    tok = token()

    # 1. structural check
    ds = load_dataset(REPO, token=tok, revision="main")
    splits = sorted(ds.keys())
    struct = {"splits": splits, "checked": {}, "problems": []}
    for split in EXPECTED_SPLITS:
        if split not in ds:
            struct["problems"].append("split %s missing" % split)
            continue
        frame = ds[split]
        rows = len(frame)
        names = sorted(frame.column_names)
        values = sorted(str(v) for v in frame.unique("outcome"))
        struct["checked"][split] = {"rows": rows, "columns": names,
                                    "label_values": values}
        if rows != EXPECTED_SPLITS[split]:
            struct["problems"].append("split %s rows %d != %d" % (split, rows, EXPECTED_SPLITS[split]))
        if names != sorted(EXPECTED_NEW_NAMES[split]):
            struct["problems"].append("split %s columns differ" % split)
        if values != sorted(EXPECTED_LABEL_VALUES):
            struct["problems"].append("split %s label values differ" % split)
    struct["ok"] = not struct["problems"]

    # 2. byte-level check against the release's own SHA256SUMS
    sums = {}
    for line in (RELEASE_DIR / "SHA256SUMS").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        want, rel = line.split(None, 1)
        sums[rel.strip()] = want

    SCRATCH.mkdir(parents=True, exist_ok=True)
    files = {"meta.json": "meta.json",
             "public/train.csv": "data/train.csv",
             "public/eval.csv": "data/eval.csv",
             "private/holdout.csv": "data/holdout.csv",
             "quality.json": "quality.json"}
    byte = {"checked": {}, "problems": []}
    for rel, repo_path in files.items():
        got = hf_hub_download(REPO, repo_path, repo_type="dataset", token=tok,
                              revision="main", local_dir=str(SCRATCH))
        got_digest = digest(got)
        want_digest = sums.get(rel)
        match = got_digest == want_digest
        byte["checked"][repo_path] = {"sha256": got_digest, "released_as": rel,
                                      "match": match}
        if not match:
            byte["problems"].append("%s digest %s != released %s" % (repo_path, got_digest, want_digest))
    byte["ok"] = not byte["problems"]

    out = {"repo": REPO, "revision_main": "main", "release_tag": RELEASE_TAG,
           "structural": struct, "bytes": byte,
           "ok": struct["ok"] and byte["ok"]}
    dest = ROOT / ".factory" / "chicago-hf-verify.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
