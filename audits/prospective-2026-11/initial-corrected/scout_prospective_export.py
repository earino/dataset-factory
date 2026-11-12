#!/usr/bin/env python3
"""Prospective-study export: production candidate/attempt/job ledger + resource usage.

Cohort: first 12 releases with a verified publication (publish attempt done) inside
2026-11-12T21:27:59.319944Z .. 2026-11-17T17:00:00Z, in publication order. The seven
releases already published before cohort start are excluded by the window itself;
carry-in candidates newly published in the window ARE included, each labelled
carry-in / new-admission for production analysis.

Bounded: per-string caps, file-size caps, no secrets, no bulk artifacts, no
candidate-state writes, no model calls. Deterministic: fixed sort order, ISO
timestamps; only collected_at and git SHAs vary between runs.

Modes: "initial" (snapshot at cohort start) and "close" (scheduled at cohort close).
Default label is "close" so the bare cron invocation does the close export. Output
lands under audits/prospective-2026-11/<label>/ on evidence branch
scout/prospective-2026-11, pushed and CI-checked. Rerun-safe: existing label dirs
are reused (mkdir exist_ok), earlier labels (initial snapshot) are never touched.

Export-tooling corrections (2026-11-12, review of 9b530351): credential-shaped
redaction only (numeric token counts preserved); job records export created_at /
collected_at / deleted_at with derived duration instead of nonexistent started /
finished; cohort includes carry-in candidates published in-window; repeat runs safe;
CI non-success reported accurately.
"""
import datetime
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
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
JOB_RESULT_CAP = 600
JOB_FILE_CAP = 1_000_000
USAGE_FILE_CAP = 20_000
# Credential-shaped keys only: end-anchored bare "token" (not *_tokens counts).
DROP_KEYS = re.compile(r"ipv4|known_hosts|ssh|password|secret|credential|authorization|api_key|private_key|(^|_)token$", re.I)
ATT_RE = re.compile(r"^(rw-[0-9a-f]+)-(discover|build|evaluate|publish|qualify)-(\d+)$")


def iso(ts):
    return datetime.datetime.fromtimestamp(ts, UTC).isoformat() if ts else None


