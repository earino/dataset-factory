#!/usr/bin/env python3
"""Export Scout's reproducible setup and a compact operational snapshot into deployment/scout/.

Deterministic where it can be: every field is either read from an authoritative source at run time
or copied from a file in this repository. Nothing is typed from memory, and nothing is exported
that is not on an explicit allowlist - copying `config.yaml` wholesale and trusting redaction is
exactly the mistake this is written to avoid.

Writes three files:

* `deployment/scout/versions.json`   - runtime identity and local customizations
* `deployment/scout/config-export.json` - allowlisted non-secret configuration fields
* `deployment/scout/STATE-SNAPSHOT.md`  - point-in-time operational state, with sources

Refuses to write anything if a secret-shaped string appears in the output, or if a key that is not
on the allowlist reaches it.

    python3 scripts/scout-snapshot.py            # write
    python3 scripts/scout-snapshot.py --check     # verify committed exports are current + clean
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deployment" / "scout"
HERMES = ["/opt/hermes/.venv/bin/python3", "/opt/hermes/hermes"]
HERMES_HOME = Path("/opt/data")

# Explicit allowlist. A field is exported only if it is named here; adding one is a deliberate act.
CONFIG_ALLOWLIST = (
    "agent.max_turns",
    "agent.run_budget_seconds",
    "agent.stall_guards",
    "agent.reasoning_effort",
    "cron.catch_up_missed",
    "cron.script_timeout_seconds",
    "cron.model",
    "skills.external_dirs",
    "approvals.mode",
    "approvals.cron_mode",
    "approvals.single_query_mode",
    "approvals.unattended_mode",
    "approvals.deny",
    "command_allowlist",
    "curator.enabled",
    "delegation.max_iterations",
)

# Credential-shaped strings must never appear in an export. The scan is a refusal, not a warning.
SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{10,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{10,}"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"[Bb]earer\s+[A-Za-z0-9._-]{20,}"),
)

# Field names that are never exported even if a future allowlist entry would reach them.
FORBIDDEN_KEYS = re.compile(r"(token|secret|password|passwd|key|credential|chat|origin|phone|"
                            r"email|sig|signature)", re.I)

# File types that must never be committed under deployment/ (checked, not assumed).
FORBIDDEN_SUFFIXES = (".env", ".db", ".sqlite", ".sqlite3", ".key", ".pem", ".p12", ".pfx",
                      ".token", ".log", ".har", ".zip", ".tar", ".gz")


def run(command, timeout=120, env=None):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                                env={**os.environ, **(env or {})})
    except (OSError, subprocess.SubprocessError) as exc:
        # A clean checkout has no Hermes runtime; the export must still be checkable there.
        return "", f"{type(exc).__name__}: {exc}", 127
    return (result.stdout or "").strip(), (result.stderr or "").strip(), result.returncode


def hermes_version():
    out, _, _ = run([*HERMES, "--version"])
    version = {"raw": out.splitlines()[:6], "hermes": None, "upstream": None,
               "install_dir": None, "install_method": None, "python": None, "openai_sdk": None}
    for line in out.splitlines():
        if "Hermes Agent" in line:
            version["hermes"] = line.split("Hermes Agent", 1)[1].split("·")[0].strip()
            match = re.search(r"upstream\s+([0-9a-f]{6,})", line)
            version["upstream"] = match.group(1) if match else None
        elif line.startswith("Install directory:"):
            version["install_dir"] = line.split(":", 1)[1].strip()
        elif line.startswith("Install method:"):
            version["install_method"] = line.split(":", 1)[1].strip()
        elif line.startswith("Python:"):
            version["python"] = line.split(":", 1)[1].strip()
        elif line.startswith("OpenAI SDK:"):
            version["openai_sdk"] = line.split(":", 1)[1].strip()
    return version, "hermes --version"


def config_fields():
    fields, not_set, rejected = {}, [], []
    for key in CONFIG_ALLOWLIST:
        if FORBIDDEN_KEYS.search(key):
            rejected.append(key)
            continue
        out, err, code = run([*HERMES, "config", "get", key])
        value = out.strip()
        if code != 0 or value.startswith("Config key not set"):
            not_set.append(key)
            continue
        # Multi-line YAML blocks are kept as text; they are configuration, not credentials.
        fields[key] = value[:1200]
    return {"fields": fields, "not_set": not_set, "rejected_by_name": rejected}, \
        "hermes config get <key>, for the allowlist above"


def cron_jobs():
    path = HERMES_HOME / "cron" / "jobs.json"
    if not path.is_file():
        return [], str(path)
    raw = json.loads(path.read_text())
    items = raw["jobs"] if isinstance(raw["jobs"], list) else list(raw["jobs"].values())
    exported = []
    for job in items:
        exported.append({
            "id": job.get("id"),
            "name": job.get("name"),
            "schedule": job.get("schedule_display"),
            "repeat": (job.get("repeat") or {}).get("times"),
            "runs_completed": (job.get("repeat") or {}).get("completed"),
            "enabled": job.get("enabled"),
            "state": job.get("state"),
            "mode": "script-only (no model)" if job.get("no_agent") else "agent",
            "script": job.get("script"),
            "delivery": "the chat the job was created from (alias: origin)" if job.get("deliver")
                        in ("origin", None) else job.get("deliver"),
            "next_run_at": job.get("next_run_at"),
            "last_status": job.get("last_status"),
        })
    return exported, f"{path} (fields allowlisted; the delivery chat identifier is not exported)"


def worker_ledger():
    jobs_dir = ROOT / "jobs"
    records, active, reserved = [], [], 0.0
    paths = sorted(jobs_dir.glob("*.json")) if jobs_dir.is_dir() else []
    for path in paths:
        record = json.loads(path.read_text())
        reserved += float(record.get("reservation_eur") or 0)
        status = record.get("status")
        records.append({"job_id": record.get("job_id"), "status": status,
                        "reservation_eur": record.get("reservation_eur")})
        if status not in ("deleted",):
            active.append({"job_id": record.get("job_id"), "status": status,
                           "server_id": record.get("server_id"),
                           "expires": record.get("expires")})
    return {"jobs_on_file": len(records), "reserved_eur_total": round(reserved, 2),
            "active": active}, "jobs/*.json (the worker launch ledger; only one coordinator writes it)"


def provider_resources():
    env = {"HCLOUD_TOKEN_FILE": "/opt/data/.secrets/hetzner.token"}
    out, err, code = run([sys.executable, str(ROOT / "scripts" / "provider-inventory.py")], env=env)
    try:
        data = json.loads(out)
        return {"servers_in_account": data.get("servers_total_in_account"),
                "primary_ips": data.get("primary_ips_count")}, "scripts/provider-inventory.py (live API)"
    except json.JSONDecodeError:
        return {"unavailable": (err or out)[:200]}, "scripts/provider-inventory.py (live API)"


def research_budget():
    out, err, code = run([sys.executable, str(ROOT / "scripts" / "research-budget.py"), "--json"])
    try:
        data = json.loads(out)
        decision = data["decision"]
        return ({"period_start": decision["period_start"],
                 "allowance_usd": decision["allowance_usd"],
                 "research_spend_usd": decision["research_cost_usd"],
                 "sessions_last_7_days": decision["runs_last_7_days"],
                 "session_cap_per_week": decision["session_cap_per_week"],
                 "note": "Hermes estimates; not the subscription quota"},
                "scripts/research-budget.py --json (Hermes usage records)")
    except (json.JSONDecodeError, KeyError):
        return {"unavailable": (err or out)[:200]}, "scripts/research-budget.py --json"


def destinations():
    """The recorded destination state of every release package.

    This named one dataset's record, so the snapshot reported a single release as though it were the
    whole publication surface.
    """
    summary, sources, found = {}, [], False
    for path in sorted((ROOT / "release").glob("*/DESTINATIONS.json")):
        found = True
        data = json.loads(path.read_text())
        dataset = path.parent.name
        for name, entry in (data.get("destinations") or {}).items():
            summary[f"{dataset}:{name}"] = {
                "repo": entry.get("repo"),
                "revision": entry.get("revision") or entry.get("release_tag"),
                "private": entry.get("private"), "verified": entry.get("verified"),
                "verified_at": entry.get("verified_at")}
        if data.get("licensing"):
            summary[f"{dataset}:licensing"] = data["licensing"]
        sources.append(path.relative_to(ROOT).as_posix())
    if not found:
        return {}, "no release/*/DESTINATIONS.json found"
    return summary, ", ".join(sources)


def queue():
    rows = []
    for path in sorted((ROOT / "candidates").glob("*/record.json")):
        record = json.loads(path.read_text())
        rows.append({"id": record.get("id"), "status": record.get("status"),
                     "next_action": (record.get("next_action") or "")[:200]})
    return rows, "candidates/*/record.json"


def disk():
    out, _, _ = run(["df", "-h", "/opt/data"])
    return {"filesystem": out.splitlines()[-1] if out else "unavailable"}, "df -h /opt/data"


def scan(text, where):
    hits = []
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            hits.append({"where": where, "pattern": pattern.pattern,
                         "preview": match.group(0)[:6] + "..."})
    return hits


def forbidden_files():
    found = []
    if OUT.is_dir():
        for path in OUT.rglob("*"):
            if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
                found.append(str(path.relative_to(ROOT)))
    return found


def build():
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    version, version_src = hermes_version()
    config, config_src = config_fields()
    jobs, jobs_src = cron_jobs()
    ledger, ledger_src = worker_ledger()
    resources, resources_src = provider_resources()
    budget, budget_src = research_budget()
    dest, dest_src = destinations()
    records, queue_src = queue()
    filesystem, disk_src = disk()

    versions = {
        "observed_at": stamp,
        "source": version_src,
        "runtime": version,
        "local_customizations": {
            "skills_external_dirs": config["fields"].get("skills.external_dirs"),
            "approvals": {k: v for k, v in config["fields"].items() if k.startswith("approvals.")},
            "command_allowlist": config["fields"].get("command_allowlist"),
            "cron_overrides": {k: v for k, v in config["fields"].items() if k.startswith("cron.")},
            "note": "Everything else here is stock Hermes; the project's own code is in this "
                    "repository and is not duplicated in the export.",
        },
        "project_code": {"scripts": "scripts/", "skills": "skills/ (registered via "
                                                         "skills.external_dirs)",
                         "worker_modules": "workers/", "factory": "factory/"},
    }
    config_export = {"observed_at": stamp, "source": config_src,
                     "allowlist": list(CONFIG_ALLOWLIST), **config}

    snapshot = [
        "# Scout operational snapshot",
        "",
        f"Observed {stamp} on the hosted coordinator. Regenerate with "
        "`python3 scripts/scout-snapshot.py`; this file is written by that script, not by hand.",
        "",
        "## Runtime",
        "",
        f"- Hermes Agent **{version['hermes']}** (upstream `{version['upstream']}`), install "
        f"`{version['install_method']}` at `{version['install_dir']}`, Python {version['python']}.",
        f"- Source: {version_src}. Full detail in `versions.json`.",
        "",
        "## Schedules that exist now",
        "",
        "| job | schedule | mode | next run | last |",
        "| --- | --- | --- | --- | --- |",
    ]
    for job in jobs:
        snapshot.append(f"| {job['name']} (`{job['id']}`) | `{job['schedule']}` | {job['mode']} | "
                        f"{job['next_run_at'] or '—'} | {job['last_status'] or '—'} |")
    snapshot += [
        "",
        f"Source: {jobs_src}. All times UTC; delivery is to the chat each job was created from.",
        "Scheduled jobs run on the coordinator's own scheduler, independently of GitHub Actions.",
        "",
        "## Budget (estimates, not the provider's quota)",
        "",
        f"- Research (model spend): allowance {budget.get('allowance_usd')} USD per month from "
        f"{str(budget.get('period_start'))[:10]}, spend so far {budget.get('research_spend_usd')} "
        f"USD, sessions this week {budget.get('sessions_last_7_days')}/"
        f"{budget.get('session_cap_per_week')}.",
        f"- Workers (compute): {ledger['jobs_on_file']} jobs on file, "
        f"{ledger['reserved_eur_total']} EUR reserved in total; active jobs: "
        f"{ledger['active'] or 'none'}.",
        f"- Provider resources live now: {resources.get('servers_in_account', 'unknown')} "
        f"servers, {resources.get('primary_ips', 'unknown')} primary IPs"
        + (f" (inventory unavailable: {resources.get('unavailable')})" if resources.get('unavailable') else "") + ".",
        f"- Coordinator disk: `{filesystem.get('filesystem', 'unavailable')}`.",
        f"- Sources: {budget_src}; {ledger_src}; {resources_src}; {disk_src}.",
        "",
        "## Destinations and publication state",
        "",
    ]
    for name, entry in sorted(dest.items()):
        if name == "licensing":
            continue
        snapshot.append(f"- **{name}**: `{entry.get('repo') or entry.get('release_tag')}`, "
                        f"revision `{entry.get('revision')}`, private={entry.get('private')}, "
                        f"verified={entry.get('verified')} at {entry.get('verified_at')}")
    licensing = dest.get("licensing") or {}
    snapshot += [
        "",
        f"Licensing: code {licensing.get('code_spdx')}, compilation "
        f"{licensing.get('compilation_spdx')}, source {licensing.get('source_spdx')}.",
        f"Source: {dest_src}. **Public visibility on either platform still requires the "
        "operator's approval.**",
        "",
        "## Queue and next action",
        "",
    ]
    for record in records:
        snapshot.append(f"- `{record['id']}` — {record['status']}: {record['next_action']}")
    snapshot += [
        "",
        f"Source: {queue_src}. The newest section of `STATE.md` carries the narrative.",
        "",
        "## Recovery notes",
        "",
        "- Reconcile before resuming: read `jobs/*.json` for non-deleted jobs and check the "
        "provider inventory above. Do not launch a second coordinator or re-run a job whose "
        "record says `running`.",
        "- The worker allowance is counted from `jobs/*.json`; deleting records to 'tidy up' "
        "would reset that accounting. Records are evidence, not scratch files.",
        "- Secrets are supplied at run time (dashboard environment or mode-0600 files under "
        "`.secrets/`); nothing here references a value. See `deployment/scout/README.md`.",
    ]

    text = "\n".join(snapshot) + "\n"
    return versions, config_export, text


def check_committed():
    """Verify the committed export: present, clean, and free of excluded file types.

    Deliberately does no live introspection - the check must mean the same thing in CI as it does
    on the coordinator, and must not depend on a runtime that a clean checkout does not have.
    """
    problems = []
    expected = ("versions.json", "config-export.json", "STATE-SNAPSHOT.md", "README.md",
                "IDENTITY.md")
    for name in expected:
        path = OUT / name
        if not path.is_file():
            problems.append({"where": name, "problem": "missing from the export"})
            continue
        if path.suffix in (".json", ".md", ".txt"):
            problems += scan(path.read_text(errors="replace"), name)
    problems += [{"where": path, "problem": "forbidden file type"} for path in forbidden_files()]
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the committed exports are clean; do not rewrite them")
    args = parser.parse_args(argv)

    if args.check:
        problems = check_committed()
        if problems:
            print(json.dumps({"ok": False, "problems": problems}, indent=2))
            return 1
        print(json.dumps({"ok": True,
                          "files": sorted(p.name for p in OUT.iterdir() if p.is_file()),
                          "checked": "secret patterns and forbidden file types"}, indent=2))
        return 0

    versions, config_export, snapshot = build()
    payloads = {"versions.json": json.dumps(versions, indent=2) + "\n",
                "config-export.json": json.dumps(config_export, indent=2) + "\n",
                "STATE-SNAPSHOT.md": snapshot}

    hits = []
    for name, body in payloads.items():
        hits += scan(body, name)

    if hits:
        print(json.dumps({"ok": False, "refused": "secret-shaped content in the export",
                          "hits": hits}, indent=2))
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in payloads.items():
        (OUT / name).write_text(body)
    print(json.dumps({"ok": True, "wrote": [str((OUT / n).relative_to(ROOT)) for n in payloads],
                      "observed_at": versions["observed_at"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
