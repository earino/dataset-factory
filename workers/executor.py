"""Run on an expendable worker, never on Scout. Uses Docker and stdlib only."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import sys
import tempfile

try:
    from .upload import publish, fetch, transfer, UploadError
    from .hf_publish import hf_publish
except ImportError:  # Standalone /opt/scout installation.
    from upload import publish, fetch, transfer, UploadError
    from hf_publish import hf_publish

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


def host_environment(base):
    """Charge client caches and temporary files to the monitored worker directory."""
    cache = base / "host-cache"
    temporary = base / "host-tmp"
    for path in (cache, temporary):
        if path.is_symlink():
            raise ValueError("Host cache path is a symlink")
        path.mkdir(exist_ok=True)
    return {**os.environ, "TMPDIR": str(temporary), "TMP": str(temporary),
            "TEMP": str(temporary), "XDG_CACHE_HOME": str(cache),
            "UV_CACHE_DIR": str(cache / "uv"),
            "UV_PYTHON_INSTALL_DIR": str(cache / "uv-python"),
            "PIP_CACHE_DIR": str(cache / "pip"),
            "HF_HOME": str(cache / "huggingface"),
            "HF_XET_CACHE": str(cache / "huggingface" / "xet"),
            "HF_ASSETS_CACHE": str(cache / "huggingface" / "assets"),
            "HF_HUB_CACHE": str(cache / "huggingface" / "hub"),
            "HF_DATASETS_CACHE": str(cache / "huggingface" / "datasets")}


def host_limit_reason(base, job, deadline, baseline):
    if time.monotonic() >= deadline:
        return "runtime-limit"
    free = shutil.disk_usage(base).free
    # Check external writes before the directory walk; installers and low free
    # space can trip the guard without waiting for a potentially slow du.
    filesystem_charge = baseline[0] + max(0, baseline[1] - free)
    if free < 512 * 1024**2 or filesystem_charge > job["max_disk_mb"] * 1024**2:
        return "disk-limit"
    if disk_bytes(base) > job["max_disk_mb"] * 1024**2:
        return "disk-limit"
    # du itself is bounded, but may have consumed the remaining runtime.
    return "runtime-limit" if time.monotonic() >= deadline else None


def live_group_members(pgid, proc_root=None):
    if proc_root is not None or sys.platform == "linux":
        # Linux workers already require procfs. Avoid adding procps/ps as an
        # unverified package prerequisite. comm may itself contain parentheses.
        root = Path(proc_root) if proc_root is not None else Path("/proc")
        for path in root.iterdir():
            if not path.name.isdigit():
                continue
            try:
                with (path / "stat").open() as handle:
                    raw = handle.read(4097)
            except (FileNotFoundError, ProcessLookupError):
                continue  # A process exited during the scan.
            fields = raw.rsplit(")", 1)[-1].split()
            if (len(raw) > 4096 or not raw.startswith(f"{path.name} (") or ")" not in raw
                    or len(fields) < 3 or not fields[2].isdigit()):
                raise ValueError("Unreadable procfs process state")
            if int(fields[2]) == pgid and fields[0] != "Z":
                return True
        return False
    # Portable development-host fallback, not used on the Linux workers.
    listing = subprocess.check_output(["ps", "-A", "-o", "pgid=,stat="],
                                      text=True, timeout=3)
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[0].isdigit():
            raise ValueError("Unreadable process-group state")
        if int(fields[0]) == pgid and not fields[1].startswith("Z"):
            return True
    return False


def stop_unreaped_group(process):
    """Keep the leader unreaped until no live group member can change artifacts."""
    deadline = time.monotonic() + 5
    while True:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except PermissionError:
            # Darwin returns EPERM for zombie-only groups. Never ignore it
            # when a live member remains. PID is still reserved by the leader.
            if live_group_members(process.pid):
                raise
            return
        if not live_group_members(process.pid):
            return
        if time.monotonic() >= deadline:
            raise ValueError("Host process group did not stop")
        # Re-signal a child forked during the previous signal-delivery window.
        time.sleep(.05)


def supervise_host(base, job, command, receipt, deadline, interval=1.0):
    """Monitor one worker-host process group; retain its PID until cleanup.

    Disk enforcement is sampled, like the container monitor, not a filesystem
    quota: writes may overshoot between checks. No model or network calls here.
    """
    report = {"job_id": job["id"], "status": "failed", "uploaded": False}
    report["host_cleanup_complete"] = True
    process = None
    failure = None
    try:
        env = host_environment(base)
        baseline = (disk_bytes(base), shutil.disk_usage(base).free)
        failure = host_limit_reason(base, job, deadline, baseline)
        if failure:
            return {**report, "failure": failure}
        live_group_members(-1)  # Validate observation capability before starting.
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, env=env, start_new_session=True)
        report["host_process_pid"] = process.pid
        while True:
            # WNOWAIT observes exit without reaping. Even on normal completion,
            # the PID cannot be recycled before we stop remaining group members.
            exited = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            failure = host_limit_reason(base, job, deadline, baseline)
            if failure or exited is not None:
                break
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        failure = f"resource-monitor-failed:{type(exc).__name__}"
    finally:
        if process is not None:
            try:
                stop_unreaped_group(process)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                failure = f"host-cleanup-failed:{type(exc).__name__}"
                report["host_cleanup_complete"] = False
                process.kill()  # Exact unreaped direct child; no group-ID retry.
            finally:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    failure = "host-cleanup-incomplete"
                    report["host_cleanup_complete"] = False
    if failure:
        return {**report, "failure": failure}
    if process.returncode != 0:
        return {**report, "failure": "host-operation-failed", "exit_code": process.returncode}
    try:
        if (receipt.is_symlink() or not receipt.is_file()
                or receipt.stat().st_size > REPORT_LIMIT):
            raise ValueError("Invalid compact receipt")
        result = json.loads(receipt.read_bytes())
        if (not isinstance(result, dict) or result.get("job_id") != job["id"]
                or result.get("status") not in ("succeeded", "failed")
                or result.get("uploaded") is not False):
            raise ValueError("Invalid host result")
        result.update(host_cleanup_complete=True, host_process_pid=process.pid)
        return result
    except (OSError, ValueError):
        return {**report, "failure": "invalid-host-receipt"}


def execute_host(base, job, operation, deadline):
    # A fresh private directory prevents a stale or partially written receipt from
    # impersonating completion. Cleanup is scoped to this newly owned directory.
    with tempfile.TemporaryDirectory(prefix=".host-operation-", dir=base) as temporary:
        receipt = Path(temporary) / "result.json"
        command = [sys.executable, str(Path(__file__).resolve()), "--host-operation", operation,
                   "--base", str(base.resolve()), "--receipt", str(receipt.resolve())]
        return supervise_host(base, job, command, receipt, deadline)


def host_child(base, operation, receipt):
    job = json.loads((base / "job.json").read_text())
    report = {"job_id": job["id"], "status": "failed", "uploaded": False}
    try:
        if operation == "transfer" and job.get("transfer"):
            transfer(base, job, report)
            report["status"] = "succeeded"
        elif operation == "hf_publish" and job.get("hf_publish"):
            hf_publish(base, job, report)
            report["status"] = "succeeded" if not report["hf_publish"]["failures"] else "failed"
        else:
            raise ValueError("Host operation does not match the job")
    except Exception as exc:
        # Raw exceptions may include credential-bearing URLs or helper arguments.
        report.update(status="failed", failure=type(exc).__name__, failure_stage=operation)
        if type(getattr(exc, "errno", None)) is int:
            report["failure_errno"] = exc.errno
    raw = json.dumps(report).encode()
    if len(raw) > REPORT_LIMIT:
        raw = json.dumps({"job_id": job["id"], "status": "failed", "uploaded": False,
                          "failure": "host-receipt-too-large"}).encode()
    receipt.write_bytes(raw)
    return 0


def execute(base, job):
    name = "scout-" + job["id"]
    report = {"job_id": job["id"], "status": "failed", "uploaded": False}
    started = time.monotonic()
    log = base / "container.log"
    log.touch()
    # Host operations used to return before reaching any resource monitor.
    # Their outer deadline includes client bootstrap, downloads and retry waits.
    if job.get("transfer") or job.get("hf_publish"):
        operation = "transfer" if job.get("transfer") else "hf_publish"
        report = execute_host(base, job, operation, started + job["timeout_minutes"] * 60)
        report["elapsed_seconds"] = round(time.monotonic() - started, 1)
        return report
    try:
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
        if report.get("host_cleanup_complete") is False:
            # No upload can establish stable artifact digests while a host
            # process may still be changing files. Keep bounded evidence local.
            report.update(uploaded=False, upload_error="host cleanup incomplete; inspect worker")
            write_report(base, report)
            return 1
        try:
            report.update(publish(base, job, report))
        except Exception as exc:
            report.update(uploaded=False, upload_error=str(exc) if isinstance(exc, UploadError) else type(exc).__name__)
        write_report(base, report)
        return 0 if report.get("uploaded") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-operation", choices=("transfer", "hf_publish"))
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if args.host_operation:
        if args.receipt is None:
            parser.error("--receipt is required for a host operation")
        os.umask(0o077)
        raise SystemExit(host_child(args.base, args.host_operation, args.receipt))
    raise SystemExit(main(args.base))