def parse_iso(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def cap(text, n):
    if text is None:
        return None
    s = str(text)
    return s if len(s) <= n else s[:n] + f"...[truncated {len(s) - n}]"


def sanitize(obj):
    if isinstance(obj, dict):
        return {k: ("[excluded]" if DROP_KEYS.search(str(k)) else sanitize(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


def main():
    collected_at = datetime.datetime.now(UTC).isoformat()
    start_dt = datetime.datetime.fromisoformat(COHORT_START)
    close_dt = datetime.datetime.fromisoformat(COHORT_CLOSE)
    start_ts, close_ts = start_dt.timestamp(), close_dt.timestamp()

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

    # verified publication per candidate: earliest done publish attempt, finished inside window
    pub_finish, pre_window_published = {}, set()
    for a in atts:
        if a["stage"] == "publish" and a["status"] == "done" and a["finished"]:
            ft = a["finished"]
            if a["candidate"] not in pub_finish or ft < pub_finish[a["candidate"]]:
                pub_finish[a["candidate"]] = ft
            if ft < start_ts:
                pre_window_published.add(a["candidate"])

    att_by_id = {}
    for a in atts:
        a["started"], a["finished"] = iso(a["started"]), iso(a["finished"])
        a["cohort_group"] = "carry-in" if a["candidate"] not in new_ids else "new-admission"
        a["result"] = cap(a["result"], RESULT_CAP)
        att_by_id[a["id"]] = a

    # jobs ledger: actual fields (created_at / collected_at / deleted_at), derived duration
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
        j = d.get("job") or {}
        m = ATT_RE.match(p.stem)
        created, collected, deleted = (parse_iso(d.get(k)) for k in ("created_at", "collected_at", "deleted_at"))
        rec = {
            "attempt": p.stem,
            "worker": m.group(1) if m else None,
            "stage": m.group(2) if m else d.get("stage") or "[unattributed]",
            "candidate": j.get("candidate"),
            "status": d.get("status"),
            "enabled": d.get("enabled"),
            "created_at": d.get("created_at"),
            "collected_at": d.get("collected_at"),
            "deleted_at": d.get("deleted_at"),
            "expires": d.get("expires"),
            "duration_seconds": round((deleted - created).total_seconds(), 3) if (created and deleted) else None,
            "reservation_eur": d.get("reservation_eur"),
            "rate_ceiling_eur": d.get("rate_ceiling_eur"),
            "provider_hourly_eur": d.get("provider_hourly_eur"),
            "reserved_hours": d.get("reserved_hours"),
            "budget_months": d.get("budget_months"),
            "server_id": d.get("server_id"),
            "server_type": j.get("server_type"),
            "location": j.get("location"),
            "cpus": j.get("cpus"),
            "memory_mb": j.get("memory_mb"),
            "timeout_minutes": j.get("timeout_minutes"),
            "lifetime_minutes": j.get("lifetime_minutes"),
            "max_disk_mb": j.get("max_disk_mb"),
            "max_artifact_mb": j.get("max_artifact_mb"),
            "cloud_calls": d.get("cloud_calls"),
            "source_bytes": d.get("source_bytes"),
            "source_sha256": d.get("source_sha256"),
            "staging_repo": d.get("staging_repo"),
            "project": d.get("project"),
            "note": d.get("note"),
            "result": cap(json.dumps(d.get("result")) if d.get("result") is not None else None, JOB_RESULT_CAP),
        }
        cand = rec["candidate"]
        rec["cohort_group"] = "carry-in" if (cand and cand not in new_ids) else ("new-admission" if cand else "[unattributed]")
        jobs.append(sanitize(rec))

    # model usage per attempt (numeric token counts preserved verbatim)
    usage, unavailable_usage, totals = {}, 0, {}
    for d in sorted((REPO / ".factory/model-tasks").iterdir()):
        if not d.is_dir():
            continue
        u = d / "usage.json"
        entry = {"attempt": d.name, "response_present": (d / "response.json").is_file(),
                 "stage": att_by_id.get(d.name, {}).get("stage", "[unattributed]")}
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
        if entry["usage"]:
            t = totals.setdefault(entry["stage"], {"attempts": 0, "elapsed_seconds": 0.0})
            t["attempts"] += 1
            t["elapsed_seconds"] = round(t["elapsed_seconds"] + float(entry["usage"].get("elapsed_seconds") or 0), 3)
            for task in entry["usage"].get("tasks") or []:
                for k in ("calls", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                    t[k] = t.get(k, 0) + (task.get(k) or 0)

    # cohort: ALL candidates verified-published inside the window (carry-in or new),
    # excluding only those already published before cohort start; first 12 by publication order
    in_window = []
    for c in cands:
        ft = pub_finish.get(c["id"])
        if c["stage"] != "published" or ft is None:
            continue
        if ft < start_ts or ft > close_ts:
            continue
        in_window.append({"id": c["id"], "dataset": c.get("dataset"), "version": c.get("version"),
                          "cohort_group": c["cohort_group"], "created": c["created"],
                          "published_at": iso(ft),
                          "attempt_count": sum(1 for a in atts if a["candidate"] == c["id"])})
    in_window.sort(key=lambda x: (x["published_at"], x["id"]))
    cohort = in_window[:COHORT_SIZE]

    def git(args):
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()

    subprocess.run(["git", "-C", str(REPO), "fetch", "origin"], capture_output=True, text=True, timeout=120)
    deployed = git(["rev-parse", "HEAD"])
    origin_tip = git(["rev-parse", "origin/main"])
    window_commits = [l for l in git(["log", "--oneline", f"--since={COHORT_START}", "origin/main"]).splitlines() if l]

    out = {
        "summary": {"label": LABEL, "collected_at": collected_at,
                    "cohort_definition": {"window_start": COHORT_START, "window_close": COHORT_CLOSE,
                                          "first_n_publication_order": COHORT_SIZE,
                                          "rule": "candidates with earliest done publish attempt finished inside the window; "
                                                  "releases already published before cohort start excluded; "
                                                  "carry-in and new-admission labels retained per candidate"},
                    "candidate_counts": {"carry-in": sum(1 for c in cands if c["cohort_group"] == "carry-in"),
                                         "new-admission": len(new_ids)},
                    "attempt_counts": {"carry-in": sum(1 for a in atts if a["cohort_group"] == "carry-in"),
                                       "new-admission": sum(1 for a in atts if a["cohort_group"] == "new-admission")},
                    "published_pre_window_excluded": len(pre_window_published),
                    "published_in_window_total": len(in_window),
                    "cohort_releases_so_far": len(cohort),
                    "jobs_exported": len(jobs), "jobs_unavailable_oversize_or_invalid": unavailable_jobs,
                    "model_usage_recorded": sum(1 for v in usage.values() if v["usage"]),
                    "model_usage_unavailable": unavailable_usage,
                    "deployed_head": deployed, "origin_main": origin_tip},
        "usage_totals_by_stage": totals,
        "cohort": cohort,
        "candidates_carry_in": [c for c in cands if c["cohort_group"] == "carry-in"],
        "candidates_new_admissions": [c for c in cands if c["cohort_group"] == "new-admission"],
        "attempts_carry_in": [a for a in atts if a["cohort_group"] == "carry-in"],
        "attempts_new_admissions": [a for a in atts if a["cohort_group"] == "new-admission"],
        "jobs_ledger": jobs,
        "model_usage": usage,
        "window_commits": window_commits,
    }

    with tempfile.TemporaryDirectory(prefix="prospective-", dir="/opt/data/cache/scratch") as tmp:
        wt = Path(tmp) / "wt"
        r = subprocess.run(["git", "-C", str(REPO), "ls-remote", "--heads", "origin", BRANCH],
                          capture_output=True, text=True)
        on_branch = bool(r.stdout.strip())
        base = ["git", "-C", str(REPO), "worktree", "add", "--detach", str(wt),
                f"origin/{BRANCH}" if on_branch else "origin/main"]
        if subprocess.run(base, capture_output=True, text=True).returncode:
            print(f"prospective export [{LABEL}]: worktree setup failed; no push made")
            return 1
        if on_branch:
            subprocess.run(["git", "-C", str(wt), "checkout", "-B", BRANCH, f"origin/{BRANCH}"],
                           capture_output=True, text=True)
        else:
            subprocess.run(["git", "-C", str(wt), "checkout", "-b", BRANCH], capture_output=True, text=True)
        root = wt / "audits/prospective-2026-11" / LABEL
        root.mkdir(parents=True, exist_ok=True)  # rerun-safe; other label dirs untouched
        for name, blob in out.items():
            (root / f"{name}.json").write_text(json.dumps(blob, indent=1, sort_keys=False) + "\n")
        (root / "scout_prospective_export.py").write_text(Path(__file__).read_text())
        (root / "note.md").write_text(
            f"# Prospective study export - {LABEL} ({collected_at})\n\n"
            f"Cohort: first {COHORT_SIZE} releases verified-published {COHORT_START} .. {COHORT_CLOSE}, "
            "in publication order. Only the releases already published before cohort start are excluded; "
            "carry-in candidates newly published inside the window are included, each labelled "
            "carry-in / new-admission for production analysis.\n\n"
            "Read-only ledger export: candidates, attempts (statuses, transitions, failure causes "
            "verbatim up to caps), job records (created/collected/deleted timestamps, derived duration, "
            "reservations), model usage per attempt with numeric token counts preserved. Unavailable "
            "values are marked; secrets and bulk artifacts excluded; ipv4/known_hosts dropped. Factory "
            "operation was never stopped or tuned for the study; all attempts, failures and "
            "interventions preserved.\n\n"
            "Defect repairs: window_commits.json lists repo commits during the window; repairs.md "
            "records export-tooling corrections. Initial snapshot 9b530351 retained unmodified.\n")
        (root / "repairs.md").write_text(
            "# Defect repairs / interventions during cohort window\n\n"
            "## Export tooling (2026-11-12, corrections to initial snapshot 9b530351)\n"
            "- sanitizer redacted numeric token counts (input_tokens etc. matched a bare 'token' rule); "
            "now credential-shaped keys only - numeric usage preserved\n"
            "- jobs export used nonexistent started/finished fields; now exports created_at/collected_at/"
            "deleted_at and derives duration when both ends exist\n"
            "- cohort wrongly excluded all carry-in candidates; now only pre-window published releases "
            "are excluded (verified publication timestamp inside window, publication order)\n"
            "- repeat close export made rerun-safe (mkdir exist_ok, earlier labels untouched)\n"
            "- CI check reports all workflow runs and non-success explicitly\n\n"
            "## Factory workflow\n- none within the cohort window so far (pre-window context: 6238b7d "
            "research-window deploy incl. b8770b3 stale-inventory fix; 8fa9fc4 catalogue README retry "
            "fix). Repo commits during the window: window_commits.json\n")
        subprocess.run(["git", "-C", str(wt), "add", "audits/prospective-2026-11"], capture_output=True, text=True)
        st = subprocess.run(["git", "-C", str(wt), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        sha = None
        if st:
            subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m",
                            f"Prospective study {LABEL} export: production ledger and resource usage"],
                           capture_output=True, text=True)
            push = subprocess.run(["git", "-C", str(wt), "push", "-u", "origin", BRANCH],
                                   capture_output=True, text=True)
            if push.returncode:
                print(f"prospective export [{LABEL}]: push FAILED; evidence left in local worktree")
                return 1
            sha = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(wt)],
                       capture_output=True, text=True)

    ci = "[no-commit]"
    if sha:
        ci, waited = "[not-yet-reported]", 0
        while waited <= 300:
            try:
                url = f"https://api.github.com/repos/earino/dataset-factory/actions/runs?head_sha={sha}&per_page=10"
                req = urllib.request.Request(url, headers={"User-Agent": "prospective-export"})
                runs = json.loads(urllib.request.urlopen(req, timeout=20).read())["workflow_runs"]
                if runs and all(r["status"] == "completed" for r in runs):
                    ci = "; ".join(f"{r['name']}={r['conclusion']}({r['id']})" for r in runs)
                    break
                if runs:
                    ci = "in-progress: " + "; ".join(f"{r['name']}={r['status']}" for r in runs)
            except OSError:
                ci = "[check-unavailable]"
            time.sleep(30)
            waited += 30
        else:
            ci = f"NOT CONFIRMED after 300s: {ci}"
    print(f"prospective export [{LABEL}]: push {'ok ' + sha if sha else 'no-change (already exported)'} "
          f"on {BRANCH}; CI {ci}; carry-in {out['summary']['candidate_counts']['carry-in']} / "
          f"new {out['summary']['candidate_counts']['new-admission']}; published-in-window "
          f"{len(in_window)} (cohort so far {len(cohort)}); jobs {len(jobs)} (+{unavailable_jobs} unavailable); "
          f"usage {out['summary']['model_usage_recorded']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
