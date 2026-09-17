"""Research records and bounded remote workers. doctor/candidate/plan are offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import subprocess

from . import candidates, worker
from .common import FactoryError, read_json


def doctor(root):
    usage = shutil.disk_usage(root)
    return {
        "python": sys.version.split()[0],
        "project_root": str(root),
        "disk_free_gib": round(usage.free / 2**30, 2),
        "coordinator_constraints": {"ram_gib": 1.9, "disk_gb": 6, "bulk_data_allowed": False},
        "cli_available": {name: shutil.which(name) is not None for name in ("git", "gh", "ssh", "hcloud")},
        "native_capabilities": "Inspect Scout's tools/connectors; absent CLIs do not prove unavailable capabilities",
        "capability_inventory_present": (root / "deployment" / "capabilities.md").exists(),
        "worker_policy_present": (root / "config" / "local.json").exists(),
        "worker_integration": "stdlib API + SSH; live smoke test required before unattended use",
        "benchmark_available_locally": (root.parent / "harness_benchmark" / "bench").is_dir(),
        "next_action": "Read docs/HANDOFF.md and docs/CAPABILITIES.md; start source research",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Offline environment summary; never prints credentials")
    candidate = commands.add_parser("candidate", help="Track source investigations")
    actions = candidate.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create")
    create.add_argument("id")
    actions.add_parser("list")
    workers = commands.add_parser("worker", help="Plan, run, reconcile, collect and delete workers")
    workers.add_argument("--config", type=Path, help="Defaults to ROOT/config/local.json")
    operations = workers.add_subparsers(dest="action", required=True)
    for name in ("plan", "launch"):
        operations.add_parser(name).add_argument("job_file", type=Path)
    for name in ("status", "collect", "destroy", "retry-upload"):
        operations.add_parser(name).add_argument("id")
    resume = operations.add_parser("resume")
    resume.add_argument("id")
    resume.add_argument("--job-file", type=Path, required=True)
    operations.add_parser("sweep").add_argument("--project", required=True)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if not root.is_dir():
            raise FactoryError("Project root must exist")
        if args.command == "doctor":
            result = doctor(root)
        elif args.command == "candidate":
            result = candidates.create(root, args.id) if args.action == "create" else candidates.listing(root)
        elif args.action == "sweep":
            result = worker.sweep(args.project)
        else:
            config = read_json(args.config or root / "config" / "local.json")
            if args.action in ("plan", "launch"):
                result = getattr(worker, args.action)(root, args.job_file, config)
            elif args.action == "resume":
                bundle = worker.source_bundle(args.job_file.resolve(), read_json(args.job_file))
                result = worker.resume(root, args.id, config, bundle=bundle)
            else:
                function = {"status": worker.reconcile, "collect": worker.collect,
                            "destroy": worker.destroy, "retry-upload": worker.retry_upload}[args.action]
                result = function(root, args.id, config)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 1 if isinstance(result, dict) and result.get("errors") else 0
    except FactoryError as exc:
        print(f"factory: {exc}", file=sys.stderr)
        return 1
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"factory: {type(exc).__name__}; check configuration and reconcile before retrying paid operations", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
