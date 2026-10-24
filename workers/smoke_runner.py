"""Host-side adapter smoke runner (issue #17). Runs on an expendable worker only.

Executes the complete integration smoke for the prediction-time contract:
materializes pinned sources, builds the image, creates the three-derivative
split with metadata, qualifies through gate 1.5 two-phase, runs streamed and
reference inference, asserts vector agreement, and executes negative
isolation probes against the actual adapter staging directory. Receipts go
to the executor's expected path; failures propagate through the host_child
contract.

Per issue #17 comment 6384184939:
- No harness clone on the worker. The bundle carries encoded source bytes;
  materialization verifies every sha256 before writing.
- Three FULL derivative files: train' = public train minus final N months,
  dev = that tail (the only eval-role file the candidate sees), test =
  original public eval bytes unchanged (scorer-owned, never candidate-visible).
- The published private holdout is never fetched.
- Gate 1.5 two-phase: qualify --report then --accept.
- Reference inference in a separate trusted container gets identical train'
  and dev for fitting, plus the scored test for prediction; the stream
  candidate gets the same train' and dev but never the test.
- Negative probes test the actual adapter staging directory, not an
  unrelated container.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

BASE = Path("/opt/scout")
REPORT_LIMIT = 200_000


# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_run(command, timeout, *, env=None, cwd=None, limit=10 * 1024 * 1024):
    """Run a command, fail on nonzero exit, and bound captured output to `limit` bytes."""
    with tempfile.SpooledTemporaryFile(max_size=limit) as out_file, \
         tempfile.SpooledTemporaryFile(max_size=limit) as err_file:
        proc = subprocess.run(command, timeout=timeout, env=env, cwd=cwd,
                               stdout=out_file, stderr=err_file)
        out_file.seek(0)
        err_file.seek(0)
        stdout = out_file.read(limit).decode("utf-8", errors="replace")
        stderr = err_file.read(limit).decode("utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(f"command failed ({proc.returncode}): {command[:3]}...; "
                               f"stderr: {stderr[-300:]}")
        return stdout


def stage_log(stage: str, detail, receipts: dict) -> None:
    value = detail if isinstance(detail, (str, int, float, bool)) else json.dumps(detail, sort_keys=True)
    receipts[stage] = value
    print(f"[smoke] {stage}: {value}", flush=True)


def owned_directory(base: Path, name: str) -> Path:
    """Create or reuse a directory with an ownership marker; refuse foreign paths."""
    path = base / name
    if path.exists():
        marker = path / ".smoke-owned"
        if not marker.is_file():
            raise RuntimeError(f"{path} exists without an ownership marker; refusing to overwrite")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / ".smoke-owned").write_text("owned by smoke_runner\n")
    return path


# ---------------------------------------------------------------------------
# Pinned-source materialization (no harness clone)
# ---------------------------------------------------------------------------

def materialize_pinned(job: dict, work: Path) -> dict:
    """Write encoded source bytes from the bundle, verifying every sha256 first.

    The bundle directory /opt/scout/source/pinned/ carries each file with its
    sha256 recorded in the job spec. No network, no git, no tar extraction.
    """
    smoke = job["smoke"]
    bundle_pinned = BASE / "source" / "pinned"
    sources = {}
    for filename, expected_sha in sorted(smoke.get("pinned_sources", {}).items()):
        encoded = bundle_pinned / filename
        if encoded.is_symlink() or not encoded.is_file():
            raise RuntimeError(f"pinned source not in bundle: {filename}")
        raw = encoded.read_bytes()
        actual = sha256_bytes(raw)
        if actual != expected_sha:
            raise RuntimeError(f"pinned source {filename}: sha256 mismatch "
                               f"(expected {expected_sha[:16]}, got {actual[:16]})")
        sources[filename] = raw
    if not sources:
        raise RuntimeError("job carries no pinned_sources; nothing to materialize")
    return sources


def resolve_lock_versions(raw_lock: bytes) -> dict:
    """Parse the harness uv.lock (TOML) for the host venv's package versions."""
    lock = tomllib.loads(raw_lock.decode("utf-8"))
    needed = {"numpy", "pandas", "scikit-learn"}
    found = {}
    packages = lock.get("package", [])
    if not isinstance(packages, list):
        raise RuntimeError("lock 'package' is not an array of tables")
    for package in packages:
        if not isinstance(package, dict):
            continue
        name = package.get("name", "")
        if name in needed:
            found[name] = package["version"]
    if set(found) != needed:
        raise RuntimeError(f"lock missing packages: {sorted(needed - set(found))}")
    return found


