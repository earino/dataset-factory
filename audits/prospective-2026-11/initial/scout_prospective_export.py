#!/usr/bin/env python3
"""Prospective-study export: production candidate/attempt/job ledger + resource usage.

Cohort: first 12 new releases published between 2026-11-12T21:27:59.319944Z and
2026-11-17T17:00:00Z. Existing (carry-in) candidates are exported separately from new
admissions. Bounded: per-string caps, file-size caps, no secrets, no bulk artifacts,
no candidate-state writes, no model calls. Deterministic: fixed sort order, ISO
timestamps; only collected_at and git SHAs vary between runs.

Modes: "initial" (snapshot at cohort start, run manually) and "close" (scheduled by
cron at cohort close). Output lands under audits/prospective-2026-11/<label>/ on
evidence branch scout/prospective-2026-11, pushed and CI-checked. Prints one compact
summary line for the scheduler.
"""
import datetime
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = Path("/opt/data/dataset-factory")
BRANCH = "scout/prospective-2026-11"
LABEL = sys.argv[1] if len(sys.argv) > 1 else "close"
COHORT_START = "2026-11-12T21:27:59.319944+00:00"
COHORT_CLOSE = "2026-11-17T17:00:00+00:00"
COHORT_SIZE = 12
UTC = datetime.timezone.utc
RESULT_CAP = 400
REASON_CAP = 300
JOB_FILE_CAP = 1_000_000
USAGE_FILE_CAP = 20_000
DROP_KEYS = re.compile(r"ipv4|ip_address|host|known_hosts|ssh|token|password|secret|credential", re.I)


def iso(ts):
    return datetime.datetime.fromtimestamp(ts, UTC).isoformat() if ts else None


def cap(text, n):
    if text is None:
        return None
    s = str(text)
    return s if len(s) <= n else s[:n] + f"…[truncated {len(s) - n}]"


