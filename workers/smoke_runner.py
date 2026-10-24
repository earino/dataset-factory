"""Host-side integration smoke for the prediction-time adapter (issue #17).

Runs on an expendable worker as a supervised executor host operation, exactly
like the existing transfer/hf_publish children: never on Scout. Stdlib only on
the host path except for the scoring venv (pandas/scikit-learn/numpy, resolved
from the harness lock at runtime and recorded). Every pin comes from the job;
this runner invents no digests, dates or claims. It proves the mechanics of
the reviewed protocol on a real artifact and reports bounded receipts.

Split design (reviewed, issue #17 comment 6384042471):
- train' = public train minus its final N calendar months by the reviewed
  ordering column; dev = that tail (labeled development file, the only eval-
  role file the candidate can see); test = original public eval bytes,
  scorer-owned, never mounted into the candidate container.
- The published private holdout is never fetched. Gate 1.5 + --accept run
  over the three derivative files only.
- The candidate container is the adapter's locked-down profile; the reference
  (ordinary row-wise, full-frame) run is a separate TRUSTED container. The
  two probability vectors are compared element-wise; no AUC is reported.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path("/opt/scout")
REPORT_LIMIT = 200_000

REFERENCE_SCRIPT = '''\
import contextlib, io, json, runpy, sys
import pandas as pd
with contextlib.redirect_stdout(sys.stderr):
    ns = runpy.run_path("train.py", run_name="__train__")
frame = pd.read_csv("/work/data/eval.csv")
fn = ns["predict_proba"]
with contextlib.redirect_stdout(sys.stderr):
    probabilities = [float(p) for p in __import__("numpy").asarray(fn(frame), dtype=float).ravel()]
print(json.dumps(probabilities))
'''

PROBE_SCRIPT = '''\
import json, pathlib, socket
scored_absent = not pathlib.Path("/work/data/eval-scored.csv").exists()
network_refused = False
try:
    with socket.create_connection(("192.0.2.1", 53), timeout=3):
        pass
except OSError:
    network_refused = True
visible = sorted(str(p.relative_to("/work")) for p in pathlib.Path("/work").rglob("*") if p.is_file())
print(json.dumps({"scored_absent": scored_absent, "network_refused": network_refused,
                  "visible_files": visible}))
'''


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_run(command, timeout, *, capture=True):
    result = subprocess.run(command, capture_output=capture, text=True, timeout=timeout)
    if result.returncode != 0:
        stderr = (getattr(result, "stderr", "") or "")[-300:]
        raise RuntimeError(f"command failed ({result.returncode}): {command[:3]}...; stderr tail: {stderr}")
    return (result.stdout or "") if capture else ""


def stage_log(stage, detail, receipts):
    value = detail if isinstance(detail, (str, int, float, bool)) else json.dumps(detail, sort_keys=True)
    receipts[stage] = value
    print(f"[smoke] {stage}: {value}", flush=True)


def host_scoring_venv(smoke, work):
    """The adapter's parent scorer runs host-side; resolve pinned versions from the lock."""
    versions = {}
    lock = (work / "harness" / "uv.lock").read_text()
    import re
    for package in ("numpy", "pandas", "scikit-learn"):
        found = re.findall(r'name = "%s"\s*,\s*version = "([^"]+)"' % package, lock)
        if not found:
            raise RuntimeError(f"cannot resolve {package} from the harness lock")
        versions[package] = sorted(set(found))[-1]
    venv = work / "host-venv"
    checked_run([sys.executable, "-m", "venv", str(venv)], timeout=300)
    checked_run([str(venv / "bin" / "pip"), "install", "--quiet", "--disable-pip-version-check",
                 f"numpy=={versions['numpy']}", f"pandas=={versions['pandas']}",
                 f"scikit-learn=={versions['scikit-learn']}"], timeout=900)
    return venv, versions