# ---------------------------------------------------------------------------
# Derivative split
# ---------------------------------------------------------------------------

def derivative_split(input_dir: Path, output_dir: Path, time_col: str, target: str,
                     positive_label: int, dev_months: int) -> dict:
    """Split public train into train' and dev by chronological tail; copy eval unchanged.

    Two streaming passes; O(1) Python memory. Months are calendar-sorted.
    File handles are passed to csv.DictWriter, not Path objects.
    """
    train_csv = input_dir / "train.csv"
    months = set()
    with train_csv.open(newline="") as stream:
        for row in csv.DictReader(stream):
            months.add(row[time_col][:7])
    if len(months) <= dev_months:
        raise RuntimeError(f"train has {len(months)} months; need at least {dev_months + 1}")
    boundary = sorted(months)[-dev_months]

    public_dir = output_dir / "public"
    private_dir = output_dir / "private"
    public_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)
    train_out = public_dir / "train.csv"
    dev_out = public_dir / "eval.csv"
    test_out = private_dir / "holdout.csv"

    counts = {"train": {"rows": 0, "positives": 0}, "dev": {"rows": 0, "positives": 0}}
    with train_csv.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise RuntimeError("train.csv has no header row")
        with train_out.open("w", newline="") as train_handle, \
             dev_out.open("w", newline="") as dev_handle:
            train_writer = csv.DictWriter(train_handle, fieldnames=list(fieldnames))
            dev_writer = csv.DictWriter(dev_handle, fieldnames=list(fieldnames))
            train_writer.writeheader()
            dev_writer.writeheader()
            for row in reader:
                if row[time_col][:7] >= boundary:
                    dev_writer.writerow(row)
                    counts["dev"]["rows"] += 1
                    if row[target] == str(positive_label):
                        counts["dev"]["positives"] += 1
                else:
                    train_writer.writerow(row)
                    counts["train"]["rows"] += 1
                    if row[target] == str(positive_label):
                        counts["train"]["positives"] += 1

    shutil.copyfile(input_dir / "eval.csv", test_out)
    return {
        "boundary_month": boundary,
        "counts": counts,
        "train_sha256": sha256_file(train_out),
        "dev_sha256": sha256_file(dev_out),
        "test_sha256": sha256_file(test_out),
        "source_train_sha256": sha256_file(train_csv),
        "source_eval_sha256": sha256_file(input_dir / "eval.csv"),
    }