def sanitize(obj):
    if isinstance(obj, dict):
        return {k: ("[excluded]" if DROP_KEYS.search(str(k)) else sanitize(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


def main():
    problems = []
    collected_at = datetime.datetime.now(UTC).isoformat()
    start_ts = datetime.datetime.fromisoformat(COHORT_START).timestamp()

    con = sqlite3.connect(f"file:{REPO}/.factory/pipeline.sqlite3?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("BEGIN")
    cands = [dict(r) for r in con.execute("SELECT id, stage, reason, created, updated, next_run FROM candidates ORDER BY created, id")]
    atts = [dict(r) for r in con.execute("SELECT id, candidate, stage, status, ordinal, started, finished, result FROM attempts ORDER BY started, id")]
    pub_meta = {}
    for r in con.execute("SELECT id, data FROM candidates WHERE stage='published' ORDER BY created"):
        try:
            data = json.loads(r["data"])
            src = data.get("source") or {}
            pub_meta[r["id"]] = {"dataset": src.get("dataset_id") or src.get("dataset"),
                                  "version": (data.get("publication") or {}).get("version")}
        except (ValueError, TypeError):
            pub_meta[r["id"]] = {"dataset": None, "version": None}
    con.close()

    for c in cands:
        c["created"], c["updated"], c["next_run"] = iso(c["created"]), iso(c["updated"]), iso(c["next_run"])
        c["reason"] = cap(c["reason"], REASON_CAP)
        c["cohort_group"] = "carry-in" if (c["created"] and datetime.datetime.fromisoformat(c["created"]).timestamp() < start_ts) else "new-admission"
        c.update(pub_meta.get(c["id"], {}))
    new_ids = {c["id"] for c in cands if c["cohort_group"] == "new-admission"}
    for a in atts:
        a["started"], a["finished"] = iso(a["started"]), iso(a["finished"])
        a["cohort_group"] = "carry-in" if a["candidate"] not in new_ids else "new-admission"
        a["result"] = cap(a["result"], RESULT_CAP)

    # jobs ledger
    jobs, unavailable_jobs = [], 0
    for p in sorted((REPO / "jobs").glob("*.json")):
        if p.stat().st_size > JOB_FILE_CAP:
            unavailable_jobs += 1
            continue
        try:
            d = json.loads(p.read_text())
        except ValueError:
            unavailable_jobs += 1
            continue
        rec = {k: d.get(k) for k in ("id", "status", "stage", "candidate", "started", "finished",
                                     "reservation_eur", "budget_months", "server_type", "location", "worker")}
        for k in ("started", "finished"):
            if isinstance(rec.get(k), (int, float)):
                rec[k] = iso(rec[k])
        rec["id"] = rec["id"] or p.stem
        rec["cohort_group"] = "carry-in" if rec.get("candidate") not in new_ids and rec.get("candidate") else "new-admission"
        if rec.get("candidate") is None:
            rec["cohort_group"] = "unattributed"
        jobs.append(sanitize(rec))

    # model usage per attempt (where recorded)
    usage, unavailable_usage = {}, 0
    for d in sorted((REPO / ".factory/model-tasks").iterdir()):
        if not d.is_dir():
            continue
        u = d / "usage.json"
        entry = {"attempt": d.name, "response_present": (d / "response.json").is_file()}
        if u.is_file() and u.stat().st_size <= USAGE_FILE_CAP:
            try:
                entry["usage"] = sanitize(json.loads(u.read_text()))
            except ValueError:
                entry["usage"] = None
                unavailable_usage += 1
        else:
            entry["usage"] = None
            unavailable_usage += 1
        usage[d.name] = entry

    # cohort: first 12 new releases in publication order
    cohort = []
    pub_finish = {}
    for a in atts:
        if a["stage"] == "publish" and a["status"] == "done" and a["finished"]:
            ft = datetime.datetime.fromisoformat(a["finished"]).timestamp()
            if a["candidate"] not in pub_finish or ft < pub_finish[a["candidate"]]:
                pub_finish[a["candidate"]] = ft
    for c in cands:
        if c["cohort_group"] != "new-admission" or c["stage"] != "published":
            continue
        cohort.append({**{k: c[k] for k in ("id", "dataset", "version", "created", "updated")},
                        "published_at": iso(pub_finish[c["id"]]) if c["id"] in pub_finish else "[unavailable]"})
    cohort.sort(key=lambda x: (x["published_at"] == "[unavailable]", x["published_at"], x["id"]))
    cohort = cohort[:COHORT_SIZE]

    # git state: deployed HEAD + commits touching the repo during the window
    def git(args):
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()

    subprocess.run(["git", "-C", str(REPO), "fetch", "origin"], capture_output=True, text=True, timeout=120)
    deployed = git(["rev-parse", "HEAD"])
    origin_tip = git(["rev-parse", "origin/main"])
    window_commits = [l for l in git(["log", "--oneline", f"--since={COHORT_START}", "origin/main"]).splitlines() if l]

    out = {
        "summary": {"label": LABEL, "collected_at": collected_at,
                     "cohort_start": COHORT_START, "cohort_close": COHORT_CLOSE, "cohort_size_target": COHORT_SIZE,
                     "candidate_counts": {"carry-in": sum(1 for c in cands if c["cohort_group"] == "carry-in"),
                                          "new-admission": len(new_ids)},
                     "attempt_counts": {"carry-in": sum(1 for a in atts if a["cohort_group"] == "carry-in"),
                                        "new-admission": sum(1 for a in atts if a["cohort_group"] == "new-admission")},
                     "jobs_exported": len(jobs), "jobs_unavailable_oversize_or_invalid": unavailable_jobs,
                     "model_usage_recorded": sum(1 for v in usage.values() if v["usage"]),
                     "model_usage_unavailable": unavailable_usage,
                     "deployed_head": deployed, "origin_main": origin_tip,
                     "cohort_releases_so_far": len(cohort)},
        "cohort": cohort,
        "candidates_carry_in": [c for c in cands if c["cohort_group"] == "carry-in"],
        "candidates_new_admissions": [c for c in cands if c["cohort_group"] == "new-admission"],
        "attempts_carry_in": [a for a in atts if a["cohort_group"] == "carry-in"],
        "attempts_new_admissions": [a for a in atts if a["cohort_group"] == "new-admission"],
        "jobs_ledger": jobs,
        "model_usage": usage,
        "window_commits": window_commits,
    }

    # write evidence branch
    with tempfile.TemporaryDirectory(prefix="prospective-", dir="/opt/data/cache/scratch") as tmp:
        wt = Path(tmp) / "wt"
        base = ["git", "-C", str(REPO), "worktree", "add", "--detach", str(wt), "origin/main"]
        r = subprocess.run(["git", "-C", str(REPO), "ls-remote", "--heads", "origin", BRANCH], capture_output=True, text=True)
        if r.stdout.strip():
            base[-1] = f"origin/{BRANCH}"
        if subprocess.run(base, capture_output=True, text=True).returncode:
            print(f"prospective export [{LABEL}]: worktree setup failed; no push made")
            return 1
        if r.stdout.strip():
            subprocess.run(["git", "-C", str(wt), "branch", BRANCH, f"origin/{BRANCH}"], capture_output=True, text=True)
            subprocess.run(["git", "-C", str(wt), "checkout", BRANCH], capture_output=True, text=True)
        else:
            subprocess.run(["git", "-C", str(wt), "checkout", "-b", BRANCH], capture_output=True, text=True)
        root = wt / "audits/prospective-2026-11" / LABEL
        root.mkdir(parents=True)
        for name, blob in out.items():
            (root / f"{name}.json").write_text(json.dumps(blob, indent=1, sort_keys=False) + "\n")
        script_copy = root / "scout_prospective_export.py"
        script_copy.write_text(Path(__file__).read_text())
        note = root / "note.md"
        if note.exists():
            note_text = note.read_text()
        else:
            note_text = (f"# Prospective study export - {LABEL} ({collected_at})\n\n"
                         "Cohort: first 12 releases published {start} .. {close} (new admissions only; "
                         "the seven carry-in published releases are excluded from the cohort but fully exported).\n"
                         "Read-only ledger export: candidates, attempts (statuses, transitions, failure causes "
                         "verbatim up to caps), job records (durations, reservations), model usage per attempt. "
                         "Unavailable values are marked; secrets and bulk artifacts excluded. Factory operation "
                         "was never stopped or tuned for the study.\n\n"
                         "Defect repairs during the window are recorded in window_commits.json (repo commits) and "
                         "repairs.md below.\n").format(start=COHORT_START, close=COHORT_CLOSE)
        note.write_text(note_text)
        repairs = root / "repairs.md"
        rep = repairs.read_text() if repairs.exists() else "# Defect repairs / interventions during cohort window\n\n"
        if LABEL == "initial" and not rep.splitlines()[-1:] == ["- none within window so far"]:
            rep += "- none within window so far (pre-window context: 6238b7d research-window deploy incl. b8770b3 stale-inventory fix; 8fa9fc4 catalogue README retry fix)\n"
        repairs.write_text(rep)
        subprocess.run(["git", "-C", str(wt), "add", "audits/prospective-2026-11"], capture_output=True, text=True)
        st = subprocess.run(["git", "-C", str(wt), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        sha = None
        if st:
            subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m",
                            f"Prospective study {LABEL} export ({LABEL}): production ledger and resource usage"], capture_output=True, text=True)
            if subprocess.run(["git", "-C", str(wt), "push", "-u", "origin", BRANCH], capture_output=True, text=True).returncode:
                print(f"prospective export [{LABEL}]: push failed; evidence left in local worktree")
                return 1
            sha = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(wt)], capture_output=True, text=True)

    ci = "[not-checked]"
    if sha:
        for _ in range(8):
            try:
                url = f"https://api.github.com/repos/earino/dataset-factory/actions/runs?head_sha={sha}&per_page=1"
                runs = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "prospective-export"}), timeout=20).read())["workflow_runs"]
                if runs and runs[0]["status"] == "completed":
                    ci = f"run {runs[0]['id']} {runs[0]['conclusion']}"
                    break
                ci = f"run {runs[0]['id']} {runs[0]['status']}" if runs else "no runs yet"
            except OSError:
                ci = "[check-unavailable]"
            import time
            time.sleep(30)

    print(f"prospective export [{LABEL}]: push {'ok ' + sha if sha else 'no-change'} on {BRANCH}; "
          f"CI {ci}; carry-in {out['summary']['candidate_counts']['carry-in']} / "
          f"new {out['summary']['candidate_counts']['new-admission']}; cohort so far {len(cohort)}; "
          f"jobs {len(jobs)} (+{unavailable_jobs} unavailable); usage {out['summary']['model_usage_recorded']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