def derivative_split(work, smoke, columns, time_col, target):
    """Two streaming passes: find the month boundary, then write the split. O(1) memory."""
    train_csv = work / "input" / "train.csv"
    boundary_month = None
    with train_csv.open(newline="") as stream:
        import csv
        reader = csv.DictReader(stream)
        months = []
        for row in reader:
            month = row[time_col][:7]
            if month not in months:
                months.append(month)
        if len(months) <= smoke["dev_months"]:
            raise RuntimeError("train has no months to spare for the development tail")
        boundary_month = months[-smoke["dev_months"]]
    derivative = work / "derivative"
    derivative.mkdir()
    counts = {"train": {"rows": 0, "positives": 0}, "dev": {"rows": 0, "positives": 0}}
    with train_csv.open(newline="") as stream:
        import csv
        reader = csv.DictReader(stream)
        writers = {}
        for name in ("train", "dev"):
            out = derivative / ("train.csv" if name == "train" else "eval.csv")
            writers[name] = (out.open("w", newline=""), csv.DictWriter(out, fieldnames=columns))
            writers[name][1].writeheader()
        for row in reader:
            side = "dev" if row[time_col][:7] >= boundary_month else "train"
            writers[side][1].writerow(row)
            counts[side]["rows"] += 1
            if row[target] == str(smoke["positive_label"]):
                counts[side]["positives"] += 1
        for handle, _ in writers.values():
            handle.close()
    shutil.copyfile(work / "input" / "eval.csv", derivative / "holdout.csv")
    return derivative, counts, boundary_month