def write_derivative_metadata(output_dir: Path, split_info: dict, smoke: dict) -> None:
    """Write meta.json and quality.json for the derivative research artifact."""
    meta = {
        "name": smoke["dataset"],
        "release_tag": f"smoke-derivative-{smoke['release_tag']}",
        "splits": {
            "train": {"rows": split_info["counts"]["train"]["rows"],
                      "positives": split_info["counts"]["train"]["positives"]},
            "eval": {"rows": split_info["counts"]["dev"]["rows"],
                     "positives": split_info["counts"]["dev"]["positives"]},
        },
        "id_columns": smoke.get("id_columns", ["row_id"]),
        "target": smoke["target"],
        "positive_label": smoke["positive_label"],
        "time_column": smoke["time_column"],
    }
    (output_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    quality = {
        "task": {
            "prediction_time": f"before the target, determined by {smoke['time_column']}",
            "time_column": smoke["time_column"],
            "event_key_column": smoke.get("event_key_column", smoke["time_column"]),
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "feature_evidence": "All features are trailing aggregates of the source panel; "
                               "availability at the prediction instant is assumed, not vintage-verified.",
            "vintage": {"kind": "current_snapshot",
                        "evidence": "Single download of the public release; no historical vintages."},
            "selection": {"kind": "outcome_conditioned",
                          "evidence": "Rows require the source panel to extend through the target period."},
            "limitations": [
                "Smoke derivative of a published release; not a historical claim.",
                "Feature availability at the declared instant is assumed from a current snapshot.",
                "Training label timing is unverified.",
            ],
            "training_label_timing": "unverified",
        },
        "split_windows": {
            "train": {"end": split_info["boundary_month"]},
            "eval": {"start": split_info["boundary_month"]},
            "holdout": {"sealed": True},
        },
    }
    (output_dir / "quality.json").write_text(json.dumps(quality, indent=2) + "\n")


# ---------------------------------------------------------------------------
# The smoke run
# ---------------------------------------------------------------------------

def smoke_run(base: Path, job: dict, report: dict) -> None:
    smoke = job["smoke"]
    work = owned_directory(base, "smoke-work")
    receipts = {}
    report["smoke"] = receipts
    report["plan"] = "chronological-row-stream smoke v2"

    # 1. Materialize pinned sources (adapter, gate, Dockerfile context, runner).
    sources = materialize_pinned(job, work)
    stage_log("pinned_sources", f"{len(sources)} files sha-verified", receipts)

    # 2. Build the image from the materialized Dockerfile context.
    image_context = work / "image-context"
    image_context.mkdir()
    for name, raw in sources.items():
        if name.startswith("image/"):
            (image_context / name[len("image/"):]).write_bytes(raw)
    if not (image_context / "Dockerfile").is_file():
        raise RuntimeError("pinned sources do not carry image/Dockerfile")
    image_tag = smoke["image_tag"]
    started = time.monotonic()
    checked_run(["docker", "build", "--quiet", "-t", image_tag, str(image_context)], timeout=3600)
    identity = json.loads(checked_run(["docker", "image", "inspect", image_tag], timeout=60))
    receipts["image"] = {"digest": identity[0]["Id"],
                          "build_seconds": round(time.monotonic() - started, 1)}
    stage_log("image", identity[0]["Id"][:32], receipts)

    # 3. Host scoring venv from the pinned uv.lock (tomllib, not regex).
    lock_raw = sources.get("image/uv.lock")
    if not lock_raw:
        raise RuntimeError("pinned sources do not carry image/uv.lock")
    versions = resolve_lock_versions(lock_raw)
    venv = work / "host-venv"
    started = time.monotonic()
    checked_run([sys.executable, "-m", "venv", str(venv)], timeout=300)
    checked_run([str(venv / "bin" / "pip"), "install", "--quiet", "--disable-pip-version-check",
                 f"numpy=={versions['numpy']}", f"pandas=={versions['pandas']}",
                 f"scikit-learn=={versions['scikit-learn']}"], timeout=900)
    receipts["host_venv"] = {**versions, "seconds": round(time.monotonic() - started, 1)}
    stage_log("host_venv", str(versions), receipts)

    # 4. Fetch Austin public assets (train/eval/meta/quality; never the holdout).
    input_dir = owned_directory(work, "input")
    expected = smoke["expected_sha256"]
    for remote_name, local_name in (("public/train.csv", "train.csv"),
                                    ("public/eval.csv", "eval.csv"),
                                    ("meta.json", "meta.json"),
                                    ("quality.json", "quality.json")):
        url = (f"https://github.com/earino/{job['dataset']}/releases/download/"
               f"{smoke['release_tag']}/{remote_name}")
        target = input_dir / local_name
        checked_run(["curl", "-fsSL", "-o", str(target), url], timeout=600)
        actual = sha256_file(target)
        if actual != expected[remote_name]:
            raise RuntimeError(f"digest mismatch for {remote_name}: "
                               f"expected {expected[remote_name][:16]}, got {actual[:16]}")
        receipts[f"fetch:{local_name}"] = actual[:16]
    stage_log("fetch", "4/4 verified", receipts)

    # 5. Create the three-derivative split with metadata.
    derivative_dir = owned_directory(work, "derivative")
    split_info = derivative_split(input_dir, derivative_dir, smoke["time_column"],
                                  smoke["target"], smoke["positive_label"], smoke["dev_months"])
    write_derivative_metadata(derivative_dir, split_info, smoke)
    receipts["derivative"] = split_info
    stage_log("derivative", f"boundary={split_info['boundary_month']} "
              f"train={split_info['counts']['train']['rows']} dev={split_info['counts']['dev']['rows']}", receipts)

    # 6. Gate 1.5 qualification: two-phase (qualify --report, then --accept).
    gate_raw = sources.get("gate/qualify_dataset.py")
    if not gate_raw:
        raise RuntimeError("pinned sources do not carry gate/qualify_dataset.py")
    gate_dir = work / "gate"
    gate_dir.mkdir()
    (gate_dir / "qualify_dataset.py").write_bytes(gate_raw)
    gate_report = work / "gate-report.json"
    started = time.monotonic()
    checked_run([sys.executable, str(gate_dir / "qualify_dataset.py"),
                 str(derivative_dir), "--report", str(gate_report)], timeout=3600)
    if not gate_report.is_file():
        raise RuntimeError("gate did not write a report")
    gate_payload = json.loads(gate_report.read_text())
    if gate_payload.get("ok") is not True:
        raise RuntimeError(f"gate qualification failed: {gate_payload.get('failed_checks', [])}")
    receipts["gate_qualify"] = {"ok": True, "seconds": round(time.monotonic() - started, 1),
                                 "failed_checks": gate_payload.get("failed_checks", [])}
    stage_log("gate_qualify", "ok", receipts)

    started = time.monotonic()
    accept_out = checked_run([sys.executable, str(gate_dir / "qualify_dataset.py"),
                              "--accept", str(gate_report), str(derivative_dir)], timeout=3600)
    if "ACCEPTED" not in accept_out:
        raise RuntimeError(f"gate acceptance failed: {accept_out[-200:]}")
    receipts["gate_accept"] = {"accepted": True, "seconds": round(time.monotonic() - started, 1)}
    stage_log("gate_accept", "ACCEPTED", receipts)

    # 7. Materialize the adapter into an owned execution directory.
    adapter_raw = sources.get("adapters/score_holdout.py")
    if not adapter_raw:
        raise RuntimeError("pinned sources do not carry adapters/score_holdout.py")
    harness_exec = owned_directory(work, "execution")
    bench_dir = harness_exec / "bench"
    bench_dir.mkdir()
    (bench_dir / "score_holdout.py").write_bytes(adapter_raw)
    receipts["adapter"] = {"sha256": sha256_bytes(adapter_raw)[:16]}
    stage_log("adapter", receipts["adapter"]["sha256"], receipts)

    # 8. Stream run: the candidate gets only the four whitelisted files.
    stream_dir = owned_directory(work, "stream-workdir")
    (stream_dir / "data").mkdir()
    shutil.copyfile(derivative_dir / "public" / "train.csv", stream_dir / "data" / "train.csv")
    shutil.copyfile(derivative_dir / "public" / "eval.csv", stream_dir / "data" / "eval.csv")
    for name in ("runner/train.py", "runner/task.json"):
        if name not in sources:
            raise RuntimeError(f"pinned sources do not carry {name}")
        (stream_dir / name.split("/")[1]).write_bytes(sources[name])

    predictions_path = work / "stream-predictions.json"
    stream_env = {
        **os.environ,
        "FACTORY_PREDICTION_TIME_COLUMN": smoke["time_column"],
        "FACTORY_DEV_EVAL": str(derivative_dir / "public" / "eval.csv"),
        "FACTORY_PREDICTIONS_OUTPUT": str(predictions_path),
        "BENCH_IMAGE": image_tag,
        "BENCH_THREADS": str(smoke.get("threads", 4)),
        "FACTORY_SCORE_TIMEOUT": str(smoke.get("score_timeout", 7200)),
    }
    started = time.monotonic()
    checked_run([str(venv / "bin" / "python"), str(bench_dir / "score_holdout.py"),
                 str(derivative_dir / "private" / "holdout.csv"),
                 smoke["target"], json.dumps(smoke["positive_label"])],
                timeout=smoke.get("score_timeout", 7200) + 600,
                env=stream_env, cwd=str(stream_dir))
    if not predictions_path.is_file():
        raise RuntimeError("stream run did not produce ordered predictions")
    stream_vec = json.loads(predictions_path.read_text())
    receipts["stream_run"] = {"seconds": round(time.monotonic() - started, 1),
                               "n_predictions": len(stream_vec),
                               "predictions_sha256": sha256_bytes(predictions_path.read_bytes())[:16]}
    stage_log("stream_run", f"n={len(stream_vec)}", receipts)

    # 9. Reference run: trusted container, identical train'+dev for fitting,
    #    scored test mounted separately; Docker ENTRYPOINT overridden.
    ref_dir = owned_directory(work, "reference-workdir")
    (ref_dir / "data").mkdir()
    shutil.copyfile(derivative_dir / "public" / "train.csv", ref_dir / "data" / "train.csv")
    shutil.copyfile(derivative_dir / "public" / "eval.csv", ref_dir / "data" / "eval.csv")
    shutil.copyfile(derivative_dir / "private" / "holdout.csv", ref_dir / "data" / "test.csv")
    for name in ("runner/train.py", "runner/task.json"):
        (ref_dir / name.split("/")[1]).write_bytes(sources[name])

    reference_script = work / "reference_check.py"
    reference_script.write_text(REFERENCE_SCRIPT)
    started = time.monotonic()
    ref_output = checked_run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "--security-opt", "no-new-privileges", "--pids-limit", "256",
         "--memory", "4g", "--read-only",
         "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
         "--mount", f"type=bind,src={ref_dir},dst=/work,readonly",
         "--entrypoint", "python", "-w", "/work", image_tag,
         str(reference_script)],
        timeout=3600)
    ref_vec = json.loads(ref_output.strip().splitlines()[-1])
    receipts["reference_run"] = {"seconds": round(time.monotonic() - started, 1),
                                  "n_predictions": len(ref_vec)}
    stage_log("reference_run", f"n={len(ref_vec)}", receipts)

    # 10. Assert vector agreement against the predeclared tolerance.
    if len(stream_vec) != len(ref_vec):
        raise RuntimeError(f"prediction vectors differ in length: {len(stream_vec)} vs {len(ref_vec)}")
    tolerance = smoke.get("tolerance", 1e-12)
    max_delta = max(abs(a - b) for a, b in zip(stream_vec, ref_vec))
    exact = sum(1 for a, b in zip(stream_vec, ref_vec) if a == b)
    if max_delta > tolerance:
        raise RuntimeError(f"vector agreement failed: max |delta| {max_delta} > tolerance {tolerance}")
    receipts["agreement"] = {"n": len(stream_vec), "max_abs_delta": max_delta,
                              "exact_equal": exact, "tolerance": tolerance, "passed": True}
    stage_log("agreement", f"max_delta={max_delta:.2e} exact={exact}/{len(stream_vec)}", receipts)

    # 11. Negative probes against the actual adapter staging directory.
    probes = {}
    scored_leaks = list(stream_dir.rglob("holdout*")) + list(stream_dir.rglob("test.csv"))
    probes["scored_file_absent_from_staging"] = len(scored_leaks) == 0
    expected_files = {"train.py", "task.json", "data/train.csv", "data/eval.csv"}
    actual_files = {str(p.relative_to(stream_dir)) for p in stream_dir.rglob("*")
                    if p.is_file() and not p.name.startswith(".")}
    probes["whitelist_exact"] = actual_files == expected_files
    if not probes["whitelist_exact"]:
        probes["actual_files"] = sorted(actual_files)
    receipts["negative_probes"] = probes
    if not all(probes.values()):
        raise RuntimeError(f"negative probes failed: {probes}")
    stage_log("negative_probes", str(probes), receipts)


