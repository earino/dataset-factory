"""Run on an expendable worker, never on Scout. Uses Docker and stdlib only."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

try:
    from .upload import publish, fetch, transfer, UploadError
except ImportError:  # Standalone /opt/scout installation.
    from upload import publish, fetch, transfer, UploadError

BASE = Path("/opt/scout")
REPORT_LIMIT = 262144


def write_report(base, report):
    raw = json.dumps(report, indent=2).encode()
    if len(raw) > REPORT_LIMIT:
        raise RuntimeError("Compact report exceeds 256 KiB")
    temporary = base / ".result.tmp"
    temporary.write_bytes(raw)
    temporary.replace(base / "result.json")


def disk_bytes(path):
    # du counts hidden files and avoids reading data into memory.
    return int(subprocess.check_output(["du", "-sb", str(path)], timeout=10).split()[0])


def stop_and_capture(base, name):
    subprocess.run(["docker", "kill", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    state = subprocess.run(["docker", "inspect", name], capture_output=True, timeout=30)
    if state.returncode == 0 and json.loads(state.stdout)[0]["State"]["Running"]:
        raise RuntimeError("Container did not stop; do not upload changing artifacts")
    with (base / "container.log").open("wb") as stream:
        process = subprocess.Popen(["docker", "logs", "--tail=2000", name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            stream.write(process.stdout.read(1024**2))
        finally:
            process.kill()
            process.wait(timeout=10)
            process.stdout.close()
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)


def execute(base, job):
    name = "scout-" + job["id"]
    report = {"job_id": job["id"], "status": "failed", "uploaded": False}
    started = time.monotonic()
    log = base / "container.log"
    log.touch()
    try:
        if job.get("transfer"):
            # No container: this job moves already-built artifacts between releases. The bytes
            # are verified twice (on arrival and by the server's own digest after upload), so a
            # repeat run is idempotent and an interrupted one is safe to redispatch.
            transfer(base, job, report)
            report["status"] = "succeeded"
            return report
        if job.get("fetch"):
            # Download the released artifact before starting the container, so a job can measure
            # the published bytes rather than rebuilding them.
            fetch(base, job, report)
        subprocess.run(["docker", "pull", job["image"]], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True, timeout=300)
        identity = json.loads(subprocess.check_output(["docker", "image", "inspect", job["image"]], timeout=30))[0]
        report["image_id"] = identity["Id"]
        report["image_digests"] = identity.get("RepoDigests", [])
        args = ["docker", "run", "--detach", "--name", name, "--init", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--pids-limit=256", "--cpus", str(job["cpus"]),
                "--memory", f"{job['memory_mb']}m", "--memory-swap", f"{job['memory_mb']}m",
                "--log-driver=local", "--log-opt=max-size=1m", "--log-opt=max-file=2",
                "--mount", f"type=bind,src={base / 'source'},dst=/workspace,readonly",
                "--mount", f"type=bind,src={base / 'output'},dst=/output"]
        if job.get("fetch"):
            # The fetched artifact, read-only, without the container ever holding a credential.
            args += ["--mount", f"type=bind,src={base / 'cache'},dst=/data,readonly"]
        args += ["--workdir", "/workspace",
                 "--env", "PYTHONDONTWRITEBYTECODE=1", job["image"], *job["command"]]
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
        deadline = time.monotonic() + job["timeout_minutes"] * 60
        while True:
            details = json.loads(subprocess.check_output(["docker", "inspect", "--size", name], timeout=30))[0]
            if not details["State"]["Running"]:
                report.update(exit_code=details["State"]["ExitCode"],
                              status="succeeded" if details["State"]["ExitCode"] == 0 else "failed",
                              oom_killed=details["State"]["OOMKilled"])
                break
            used = disk_bytes(base) + details.get("SizeRw", 0)
            if time.monotonic() >= deadline:
                report["failure"] = "runtime-limit"
                break
            if used > job["max_disk_mb"] * 1024**2 or shutil.disk_usage(base).free < 512 * 1024**2:
                report["failure"] = "disk-limit"
                break
            time.sleep(3)
    except (OSError, ValueError, subprocess.SubprocessError, UploadError) as exc:
        # UploadError included on purpose: a credential or repository problem inside a transfer or
        # a fetch must still produce a report, or the job dies without any evidence on the worker.
        report["failure"] = type(exc).__name__  # No raw credential-bearing command output.
    finally:
        stop_and_capture(base, name)
    report["elapsed_seconds"] = round(time.monotonic() - started, 1)
    summary = base / "output" / "summary.json"
    if summary.is_file() and not summary.is_symlink() and summary.stat().st_size <= 65536:
        try:
            report["summary"] = json.loads(summary.read_text())
        except (OSError, ValueError):
            report["summary_error"] = "Invalid summary.json; inspect uploaded artifacts"
    return report


def main(base=BASE):
    os.umask(0o077)
    with (base / "executor.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        job = json.loads((base / "job.json").read_text())
        execution = base / "execution.json"
        if execution.exists():
            report = json.loads(execution.read_text())
        elif (base / "started").exists():
            # A process/VM restart must never silently rerun a possibly completed job.
            report = {"job_id": job["id"], "status": "failed", "uploaded": False,
                      "failure": "executor-interrupted; job was not rerun"}
            stop_and_capture(base, "scout-" + job["id"])
            execution.write_text(json.dumps(report))
        else:
            (base / "started").touch()
            report = execute(base, job)
            execution.write_text(json.dumps(report))
        try:
            report.update(publish(base, job, report))
        except Exception as exc:
            report.update(uploaded=False, upload_error=str(exc) if isinstance(exc, UploadError) else type(exc).__name__)
        write_report(base, report)
        return 0 if report.get("uploaded") else 1


if __name__ == "__main__":
    raise SystemExit(main())
