"""One-coordinator worker lifecycle. Heavy data never traverses this host."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

from .cloud import Cloud
from .common import FactoryError, identifier, locked, read_json, utcnow, write_json
from .http import API, secret

REPORT_LIMIT = 262144
BUNDLE_LIMIT = 2 * 1024 * 1024


def number(value, name, positive=True):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise FactoryError(f"{name} must be a number") from None
    if not result.is_finite() or (result <= 0 if positive else result < 0):
        raise FactoryError(f"Invalid {name}")
    return result


def validate(job, config):
    identifier(job["id"])
    identifier(config["project"])
    identifier(job["candidate"])
    if job["server_type"] not in config["server_types"] or job["location"] not in config["allowed_locations"]:
        raise FactoryError("Worker type/location is not in the configured allowance")
    for key in ("cpus", "memory_mb", "timeout_minutes", "lifetime_minutes", "max_disk_mb", "max_artifact_mb"):
        if type(job[key]) is not int or job[key] <= 0:
            raise FactoryError(f"{key} must be a positive integer")
    if job["timeout_minutes"] > config["max_job_minutes"]:
        raise FactoryError("Job runtime exceeds policy")
    if not job["timeout_minutes"] + 15 <= job["lifetime_minutes"] <= config["max_lifetime_minutes"]:
        raise FactoryError("Lifetime must include at least 15 minutes for boot/upload and fit policy")
    # A transfer job moves already-built artifacts between releases and runs no container, so it
    # needs no argv and no image; everything else is validated the same way.
    runs_container = not job.get("transfer")
    command = job.get("command")
    if runs_container and (not isinstance(command, list) or not command
                           or not all(isinstance(x, str) and x and "\0" not in x
                                      for x in command)):
        raise FactoryError("command must be a nonempty argv array")
    image = job.get("image")
    if runs_container and (not isinstance(image, str)
                           or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:@-]*", image)):
        raise FactoryError("Invalid Docker image reference")
    for key in ("transfer", "fetch"):
        if key not in job:
            continue
        spec = job[key]
        required = (("source_repo", "target_repo", "target_release", "assets")
                    if key == "transfer" else ("repo", "assets"))
        missing = [name for name in required if name not in spec]
        if missing:
            raise FactoryError(f"{key} spec is missing {missing}")
        if not isinstance(spec["assets"], list) or not spec["assets"]:
            raise FactoryError(f"{key} spec needs a non-empty assets list")
        for item in spec["assets"]:
            keys = (("source_asset_id", "target_name", "size", "sha256")
                    if key == "transfer" else ("asset_id", "dest", "sha256"))
            absent = [name for name in keys if name not in item]
            if absent:
                raise FactoryError(f"{key} asset entry is missing {absent}")
    if config["max_workers"] != 1:
        raise FactoryError("This first version supports one worker at a time")
    if not 1 <= config["max_report_bytes"] <= REPORT_LIMIT:
        raise FactoryError("Report limit must be at most 256 KiB")
    if not 1 <= config["max_coordinator_reports_bytes"] <= 20 * 1024 * 1024:
        raise FactoryError("Coordinator reports must be capped at 20 MiB")
    if not 15 <= config["cleanup_grace_minutes"] <= 60:
        raise FactoryError("Cleanup grace must be 15–60 minutes")
    rate = number(config["server_types"][job["server_type"]], "hourly rate ceiling")
    hours = math.ceil((job["lifetime_minutes"] + config["cleanup_grace_minutes"]) / 60)
    return {"job": job, "reservation_eur": str(rate * hours), "rate_ceiling_eur": str(rate),
            "reserved_hours": hours, "note": "Conservative reservation, not a provider billing guarantee"}


def source_bundle(job_path, job):
    """Explicit job-directory source only; no credentials/data/private factory tree."""
    buffer = io.BytesIO()
    total = 0
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        def add(name, content):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(content), 0o600
            archive.addfile(info, io.BytesIO(content))

        for path in sorted(job_path.parent.rglob("*")):
            if path.is_symlink():
                raise FactoryError("Job source may not contain symlinks")
            if not path.is_file() or path == job_path:
                continue
            relative = path.relative_to(job_path.parent)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                raise FactoryError("Job directory must contain only explicit source files, no hidden files/caches")
            if path.suffix not in (".py", ".sh", ".json", ".txt", ".toml", ".yaml", ".yml", ".md"):
                raise FactoryError(f"Unexpected source file: {relative}; keep data off Scout")
            total += path.stat().st_size
            if total > BUNDLE_LIMIT:
                raise FactoryError("Job source exceeds 2 MiB; source bundle is not a data transport")
            add("source/" + relative.as_posix(), path.read_bytes())
        add("job.json", json.dumps(job, sort_keys=True).encode())
        for name in ("executor.py", "upload.py"):
            add(name, (Path(__file__).resolve().parents[1] / "workers" / name).read_bytes())
    if len(buffer.getvalue()) > BUNDLE_LIMIT + 256 * 1024:
        raise FactoryError("Job bundle too large")
    return buffer.getvalue()


def github(config):
    repo = config["staging_repo"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise FactoryError("Configure staging_repo as owner/repository")
    api = API("https://api.github.com", secret("FACTORY_GITHUB_TOKEN"))
    if api.request("GET", f"repos/{repo}").get("private") is not True:
        raise FactoryError("Staging repository must be private")
    return api


def check_price(cloud, job, ceiling):
    # Fail closed on an unknown price/schema. Ceiling includes IPv4 and VAT.
    pricing = cloud.request("GET", "pricing")["pricing"]
    if pricing.get("currency") != "EUR":
        raise FactoryError("Only EUR billing is supported by the initial reservation policy")
    def price(entries, field, value):
        for entry in entries:
            if entry.get(field) == value:
                for location in entry.get("prices", []):
                    if location.get("location") == job["location"]:
                        return number(location["price_hourly"]["gross"], "provider price", positive=False)
        raise FactoryError("Could not establish current hourly price for this resource/location")
    server = price(pricing["server_types"], "name", job["server_type"])
    ipv4 = price(pricing["primary_ips"], "type", "ipv4")
    if server + ipv4 > Decimal(ceiling):
        raise FactoryError("Current server + IPv4 hourly price exceeds configured ceiling")
    return str(server + ipv4)


def ssh_args(config, record):
    key = Path(config["ssh_private_key"]).expanduser()
    if not key.is_file():
        raise FactoryError("Configured SSH private key is missing")
    ip = record["ipv4"]
    import ipaddress
    ipaddress.IPv4Address(ip)
    return ["ssh", "-i", str(key), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
            "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"UserKnownHostsFile={record['known_hosts']}", f"root@{ip}"]


def remote(config, record, command, data=None, timeout=60):
    result = subprocess.run(ssh_args(config, record) + [command], input=data, capture_output=True, timeout=timeout)
    if result.returncode:
        # Do not echo arbitrary remote output or credentials into the conversation.
        raise FactoryError(f"Remote command failed (exit {result.returncode}); use worker status")
    if len(result.stdout) > REPORT_LIMIT:
        raise FactoryError("Unexpected large remote response")
    return result.stdout


def plan(root, job_path, config):
    job = read_json(job_path)
    report = validate(job, config)
    bundle = source_bundle(Path(job_path).resolve(), job)
    return {**report, "source_bytes": len(bundle), "source_sha256": hashlib.sha256(bundle).hexdigest(),
            "cloud_calls": 0, "enabled": config.get("enabled") is True}


def launch(root, job_path, config, cloud=None):
    if config.get("enabled") is not True or config.get("cleanup_configured") is not True:
        raise FactoryError("Worker launch disabled; configure policy and independent cleanup first")
    if not shutil.which("ssh"):
        raise FactoryError("SSH client is required")
    job_path = Path(job_path).resolve()
    proposal = plan(root, job_path, config)
    job, now = proposal["job"], utcnow()
    if not Path(config["ssh_private_key"]).expanduser().is_file() or not config["ssh_key_name"]:
        raise FactoryError("Configure an existing SSH key and its registered Hetzner name")
    github(config)  # Verify upload access's repository visibility before paid resources.
    cloud = cloud or Cloud()
    with locked(root):
        record_path = Path(root) / "jobs" / (job["id"] + ".json")
        if record_path.exists():
            raise FactoryError("Job ID already recorded; use status/reconcile, never relaunch it")
        records = [read_json(p) for p in (Path(root) / "jobs").glob("*.json")]
        if any(r["status"] != "deleted" for r in records) or cloud.list_resources("servers", config["project"]):
            raise FactoryError("An active or interrupted job exists; reconcile it before launching another")
        budget = number(config["monthly_budget_eur"], "monthly budget")
        month = now.strftime("%Y-%m")
        # Reserve against both months if a job could straddle a month boundary.
        expires = int(now.timestamp()) + job["lifetime_minutes"] * 60
        end_month = datetime.fromtimestamp(expires + config["cleanup_grace_minutes"] * 60, timezone.utc).strftime("%Y-%m")
        months = sorted({month, end_month})
        for period in months:
            spent = sum(Decimal(r["reservation_eur"]) for r in records if period in r["budget_months"])
            if spent + Decimal(proposal["reservation_eur"]) > budget:
                raise FactoryError("Conservative monthly cost reservations would exceed allowance")
        actual_rate = check_price(cloud, job, proposal["rate_ceiling_eur"])
        folder = Path(root) / ".factory" / job["id"]
        folder.mkdir(parents=True)
        record = {**proposal, "status": "provisioning", "project": config["project"],
                  "created_at": now.isoformat(), "expires": expires, "budget_months": months,
                  "cleanup_grace_minutes": config["cleanup_grace_minutes"],
                  "provider_hourly_eur": actual_rate, "server_id": None,
                  "known_hosts": str((folder / "known_hosts").resolve()), "staging_repo": config["staging_repo"]}
        write_json(record_path, record)  # Before any mutation: survives ambiguous responses.
        labels = {"factory": config["project"], "job": job["id"], "expires": str(expires)}
        response = cloud.request("POST", "servers", {
            "name": "scout-" + job["id"], "server_type": job["server_type"], "location": job["location"],
            "image": "ubuntu-24.04", "ssh_keys": [config["ssh_key_name"]], "labels": labels,
            "public_net": {"enable_ipv4": True, "enable_ipv6": False},
            "user_data": "#cloud-config\npackage_update: true\npackages: [docker.io, python3]\nruncmd:\n  - [systemctl, enable, --now, docker]\n",
        })
        server = response["server"]
        record.update(server_id=server["id"], ipv4=server["public_net"]["ipv4"]["ip"])
        write_json(record_path, record)
        cloud.label_ips(server)
        cloud.wait_action(response["action"])
    # Lock does not span boot wait; the durable job blocks competing launches.
    return resume(root, job["id"], config, cloud, bundle=source_bundle(job_path, job))


def load_record(root, job_id):
    return read_json(Path(root) / "jobs" / (identifier(job_id) + ".json"))


def reconcile(root, job_id, config, cloud=None):
    cloud = cloud or Cloud()
    record = load_record(root, job_id)
    if record["project"] != config["project"]:
        raise FactoryError("Policy project differs from recorded job")
    matches = [s for s in cloud.list_resources("servers", config["project"]) if s.get("labels", {}).get("job") == job_id]
    if len(matches) > 1:
        raise FactoryError("Multiple workers share a job ID; inspect before further operations")
    if matches:
        server = matches[0]
        if record.get("server_id") not in (None, server["id"]):
            raise FactoryError("Provider ID differs from job record")
        record.update(server_id=server["id"], ipv4=server["public_net"]["ipv4"]["ip"])
    elif record.get("server_id"):
        # A filtered list alone is not proof of deletion: a label may have changed.
        if cloud.server(record["server_id"]) is not None:
            raise FactoryError("Worker still exists with changed labels; inspect ownership")
        cloud.clean_job_ips(config["project"], job_id)
        record.update(status="deleted", deleted_at=utcnow().isoformat())
    else:
        if time.time() > record["expires"] + record["cleanup_grace_minutes"] * 60:
            cloud.clean_job_ips(config["project"], job_id)
            record.update(status="deleted", deleted_at=utcnow().isoformat(),
                          reconciliation="No server found after expiry and cleanup grace; reservation retained")
        else:
            record["status"] = "creation-unresolved"
    write_json(Path(root) / "jobs" / f"{job_id}.json", record)
    return record


def resume(root, job_id, config, cloud=None, bundle=None):
    record = reconcile(root, job_id, config, cloud)
    if not record.get("server_id") or record["status"] == "deleted":
        raise FactoryError("No live worker to resume")
    if record["expires"] <= int(time.time()) + record["job"]["timeout_minutes"] * 60 + 300:
        raise FactoryError("Insufficient worker lifetime remains; collect/clean up and use a new job")
    if bundle is None:
        raise FactoryError("Use status/collect for existing runs; bootstrap resume requires --job-file")
    if hashlib.sha256(bundle).hexdigest() != record["source_sha256"]:
        raise FactoryError("Source bundle changed since launch")
    deadline = min(time.monotonic() + 600, time.monotonic() + record["expires"] - time.time() - 300)
    while True:
        try:
            remote(config, record, "cloud-init status --wait >/dev/null && docker info >/dev/null", timeout=45)
            break
        except (FactoryError, subprocess.TimeoutExpired):
            if time.monotonic() >= deadline:
                raise FactoryError("Worker not ready; use resume with the same source or let expiry clean it up")
            time.sleep(10)
    # Never rerun a dispatched job after a lost SSH reply.
    started = remote(config, record, "test -f /opt/scout/started && echo yes || echo no").strip()
    if started == b"yes":
        record["status"] = "running"
    else:
        remote(config, record, "umask 077; mkdir -p /opt/scout/source /opt/scout/output && cat > /opt/scout/source.tar && tar -xf /opt/scout/source.tar -C /opt/scout", bundle)
        credentials = json.dumps({"token": secret("FACTORY_GITHUB_TOKEN"), "repo": record["staging_repo"]}).encode()
        remote(config, record, "umask 077; cat > /opt/scout/credentials.json", credentials)
        # Root-only token is outside all container mounts and never put in cloud-init.
        remote(config, record, "systemctl is-active --quiet scout-job || systemd-run --collect --unit=scout-job --property=Restart=no /usr/bin/python3 /opt/scout/executor.py")
        record["status"] = "running"
    write_json(Path(root) / "jobs" / f"{job_id}.json", record)
    return record


def retry_upload(root, job_id, config, cloud=None):
    record = reconcile(root, job_id, config, cloud)
    if record["status"] == "deleted" or record["expires"] < time.time() + 180:
        raise FactoryError("No live worker with enough time for upload recovery")
    remote(config, record, "test -f /opt/scout/started && systemd-run --collect --unit=scout-upload /usr/bin/python3 /opt/scout/executor.py")
    return {"job_id": job_id, "status": "upload recovery dispatched; collect again shortly"}


def collect(root, job_id, config, cloud=None):
    record = reconcile(root, job_id, config, cloud)
    if record["status"] == "deleted":
        raise FactoryError("Worker is gone; recover artifacts from the recorded staging release")
    folder = Path(root) / ".factory" / job_id
    limit = min(config["max_report_bytes"], REPORT_LIMIT)
    # wc checks prevent transferring an unexpected data file to the small host.
    cmd = f"if test -f /opt/scout/result.json; then test $(wc -c < /opt/scout/result.json) -le {limit} && cat /opt/scout/result.json; else printf '%s' '{{\"status\":\"running\"}}'; fi"
    raw = remote(config, record, cmd)
    if len(raw) > limit:
        raise FactoryError("Report exceeds configured limit")
    report = json.loads(raw)
    if report.get("status") == "running":
        return {"job": job_id, "status": "running", "expires": record["expires"]}
    if report.get("job_id") != job_id:
        raise FactoryError("Remote report belongs to a different job")
    total = sum(p.stat().st_size for p in (Path(root) / ".factory").glob("*/result.json") if p != folder / "result.json")
    if total + len(json.dumps(report, indent=2).encode()) + 1 > config["max_coordinator_reports_bytes"]:
        raise FactoryError("Local report budget exhausted; preserve and prune old reports")
    api = github(config)
    if report.get("uploaded") is not True or report.get("repo") != record["staging_repo"]:
        write_json(folder / "result.json", report)
        raise FactoryError("Artifacts not preserved; inspect local compact report; expiry still applies")
    release = api.request("GET", f"repos/{record['staging_repo']}/releases/{int(report['release_id'])}")
    if release["tag_name"] != "job-" + job_id:
        raise FactoryError("Staging release tag differs from this job")
    expected = report["assets"]
    if not expected or len(expected) > 400 or len({a["id"] for a in expected}) != len(expected):
        raise FactoryError("Invalid artifact manifest")
    actual_assets = {}
    for page in range(1, 12):
        batch = api.request("GET", f"repos/{record['staging_repo']}/releases/{int(report['release_id'])}/assets?per_page=100&page={page}")
        actual_assets.update({a["id"]: a for a in batch})
        if len(batch) < 100:
            break
    for asset in expected:
        actual = actual_assets.get(asset["id"], {})
        if actual.get("size") != asset["size"] or actual.get("digest") != "sha256:" + asset["sha256"]:
            raise FactoryError("Uploaded artifact size/digest mismatch")
    write_json(folder / "result.json", report)
    record.update(status="collected", result=report, collected_at=utcnow().isoformat())
    write_json(Path(root) / "jobs" / f"{job_id}.json", record)
    return report


def destroy(root, job_id, config, cloud=None):
    cloud = cloud or Cloud()
    record = reconcile(root, job_id, config, cloud)
    if record["status"] == "deleted":
        return record
    if record["status"] != "collected" and record["expires"] > int(time.time()):
        raise FactoryError("Collect and verify artifacts before normal deletion; expired jobs are cleaned by sweep")
    if not record.get("server_id"):
        raise FactoryError("Creation unresolved; no confirmed server ID to delete")
    cloud.delete_owned({"id": record["server_id"]}, config["project"], job_id)
    cloud.clean_job_ips(config["project"], job_id)
    record.update(status="deleted", deleted_at=utcnow().isoformat())
    write_json(Path(root) / "jobs" / f"{job_id}.json", record)
    return record


def sweep(project, cloud=None, now=None):
    identifier(project)
    cloud, now = cloud or Cloud(), int(time.time()) if now is None else now
    removed, errors = [], []
    for server in cloud.list_resources("servers", project):
        labels = server.get("labels", {})
        try:
            job_id = identifier(labels["job"])
            if labels.get("factory") != project or int(labels["expires"]) > now:
                continue
            cloud.delete_owned(server, project, job_id)
            removed.append(server["id"])
        except (KeyError, ValueError, FactoryError) as exc:
            errors.append({"server_id": server["id"], "error": str(exc)})
    ips = cloud.clean_expired_ips(project, now)
    return {"deleted_servers": removed, "deleted_primary_ips": ips, "errors": errors}