REFERENCE_SCRIPT = '''\
import contextlib, importlib.util, io, json, sys
import numpy as np
import pandas as pd

with contextlib.redirect_stdout(sys.stderr):
    spec = importlib.util.spec_from_file_location("train", "/work/train.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
fn = mod.predict_proba
if not callable(fn):
    raise RuntimeError("no predict_proba in train.py")

test = pd.read_csv("/work/data/test.csv")
with contextlib.redirect_stdout(sys.stderr):
    probabilities = [float(p) for p in np.asarray(fn(test), dtype=float).ravel()]
print(json.dumps(probabilities))
'''


# ---------------------------------------------------------------------------
# Executor contract: called from executor.py host_child with --base and --receipt
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if args.receipt is None:
        parser.error("--receipt is required")

    os.umask(0o077)
    job = json.loads((args.base / "job.json").read_text())
    report = {"job_id": job["id"], "status": "failed", "uploaded": False}
    try:
        if not job.get("smoke_adapter") or not isinstance(job.get("smoke"), dict):
            raise ValueError("Host operation does not match the job")
        smoke_run(args.base, job, report)
        report["status"] = "succeeded"
    except Exception as exc:
        report["failure"] = type(exc).__name__
        report["failure_detail"] = str(exc)[:500]
        errno = getattr(exc, "errno", None)
        if type(errno) is int:
            report["failure_errno"] = errno

    raw = json.dumps(report).encode()
    if len(raw) > REPORT_LIMIT:
        raw = json.dumps({"job_id": job["id"], "status": "failed", "uploaded": False,
                          "failure": "host-receipt-too-large"}).encode()
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