def run(job, report):
    smoke = job["smoke"]
    work = BASE / "smoke"
    if work.exists():
        shutil.rmtree(work)
    (work / "input").mkdir(parents=True)
    receipts = {}
    report["smoke"] = receipts
    report["plan"] = "chronological-row-stream smoke v1"

    # 1. Pinned harness clone.
    clone = work / "harness"
    checked_run(["git", "clone", "--quiet", smoke["harness_repo"], str(clone)], timeout=600)
    checked_run(["git", "-C", str(clone), "checkout", "--quiet", smoke["harness_commit"]], timeout=120)
    if subprocess.check_output(["git", "-C", str(clone), "rev-parse", "HEAD"], text=True).strip() != smoke["harness_commit"]:
        raise RuntimeError("harness clone is not at the pinned commit")
    pristine_scorer = work / "original-score_holdout.py"
    shutil.copyfile(clone / "bench" / "score_holdout.py", pristine_scorer)
    stage_log("harness", {"commit": smoke["harness_commit"],
                          "original_scorer_sha256": sha256_file(pristine_scorer)}, receipts)

    # 2. Pinned image build (worker host; no prebuilt registry image exists).
    started = time.monotonic()
    checked_run(["docker", "build", "--quiet", "-t", smoke["image_tag"], str(clone)], timeout=3600)
    identity = json.loads(checked_run(["docker", "image", "inspect", smoke["image_tag"]], timeout=60))
    stage_log("image", {"digest": identity[0]["Id"], "build_seconds": round(time.monotonic() - started, 1)}, receipts)

    # 3. Public release fetch (train/eval/meta/quality/MANIFEST only; never the holdout).
    expected = smoke["expected_sha256"]
    for remote_name, local_name in (("public/train.csv", "train.csv"), ("public/eval.csv", "eval.csv"),
                                     ("meta.json", "meta.json"), ("quality.json", "quality.json")):
        url = (f"https://github.com/earino/{job['dataset']}/releases/download/"
               f"{smoke['release_tag']}/{remote_name}")
        target = work / "input" / local_name
        checked_run(["curl", "-fsSL", "-o", str(target), url], timeout=600)
        digest = sha256_file(target)
        if digest != expected[remote_name]:
            raise RuntimeError(f"digest mismatch for {remote_name}")
        stage_log(f"fetch:{local_name}", digest, receipts)
    manifest_url = f"https://raw.githubusercontent.com/earino/{job['dataset']}/main/MANIFEST.json"
    checked_run(["curl", "-fsSL", "-o", str(work / "input" / "MANIFEST.json"), manifest_url], timeout=120)
    manifest = json.loads((work / "input" / "MANIFEST.json").read_text())
    if manifest["artifact_version"] != smoke["artifact_version"]:
        raise RuntimeError("fetched artifact version differs from the pin")

    # 4. Derivative split (reviewed assumptions; source hashes preserved separately).
    import csv
    with (work / "input" / "train.csv").open(newline="") as stream:
        columns = list(csv.DictReader(stream).fieldnames or [])
    derivative, counts, boundary = derivative_split(work, smoke, columns, smoke["time_column"], smoke["target"])
    stage_log("derivative", {"boundary_month": boundary, "counts": counts,
                             "source_train_sha256": expected["public/train.csv"],
                             "source_eval_sha256": expected["public/eval.csv"],
                             "derivative_train_sha256": sha256_file(derivative / "train.csv"),
                             "derivative_dev_sha256": sha256_file(derivative / "eval.csv"),
                             "test_sha256": sha256_file(derivative / "holdout.csv"),
                             "note": "research derivative of public-train chronology; "
                                     "test = original public eval bytes unchanged; not a historical claim"}, receipts)

    # 5. Gate 1.5 qualification + accept over the three derivative files.
    started = time.monotonic()
    out = checked_run([sys.executable, str(BASE / "source" / "gate" / "qualify_dataset.py"),
                       str(derivative), "--config", str(BASE / "source" / "smoke" / "derivative-descriptor.json"),
                       "--accept"], timeout=3600)
    report["gate_output_tail"] = out[-2000:]
    stage_log("gate", {"seconds": round(time.monotonic() - started, 1), "accepted": "ACCEPTED" in out[-4000:]}, receipts)

    # 6. Host scoring venv + adapter install into the owned clone.
    venv, versions = host_scoring_venv(smoke, work)
    stage_log("host_venv", versions, receipts)
    out = checked_run([sys.executable, str(BASE / "source" / "scripts" / "install-prediction-adapter.py"),
                       "--source", str(clone), "--destination", str(work / "execution")], timeout=300)
    receipt = json.loads(out.strip().splitlines()[-1])
    if receipt["original_scorer_sha256"] != sha256_file(pristine_scorer):
        raise RuntimeError("adapter receipt disagrees with the preserved original scorer")
    stage_log("adapter", receipt, receipts)

    # 7. Candidate stream run: locked-down container, one row at a time, parent-only output.
    workdir = work / "run"
    (workdir / "data").mkdir(parents=True)
    shutil.copyfile(BASE / "source" / "runner" / "train.py", workdir / "train.py")
    shutil.copyfile(BASE / "source" / "runner" / "task.json", workdir / "task.json")
    shutil.copyfile(derivative / "train.csv", workdir / "data" / "train.csv")
    # The development file enters the whitelist ONLY through FACTORY_DEV_EVAL (adapter
    # 9465412 mounts the explicit source as data/eval.csv itself); the scored test file
    # is never present in the candidate workdir in any form.
    env = {**os.environ, "FACTORY_PREDICTION_TIME_COLUMN": smoke["time_column"],
           "FACTORY_DEV_EVAL": str(derivative / "eval.csv"),
           "FACTORY_PREDICTIONS_OUTPUT": str(work / "stream-predictions.json"),
           "BENCH_IMAGE": smoke["image_tag"], "BENCH_THREADS": str(smoke.get("threads", 4)),
           "FACTORY_SCORE_TIMEOUT": str(smoke.get("score_timeout", 7200))}
    started = time.monotonic()
    checked_run([str(venv / "bin" / "python"), str(work / "execution" / "bench" / "score_holdout.py"),
                 str(derivative / "holdout.csv"), smoke["target"], json.dumps(smoke["positive_label"])],
                timeout=smoke.get("score_timeout", 7200) + 600, capture=False)
    stage_log("stream_run", {"seconds": round(time.monotonic() - started, 1),
                             "predictions_sha256": sha256_file(work / "stream-predictions.json")}, receipts)

    # 8. Reference run: TRUSTED container, ordinary full-frame access to the test file.
    refdir = work / "reference"
    (refdir / "data").mkdir(parents=True)
    for source, dest in ((BASE / "source" / "runner" / "train.py", "train.py"),
                         (BASE / "source" / "runner" / "task.json", "task.json"),
                         (derivative / "train.csv", "data/train.csv"),
                         (derivative / "holdout.csv", "data/eval.csv")):
        shutil.copyfile(source, refdir / dest)
    (refdir / "score_reference.py").write_text(REFERENCE_SCRIPT)
    started = time.monotonic()
    out = checked_run(["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
                       "--security-opt", "no-new-privileges", "--pids-limit", "256", "--memory", "4g",
                       "--mount", f"type=bind,src={refdir},dst=/work,readonly",
                       "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m", "-w", "/work",
                       smoke["image_tag"], "python", "-u", "score_reference.py"], timeout=3600)
    (work / "reference-predictions.json").write_text(out.strip().splitlines()[-1])
    stage_log("reference_run", {"seconds": round(time.monotonic() - started, 1)}, receipts)

    # 9. Vector agreement, element-wise. No AUC is computed or reported.
    stream_vec = json.loads((work / "stream-predictions.json").read_text())
    ref_vec = json.loads((work / "reference-predictions.json").read_text())
    if len(stream_vec) != len(ref_vec):
        raise RuntimeError("prediction vectors differ in length")
    deltas = [abs(a - b) for a, b in zip(stream_vec, ref_vec)]
    stage_log("agreement", {"n": len(deltas), "max_abs_delta": max(deltas),
                            "exact_equal": sum(1 for d in deltas if d == 0.0)}, receipts)

    # 10. Negative probes: scored file absent, network refused, whitelist visible.
    probedir = work / "probe"
    probedir.mkdir()
    shutil.copyfile(derivative / "train.csv", probedir / "train.csv")
    out = checked_run(["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                       "--mount", f"type=bind,src={probedir},dst=/work,readonly",
                       smoke["image_tag"], "python", "-c", PROBE_SCRIPT], timeout=300)
    probe = json.loads(out.strip().splitlines()[-1])
    visible = sorted(str(p.relative_to(workdir)) for p in workdir.rglob("*") if p.is_file())
    stage_log("negative_probes", {**probe, "candidate_visible_files": visible}, receipts)
    if not probe["scored_absent"] or not probe["network_refused"]:
        raise RuntimeError("a negative probe did not fail closed")
    unexpected = [f for f in probe["visible_files"] if f not in
                  ("train.py", "task.json", "data/train.csv", "data/eval.csv")]
    if unexpected:
        raise RuntimeError(f"candidate saw unexpected files: {unexpected}")


def main() -> int:
    job = json.loads((BASE / "job.json").read_text())
    report = {"job_id": job["id"], "status": "failed", "uploaded": False}
    try:
        if not job.get("smoke_adapter") or not isinstance(job.get("smoke"), dict):
            raise ValueError("Host operation does not match the job")
        run(job, report)
        report["status"] = "succeeded"
    except Exception as exc:
        report["failure"] = type(exc).__name__
        errno = getattr(exc, "errno", None)
        if type(errno) is int:
            report["failure_errno"] = errno
    raw = json.dumps(report).encode()
    if len(raw) > REPORT_LIMIT:
        raw = json.dumps({"job_id": job["id"], "status": "failed", "uploaded": False,
                          "failure": "host-receipt-too-large"}).encode()
    (BASE / "smoke").mkdir(exist_ok=True)
    (BASE / "smoke" / "result.json").write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
