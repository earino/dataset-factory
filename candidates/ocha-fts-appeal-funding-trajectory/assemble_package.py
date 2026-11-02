#!/usr/bin/env python3
"""Assemble release/ocha-fts-appeal-funding-trajectory/ from canonical sources.

Every copied byte comes from a recorded source: the artifact's own meta.json and
quality.json (fetched from the accepted staging release 431492902 this session,
digests asserted), the candidate's source/baseline scripts, the canonical gate,
the read-only benchmark clone's runner files, and the standing licence texts.
Docs (README, DATA_DICTIONARY, ...) are written separately by hand; this script
creates the directory skeleton and the byte-exact copies.
"""
import hashlib
import json
import pathlib
import shutil

REPO = pathlib.Path("/opt/data/dataset-factory")
CAND = REPO / "candidates/ocha-fts-appeal-funding-trajectory"
REL = REPO / "release/ocha-fts-appeal-funding-trajectory"
SCRATCH = pathlib.Path("/opt/data/cache/scratch/ftsb2")
BENCH = pathlib.Path("/opt/data/harness_benchmark/task_template")
PINS = REPO / "release/pins-planning-appeal-outcome"

EXPECTED = json.loads((CAND / "baseline/expected_artifact.json").read_text())


def copy(src: pathlib.Path, dst: pathlib.Path, expect_sha: str = None) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    got = hashlib.sha256(dst.read_bytes()).hexdigest()
    if expect_sha is not None:
        assert got == expect_sha, f"{dst}: {got} != {expect_sha}"
    print(f"  {dst.relative_to(REL)}  ({got[:16]}...)")


if REL.exists():
    raise SystemExit("release/ocha-fts-appeal-funding-trajectory already exists; refusing to overwrite")
REL.mkdir(parents=True)

print("artifact bytes (from the accepted staging release 431492902):")
meta = SCRATCH / "ocha_meta.json"
quality = SCRATCH / "ocha_quality.json"
copy(meta, REL / "meta.json", EXPECTED["files"]["meta.json"]["sha256"])
copy(quality, REL / "quality.json", EXPECTED["files"]["quality.json"]["sha256"])

print("gate report beside the artifact:")
copy(CAND / "baseline/qualification.json", REL / "qualification.json")

print("code/:")
copy(CAND / "source/build.py", REL / "code/build.py")
copy(CAND / "source/run.sh", REL / "code/run.sh")
copy(CAND / "source/score.py", REL / "code/score.py")
copy(CAND / "baseline/materialize.py", REL / "code/materialize.py")
copy(REPO / "skills/dataset-qualification/scripts/qualify_dataset.py",
     REL / "code/qualify_dataset.py",
     "4fab8a34fe4f3357b7cd911087bfa243c56a96d8720e40d0d4cb2169100404d1")

print("baseline/ runner files (verbatim from the read-only clone):")
copy(BENCH / "train.py", REL / "baseline/train.py",
     "a3c6bcf13735bc85c52129ded68f839090dffdc266ebc3810dc61b2e6ea5e7e8")
copy(BENCH / "validate.py", REL / "baseline/validate.py",
     "b597e7f84fed614e64b4a86fbecbd6ec0145916a24d0d221a796586976418e7b")
copy(BENCH / "validate.sh", REL / "baseline/validate.sh",
     "3f06ca48f11c2e05d331b4d8394284925de660c1d4b086d2f8243959e83b7e6d")

print("licence texts (standing defaults):")
copy(PINS / "LICENSE-MIT.txt", REL / "LICENSE-MIT.txt")
copy(PINS / "LICENSE-CC0-1.0.txt", REL / "LICENSE-CC0-1.0.txt")

print("done")
