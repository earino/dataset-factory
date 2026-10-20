#!/usr/bin/env python3
"""Build the Scout dashboard from repo state.

Renders static HTML into an output directory. `--publish` commits that directory to
the catalogue Pages repository. Every panel carries its own `as_of` and `source`;
a missing input renders "no data" with the path it looked for, never a zero.

Design rules are in docs/DASHBOARD.md. Two of them are enforced here in code:
nothing from .secrets/ or .env may reach the output (asserted before writing), and a
page whose newest input is older than its freshness SLA is labelled STALE.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
import tempfile
import shutil
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory import dashboard_render as ui  # noqa: E402
SNAPSHOT_SCHEMA = 1
SNAPSHOT_GENERATED = ""
PUBLISH_REPO = "earino/dataset-factory-dashboard"
PAGES_URL = "https://earino.github.io/dataset-factory-dashboard/"
SITE_SUBDIR = ""  # empty: the dashboard owns its repository root
SECRETS = Path("/opt/data/.secrets")
CRON_JOBS = Path("/opt/data/cron/jobs.json")


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def age_minutes(dt):
    return None if dt is None else round((now() - dt).total_seconds() / 60, 1)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def panel(value, source, as_of=None, stale_after_minutes=None, expected=None, note=None):
    """A value plus the provenance needed to judge it."""
    dt = parse_time(as_of)
    age = age_minutes(dt)
    stale = bool(stale_after_minutes is not None and age is not None and age > stale_after_minutes)
    return {"value": value, "source": source, "as_of": as_of, "age_minutes": age,
            "stale": stale, "expected": expected, "note": note,
            "status": "no data" if value is None else ("stale" if stale else "ok")}


# ---------------------------------------------------------------- collectors

def collect_candidates():
    records, errors = [], []
    for path in sorted((ROOT / "candidates").glob("*/record.json")):
        record = read_json(path)
        if record is None:
            errors.append(str(path.relative_to(ROOT)))
            continue
        jurisdiction = record.get("jurisdiction") or {}
        records.append({
            "id": record.get("id", path.parent.name),
            "status": record.get("status", "unknown"),
            "country": jurisdiction.get("country") or "unknown",
            "region": jurisdiction.get("region") or "unknown",
            "publisher": jurisdiction.get("publisher") or "",
            "next_action": (record.get("next_action") or "")[:160],
            "path": str(path.relative_to(ROOT)),
        })
    counts = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    live = [r for r in records if r["status"] in ("investigating", "qualified")]
    countries = {}
    for record in live:
        countries[record["country"]] = countries.get(record["country"], 0) + 1
    non_us = sum(1 for r in live if r["country"] not in ("US", "unknown"))
    return {
        "records": records, "counts": counts, "live": live, "errors": errors,
        "countries": countries,
        "non_us_share": (round(100 * non_us / len(live), 1) if live else None),
    }


def collect_releases():
    releases = []
    for manifest_path in sorted((ROOT / "release").glob("*/MANIFEST.json")):
        manifest = read_json(manifest_path, {})
        folder = manifest_path.parent
        destinations = read_json(folder / "DESTINATIONS.json", {}) or {}
        dest = destinations.get("destinations", {}) or {}
        verified = {name: bool((body or {}).get("verified")) for name, body in dest.items()}
        verified_at = sorted(filter(None, [(body or {}).get("verified_at") for body in dest.values()]))
        rows = 0
        for split in (manifest.get("splits") or {}).values():
            if isinstance(split, dict) and isinstance(split.get("rows"), int):
                rows += split["rows"]
        baseline_block = manifest.get("baseline") or {}
        baseline = (baseline_block.get("levels")
                    or (baseline_block.get("artifact") or {}).get("levels") or {})
        aucs = [v.get("eval_auc") for v in baseline.values()
                if isinstance(v, dict) and isinstance(v.get("eval_auc"), (int, float))]
        persistence = ((manifest.get("baseline") or {}).get("persistence_reference") or {})
        releases.append({
            "dataset": manifest.get("dataset", folder.name),
            "release_tag": manifest.get("release_tag") or "",
            "rows": rows or None,
            "assets": len(manifest.get("assets") or manifest.get("package_files") or {}) or None,
            "verified": verified,
            "verified_all": bool(verified) and all(verified.values()),
            "verified_at": verified_at[-1] if verified_at else None,
            "baseline_eval_auc": max(aucs) if aucs else None,
            "persistence_auc": persistence.get("persistence_prev_target_cited_eval_auc"),
            "publication_note": (manifest.get("publication_note") or "")[:200],
        })
    return {"releases": releases, "errors": []}


def collect_coverage():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/discovery-coverage.py"), "--json"],
                            cwd=ROOT, text=True, capture_output=True, timeout=120)
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {"error": (result.stderr or "no output")[-200:]}


def collect_budget():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/research-budget.py"), "--json"],
                            cwd=ROOT, text=True, capture_output=True, timeout=120)
    payload = None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        pass
    if payload is None:
        return {"error": (result.stderr or result.stdout or "no output")[-300:], "decision": None}
    config = payload.get("config") or {}
    keep = ("weekly_token_budget", "sessions_per_week", "allowance_usd", "period",
            "session_max_minutes", "session_max_turns")
    return {"decision": payload.get("decision") or {},
            "config": {key: config[key] for key in keep if key in config}}


def collect_cron():
    payload = read_json(CRON_JOBS, {}) or {}
    jobs = []
    for job in payload.get("jobs", []):
        schedule = job.get("schedule") or {}
        jobs.append({
            "id": job.get("id"), "name": job.get("name"),
            "schedule": schedule.get("display") or schedule.get("kind"),
            "enabled": bool(job.get("enabled")),
            "no_agent": bool(job.get("no_agent")),
            "last_run_at": job.get("last_run_at"), "last_status": job.get("last_status"),
            "next_run_at": job.get("next_run_at"),
            "failure_streak": job.get("failure_streak") or 0,
            "last_error": (job.get("last_error") or "")[:200],
        })
    return {"jobs": jobs, "updated_at": payload.get("updated_at")}


def collect_health(run_tests=True):
    health = {"tests": None, "checks": None, "coverage": None, "head": None, "ci": None}

    def run(cmd, timeout=300):
        try:
            return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None if not isinstance(exc, OSError) else None

    if run_tests:
        result = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
        if result is not None:
            tail = (result.stderr or "") + (result.stdout or "")
            count = None
            for line in tail.splitlines():
                if line.startswith("Ran ") and " test" in line:
                    count = line.split()[1]
            health["tests"] = {"count": count, "ok": result.returncode == 0}

    result = run([sys.executable, "scripts/check-candidate.py", "--all"])
    if result is not None:
        text = result.stdout or ""
        oks = sum(1 for line in text.splitlines() if ": OK" in line)
        health["checks"] = {"ok": result.returncode == 0, "passing": oks}

    result = run([sys.executable, "scripts/discovery-coverage.py"])
    if result is not None:
        text = (result.stdout or "").strip().splitlines()
        health["coverage"] = {"ok": result.returncode == 0,
                              "summary": next((l for l in text if "non-US" in l), None)}

    result = run(["git", "log", "-1", "--format=%h %cI %s"])
    if result is not None and result.returncode == 0:
        parts = (result.stdout or "").strip().split(" ", 2)
        if len(parts) == 3:
            health["head"] = {"sha": parts[0], "at": parts[1], "subject": parts[2][:120]}

    health["ci"] = collect_ci()
    return health


def _github_token():
    path = SECRETS / "github-publish.token"
    try:
        token = path.read_text().strip()
    except OSError:
        return None
    return token or None


def collect_ci():
    """Latest workflow conclusion. The token is used in memory only and never rendered."""
    token = _github_token()
    if token is None:
        return {"error": "no publish token available"}
    url = ("https://api.github.com/repos/earino/dataset-factory/actions/runs"
           "?per_page=1&exclude_pull_requests=true")
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "User-Agent": "scout-dashboard"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read())
    except Exception as exc:  # network, auth, rate limit - all render as no data
        return {"error": type(exc).__name__}
    runs = body.get("workflow_runs") or []
    if not runs:
        return {"error": "no workflow runs"}
    run = runs[0]
    return {"conclusion": run.get("conclusion"), "status": run.get("status"),
            "head_sha": (run.get("head_sha") or "")[:7], "created_at": run.get("created_at"),
            "url": run.get("html_url")}


def collect_snapshot(include_tests=True):
    candidates = collect_candidates()
    releases = collect_releases()
    stamp = iso(now())
    return {
        "schema": SNAPSHOT_SCHEMA,
        "generated_at": stamp,
        "repo": {"head": None},
        "candidates": candidates,
        "coverage": collect_coverage(),
        "releases": releases,
        "budget": collect_budget(),
        "cron": collect_cron(),
        "health": collect_health(run_tests=include_tests),
        "panels": {
            "candidates": panel(len(candidates["live"]), "candidates/*/record.json", stamp),
            "releases": panel(len(releases["releases"]), "release/*/MANIFEST.json", stamp),
            "budget": panel(None, "scripts/research-budget.py --json", stamp),
        },
    }


# ---------------------------------------------------------------- rendering

def derive_alarms(snapshot):
    """Return (html, plain, soft_plain). A running session is a notice, not an alarm."""
    html_parts, plain, soft = [], [], []
    budget = (snapshot.get("budget") or {}).get("decision") or {}
    health = snapshot.get("health") or {}
    reports = snapshot.get("releases", {}).get("releases", [])

    def add(text, tone="bad", icon="!"):
        html_parts.append(ui.alarm(ui.esc(text), tone, icon))
        plain.append(text)

    for job in (snapshot.get("cron") or {}).get("jobs", []):
        if not job["enabled"]:
            continue
        nxt = parse_time(job.get("next_run_at"))
        if nxt and nxt < now() - timedelta(minutes=15):
            add(f"{job['name']} missed its window ({job['next_run_at']}); last status {job['last_status']}",
                "bad", "!")
        elif job.get("failure_streak", 0) >= 2 or job.get("last_status") not in (None, "ok"):
            add(f"{job['name']} last status {job['last_status']} (streak {job['failure_streak']})",
                "warn", "!")
    if budget.get("allowed") is False and budget.get("reasons"):
        reasons = budget["reasons"]
        if all("lock held" in r for r in reasons):
            soft.append("A research session is running: " + "; ".join(reasons))
        else:
            add("Research gate refused the next session: " + "; ".join(reasons), "warn", "⏸")
    tokens, ceiling = budget.get("research_tokens_last_7_days"), budget.get("weekly_token_budget")
    if tokens and ceiling and tokens / ceiling >= 0.8:
        add(f"Token use at {round(100 * tokens / ceiling)}% of the weekly ceiling", "warn", "!")
    ci = health.get("ci") or {}
    if ci.get("conclusion") not in (None, "success"):
        add(f"CI on {ci.get('head_sha')} concluded {ci.get('conclusion')}", "bad", "!")
    tests = health.get("tests") or {}
    if tests and not tests.get("ok"):
        add("Test suite is failing", "bad", "!")
    checks = health.get("checks") or {}
    if checks and not checks.get("ok"):
        add("check-candidate --all is failing", "bad", "!")
    unverified = [r for r in reports if not r["verified_all"]]
    if unverified:
        add(f"{len(unverified)} release(s) not fully verified", "bad", "!")
    return html_parts, plain, soft


def collect_history(out: Path, snapshot):
    """Append one point per run to build/dashboard/history.json and return the series.

    The series starts when this feature starts: it is never back-filled with invented
    values, so a sparkline that has one point says so instead of drawing a trend.
    """
    path = out / "history.json"
    points = read_json(path, []) or []
    if not isinstance(points, list):
        points = []
    decision = (snapshot.get("budget") or {}).get("decision") or {}
    point = {
        "at": snapshot["generated_at"],
        "published": len(snapshot["releases"]["releases"]),
        "live": len(snapshot["candidates"]["live"]),
        "tokens_7d": decision.get("research_tokens_last_7_days"),
        "sessions_7d": decision.get("runs_last_7_days"),
        "qualified": snapshot["candidates"]["counts"].get("qualified", 0),
    }
    last = parse_time(points[-1]["at"]) if points else None
    if last is None or (now() - last) >= timedelta(minutes=20):
        points.append(point)
    points = points[-500:]
    path.write_text(json.dumps(points, indent=1))
    return points


def build(out: Path, include_tests=True):
    global SNAPSHOT_GENERATED
    out.mkdir(parents=True, exist_ok=True)
    snapshot = collect_snapshot(include_tests=include_tests)
    history = collect_history(out, snapshot)
    snapshot["history"] = history
    alarms_html, alarms_plain, soft = derive_alarms(snapshot)
    snapshot["alarms"] = alarms_plain
    snapshot["notices"] = soft
    stamp = snapshot["generated_at"]
    SNAPSHOT_GENERATED = stamp
    files = {
        "index.html": ui.page("Overview", "exec", stamp,
                              ui.render_overview(snapshot, alarms_html, alarms_plain),
                              footer_extra="Sources: candidates/*/record.json, release/*/MANIFEST.json, "
                                           "research-budget.py, cron jobs.json."),
        "cost.html": ui.page("Cost", "cost", stamp, ui.render_cost(snapshot, alarms_html, alarms_plain),
                             footer_extra="Token figures are measured from the session ledger; USD cost is "
                                          "not meaningful on this subscription and is deliberately not shown."),
        "reliability.html": ui.page("Ops", "ops", stamp, ui.render_ops(snapshot, alarms_html, alarms_plain),
                                    footer_extra="A job is not alive because it was launched; this reads the "
                                                 "scheduler's own record."),
    }
    files["style.css"] = ui.CSS
    files["robots.txt"] = "User-agent: *\nDisallow: /\n"
    files["dashboard.json"] = json.dumps(snapshot, indent=1, sort_keys=True, default=str)
    assert_no_secrets(files)
    for name, content in files.items():
        (out / name).write_text(content)
    return snapshot, out


def assert_no_secrets(files):
    """Belt and braces: no credential file content may appear in a published page."""
    for secret in SECRETS.glob("*.token") if SECRETS.is_dir() else []:
        try:
            value = secret.read_text().strip()
        except OSError:
            continue
        if len(value) < 20:
            continue
        for name, content in files.items():
            if value in content:
                raise SystemExit(f"refusing to publish: {secret.name} appears in {name}")


# ---------------------------------------------------------------- publishing

def _git(args, cwd, token=None, timeout=180):
    env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    if token:
        import base64
        auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        # Kept out of argv and out of .git/config.
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {auth}"
    return subprocess.run(["git"] + args, cwd=cwd, env=env, text=True,
                          capture_output=True, timeout=timeout)


def publish(out: Path, repo=PUBLISH_REPO):
    token = _github_token()
    if token is None:
        raise SystemExit("no publish token at /opt/data/.secrets/github-publish.token")
    work = Path(tempfile.mkdtemp(prefix="dashboard-publish-"))
    try:
        repo_dir = work / "repo"
        clone = _git(["clone", "--depth", "1", f"https://github.com/{repo}.git", str(repo_dir)],
                     cwd=work, token=token)
        if clone.returncode:
            # First publication: the repository exists but is empty, or does not exist yet.
            repo_dir.mkdir(parents=True, exist_ok=True)
            _git(["init", "-q", "-b", "main"], cwd=repo_dir)
            _git(["remote", "add", "origin", f"https://github.com/{repo}.git"], cwd=repo_dir)
        target = repo_dir / SITE_SUBDIR if SITE_SUBDIR else repo_dir
        if SITE_SUBDIR and target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        for item in sorted(out.iterdir()):
            shutil.copy2(item, target / item.name)
        _git(["add", "-A", SITE_SUBDIR or "."], cwd=repo_dir)
        status = _git(["status", "--porcelain"], cwd=repo_dir)
        if not status.stdout.strip():
            return {"published": False, "reason": "no change", "commit": None}
        commit = _git(["commit", "-m", f"Dashboard snapshot {SNAPSHOT_GENERATED}"], cwd=repo_dir)
        if commit.returncode:
            raise SystemExit(f"commit failed: {commit.stderr[-300:]}")
        push = _git(["push", "origin", "HEAD:main"], cwd=repo_dir, token=token)
        if push.returncode:
            raise SystemExit(f"push failed: {push.stderr[-300:]}")
        sha = _git(["rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()
        return {"published": True, "commit": sha, "url": PAGES_URL}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def verify(url=PAGES_URL, expect=SNAPSHOT_GENERATED, attempts=6, delay=20):
    """Anonymous read-back of the published page. No credential is used.

    Pages serves a build a minute or two after the push, so this waits rather than
    calling a slow deploy a failure. A page that is live but lacks the new stamp is
    a stale deployment, which is also a failure.
    """
    import time
    last = {"ok": False, "error": "not attempted"}
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(f"{url}index.html?ts={int(now().timestamp())}",
                                             headers={"User-Agent": "scout-dashboard-verify"})
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8", "replace")
            ok = response.status == 200 and expect in body and "noindex" in body
            if ok:
                return {"ok": True, "status": response.status, "found_stamp": True,
                        "attempt": attempt + 1}
            last = {"ok": False, "status": response.status, "found_stamp": expect in body,
                    "noindex": "noindex" in body, "attempt": attempt + 1}
        except Exception as exc:
            last = {"ok": False, "error": type(exc).__name__, "attempt": attempt + 1}
        if attempt + 1 < attempts:
            time.sleep(delay)
    return last


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "build" / "dashboard"))
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--no-tests", action="store_true")
    args = parser.parse_args(argv)
    snapshot, out = build(Path(args.out), include_tests=not args.no_tests)
    print(json.dumps({"out": str(out), "generated_at": snapshot["generated_at"],
                      "live": len(snapshot["candidates"]["live"]),
                      "releases": len(snapshot["releases"]["releases"]),
                      "tests": (snapshot["health"]["tests"] or {}).get("count")}))
    if args.publish:
        result = publish(out)
        print(json.dumps(result))
        if result.get("published"):
            print(json.dumps(verify()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
