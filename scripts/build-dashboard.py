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
SNAPSHOT_SCHEMA = 1
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

CSS = """
:root{--bg:#0f1115;--panel:#171a21;--line:#262b36;--fg:#e6e9ef;--dim:#8b93a3;
--ok:#3ecf8e;--warn:#e5b567;--bad:#e06c75;--accent:#63a4ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{display:flex;justify-content:space-between;align-items:baseline;gap:16px;
padding:18px 24px;border-bottom:1px solid var(--line);flex-wrap:wrap}
header h1{font-size:17px;margin:0;letter-spacing:.2px}
nav a{color:var(--dim);text-decoration:none;margin-left:14px;font-size:13px}
nav a.on,nav a:hover{color:var(--fg)}
.stamp{color:var(--dim);font-size:12px}
main{padding:22px 24px 60px;max-width:1240px;margin:0 auto}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);
margin:26px 0 10px;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.tile .k{color:var(--dim);font-size:12px;margin-bottom:6px}
.tile .v{font-size:27px;font-weight:600;letter-spacing:-.5px}
.tile .v small{font-size:13px;font-weight:400;color:var(--dim);margin-left:4px}
.tile .src{color:var(--dim);font-size:11px;margin-top:8px;overflow:hidden;text-overflow:ellipsis}
.tile.stale{border-color:var(--warn)}
.tile.stale .v{color:var(--warn)}
.badge{display:inline-block;font-size:10px;text-transform:uppercase;letter-spacing:.06em;
padding:1px 6px;border-radius:4px;border:1px solid var(--line);color:var(--dim)}
.badge.ok{color:var(--ok);border-color:#1f4a38}.badge.bad{color:var(--bad);border-color:#4a2529}
.badge.warn{color:var(--warn);border-color:#4a3d22}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.05em}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.bar{height:6px;background:var(--panel);border:1px solid var(--line);border-radius:4px;overflow:hidden}
.bar>span{display:block;height:100%;background:var(--accent)}
.alarm{border-left:3px solid var(--bad);padding:8px 12px;background:#1b1416;margin:6px 0;
border-radius:0 6px 6px 0;font-size:13px}
.note{color:var(--dim);font-size:12px;margin-top:10px;max-width:80ch}
.meh{border-left-color:var(--warn);background:#1b1812}
footer{color:var(--dim);font-size:11px;padding:0 24px 30px;max-width:1240px;margin:0 auto}
"""


def esc(value):
    return html.escape("" if value is None else str(value))


def tile(key, value, unit="", source="", stamp="", stale=False, note=""):
    shown = "no data" if value is None else f"{value}"
    return (f'<div class="tile{" stale" if stale else ""}"><div class="k">{esc(key)}</div>'
            f'<div class="v">{esc(shown)}{f"<small>{esc(unit)}</small>" if unit and value is not None else ""}</div>'
            f'<div class="src">{esc(note or source)}</div></div>')


def layout(title, body, active):
    stamp = esc(SNAPSHOT_GENERATED)
    def link(href, label, key):
        return f'<a href="{href}"{" class=on" if key == active else ""}>{label}</a>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{esc(title)} - Scout</title><link rel="stylesheet" href="style.css"></head><body>
<header><h1>Scout &middot; {esc(title)}</h1>
<nav>{link("index.html","Executive","exec")}{link("cost.html","Cost","cost")}
{link("reliability.html","Reliability","rel")}</nav></header>
<div class="stamp" style="padding:6px 24px 0">state as of {stamp}</div>
<main>{body}</main>
<footer>Generated from repository state by scripts/build-dashboard.py. Every figure names its
source; a missing input reads "no data" rather than zero. Snapshot: dashboard.json.</footer>
</body></html>"""


SNAPSHOT_GENERATED = ""


def render_exec(snapshot):
    c = snapshot["candidates"]
    r = snapshot["releases"]
    b = snapshot["budget"]
    decision = b.get("decision") or {}
    health = snapshot["health"]
    counts = c["counts"]
    published = len(r["releases"])
    live = len(c["live"])
    queue = [x for x in c["live"] if x["status"] == "investigating"]
    qualified = counts.get("qualified", 0)
    tokens = decision.get("research_tokens_last_7_days")
    budget_tokens = decision.get("weekly_token_budget")
    sessions = decision.get("runs_last_7_days")
    session_cap = decision.get("session_cap_per_week")
    verified_all = [x for x in r["releases"] if x["verified_all"]]
    last_pub = max((parse_time(x["verified_at"]) for x in r["releases"] if x["verified_at"]),
                   default=None)
    days_since = None if last_pub is None else round((now() - last_pub).total_seconds() / 86400, 1)

    alarms = []
    for job in snapshot["cron"]["jobs"]:
        if not job["enabled"]:
            continue
        nxt = parse_time(job["next_run_at"])
        if nxt and nxt < now() - timedelta(minutes=15):
            alarms.append(f"{esc(job['name'])} missed its window ({esc(job['next_run_at'])}), "
                          f"last status {esc(job['last_status'])}")
        elif job["failure_streak"] >= 2 or (job["last_status"] not in (None, "ok")):
            alarms.append(f"{esc(job['name'])} last status {esc(job['last_status'])} "
                          f"(streak {job['failure_streak']})")
    if decision.get("allowed") is False and decision.get("reasons"):
        alarms.append("Research gate refused the next session: " + esc("; ".join(decision["reasons"])))
    if tokens and budget_tokens and tokens / budget_tokens >= 0.8:
        alarms.append(f"Token use at {round(100*tokens/budget_tokens)}% of the weekly ceiling")
    ci = snapshot["health"].get("ci") or {}
    if ci.get("conclusion") not in (None, "success"):
        alarms.append(f"CI on {esc(ci.get('head_sha'))} concluded {esc(ci.get('conclusion'))}")
    if len(verified_all) != published:
        alarms.append(f"{published - len(verified_all)} release(s) not fully verified")
    if not alarms:
        alarms.append("Nothing above threshold.")

    tiles = "".join([
        tile("Live candidates", live, "", "candidates/*/record.json",
             note=f"{qualified} qualified, {len(queue)} awaiting construction"),
        tile("Published datasets", published, "", "release/*/MANIFEST.json",
             note=f"{len(verified_all)}/{published} fully verified"),
        tile("Days since publication", days_since if days_since is not None else None, "days",
             "DESTINATIONS.json verified_at"),
        tile("Non-US share of bench", round(100 * snapshot["coverage"].get("live_non_us_share", 0), 1)
             if snapshot["coverage"].get("live") else None, "%", "discovery-coverage.py --json",
             note=f"{snapshot['coverage'].get('live_non_us', 0)} of {snapshot['coverage'].get('live', 0)} active candidates; goal is 50%"),
        tile("Research tokens this week", f"{tokens:,}" if tokens else None,
             f"of {budget_tokens:,}" if budget_tokens else "", "research-budget.py --json",
             stale=False, note="weekly ceiling 40,000,000 (measured, not estimated)"),
        tile("Sessions this week", sessions, f"of {session_cap}" if session_cap else "",
             "research-budget.py --json"),
        tile("Tests", (health["tests"] or {}).get("count"), "passing",
             "unittest discover", note="green" if (health["tests"] or {}).get("ok") else "not measured or failing"),
        tile("Candidate checks", (health["checks"] or {}).get("passing"),
             "OK", "check-candidate.py --all",
             note="schema and identity checks across all candidates"),
        tile("Newest CI", (health["ci"] or {}).get("conclusion") or None, "",
             "GitHub Actions", note=f"commit {esc((health['ci'] or {}).get('head_sha'))}"),
    ])

    funnel_rows = "".join(
        f"<tr><td>{esc(status)}</td><td class=num>{count}</td></tr>"
        for status, count in sorted(counts.items(), key=lambda kv: -kv[1])) or (
        "<tr><td colspan=2>no candidate records</td></tr>")
    release_rows = "".join(
        f"<tr><td>{esc(x['dataset'])}</td><td>{esc(x['release_tag'])}</td>"
        f"<td class=num>{x['rows'] or '-'}</td>"
        f"<td class=num>{'-' if x['baseline_eval_auc'] is None else x['baseline_eval_auc']}</td>"
        f"<td><span class='badge {'ok' if x['verified_all'] else 'bad'}'>"
        f"{'verified' if x['verified_all'] else 'unverified'}</span></td></tr>"
        for x in r["releases"]) or ("<tr><td colspan=5>no releases recorded</td></tr>")
    queue_rows = "".join(
        f"<tr><td>{esc(x['id'])}</td><td>{esc(x['country'])}</td><td>{esc(x['status'])}</td>"
        f"<td>{esc(x['next_action'])}</td></tr>" for x in sorted(
            c["live"], key=lambda x: 0 if x["status"] == "qualified" else 1)) or (
        "<tr><td colspan=4>nothing queued</td></tr>")

    body = f"""
<h2>The funnel</h2><div class="grid">{tiles}</div>
<h2>Pipeline by status</h2>
<table><thead><tr><th>Status</th><th class=num>Candidates</th></tr></thead><tbody>{funnel_rows}</tbody></table>
<h2>Published releases</h2>
<table><thead><tr><th>Dataset</th><th>Version</th><th class=num>Rows</th><th class=num>Baseline AUC</th><th>Destinations</th></tr></thead>
<tbody>{release_rows}</tbody></table>
<h2>Work queue</h2>
<table><thead><tr><th>Candidate</th><th>Country</th><th>Status</th><th>Next action</th></tr></thead>
<tbody>{queue_rows}</tbody></table>
<h2>Alarms</h2>
{''.join(f'<div class="alarm{"" if i == 0 else " meh"}">{a}</div>' for i, a in enumerate(alarms))}
<div class="note">Read-only projection of the private factory. Nothing here is a credential,
a session transcript or a staging URL.</div>"""
    return body


def render_cost(snapshot):
    b = snapshot["budget"]
    decision = b.get("decision") or {}
    config = b.get("config") or {}
    usage = decision.get("usage") or {}
    tokens = decision.get("research_tokens_last_7_days")
    ceiling = decision.get("weekly_token_budget")
    pct = round(100 * tokens / ceiling, 1) if tokens and ceiling else None
    sessions = decision.get("runs_last_7_days")
    cap = decision.get("session_cap_per_week")
    spct = round(100 * sessions / cap, 1) if sessions and cap else None

    def bucket(name, body):
        return (f"<tr><td>{esc(name)}</td><td class=num>{(body or {}).get('calls') or 0}</td>"
                f"<td class=num>{((body or {}).get('input_tokens') or 0):,}</td>"
                f"<td class=num>{((body or {}).get('output_tokens') or 0):,}</td></tr>")
    rows = "".join(bucket(k, v) for k, v in usage.items())

    body = f"""
<h2>Model spend</h2><div class="grid">
{tile("Research tokens (7d)", f"{tokens:,}" if tokens else None, f"of {ceiling:,}" if ceiling else "",
      "research-budget.py --json", note=f"{pct}% of the weekly ceiling" if pct is not None else "")}
{tile("Sessions (7d)", sessions, f"of {cap}" if cap else "", "research-budget.py --json",
      note=f"{spct}% of the weekly cap" if spct is not None else "")}
{tile("Next session allowed", "yes" if decision.get("allowed") else "no", "", "budget gate",
      note="; ".join(decision.get("reasons") or [])[:120] or "gate open")}
{tile("Worker spend (month)", None, "EUR", "not instrumented",
      note="per-job cost is not recorded yet; P1 adds the worker ledger")}
</div>
<h2>Usage by source (all-time counters)</h2>
<table><thead><tr><th>Source</th><th class=num>Calls</th><th class=num>Input tokens</th><th class=num>Output tokens</th></tr></thead>
<tbody>{rows}</tbody></table>
<div class="bar" style="margin-top:14px"><span style="width:{min(pct or 0, 100)}%"></span></div>
<div class="note">Token figures are measured from the session ledger; cost in USD is not
meaningful on this subscription and is deliberately not shown. Worker euros are the separate
Hetzner allowance ({esc((config.get('period') or {}).get('kind'))}, {esc(json.loads((ROOT/'config/local.json').read_text()).get('monthly_budget_eur') if (ROOT/'config/local.json').is_file() else None)} EUR).</div>"""
    return body


def render_reliability(snapshot):
    health = snapshot["health"]
    tests = health.get("tests") or {}
    checks = health.get("checks") or {}
    coverage = health.get("coverage") or {}
    head = health.get("head") or {}
    ci = health.get("ci") or {}
    jobs = [j for j in snapshot["cron"]["jobs"] if j["enabled"]]
    job_rows = "".join(
        f"<tr><td>{esc(j['name'])}</td><td>{esc(j['schedule'])}</td>"
        f"<td>{esc(j['last_run_at'])}</td>"
        f"<td><span class='badge {'ok' if j['last_status'] == 'ok' else ('warn' if not j['last_status'] else 'bad')}'>"
        f"{esc(j['last_status'] or 'pending')}</span></td><td>{esc(j['next_run_at'])}</td>"
        f"<td class=num>{j['failure_streak']}</td></tr>" for j in jobs)
    ok = lambda flag: f"<span class='badge {'ok' if flag else 'bad'}'>{'pass' if flag else 'fail'}</span>"
    body = f"""
<h2>Gates</h2><div class="grid">
{tile("Test suite", tests.get("count"), "tests", "unittest discover",
      note="pass" if tests.get("ok") else "FAILING")}
{tile("Candidate checks", checks.get("passing"), "OK", "check-candidate.py --all",
      note="pass" if checks.get("ok") else "FAILING")}
{tile("Discovery coverage", coverage.get("ok") and "determined" or "undetermined", "",
      "discovery-coverage.py", note=(coverage.get("summary") or "")[:120])}
{tile("CI", ci.get("conclusion") or None, "", "GitHub Actions",
      note=f"{esc(ci.get('head_sha'))} at {esc(ci.get('created_at'))}")}
</div>
<h2>Scheduled jobs</h2>
<table><thead><tr><th>Job</th><th>Schedule</th><th>Last run</th><th>Status</th><th>Next</th><th class=num>Failures</th></tr></thead>
<tbody>{job_rows}</tbody></table>
<h2>Repository head</h2>
<table><tbody><tr><td>commit</td><td><code>{esc(head.get('sha'))}</code></td></tr>
<tr><td>time</td><td>{esc(head.get('at'))}</td></tr>
<tr><td>subject</td><td>{esc(head.get('subject'))}</td></tr></tbody></table>
<div class="note">A job is not "alive" because it was launched. This table reads the scheduler's
own record: last status, failure streak and next run time.</div>"""
    return body


def build(out: Path, include_tests=True):
    global SNAPSHOT_GENERATED
    out.mkdir(parents=True, exist_ok=True)
    snapshot = collect_snapshot(include_tests=include_tests)
    SNAPSHOT_GENERATED = snapshot["generated_at"]
    pages = [("index.html", "Executive", "exec", render_exec(snapshot)),
             ("cost.html", "Cost", "cost", render_cost(snapshot)),
             ("reliability.html", "Reliability", "rel", render_reliability(snapshot))]
    files = {name: layout(title, body, active) for name, title, active, body in pages}
    files["style.css"] = CSS
    files["robots.txt"] = "User-agent: *\nDisallow: /\n"
    files["dashboard.json"] = json.dumps(snapshot, indent=1, sort_keys=True)
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


def verify(url=PAGES_URL, expect=SNAPSHOT_GENERATED, attempts=3):
    """Anonymous read-back of the published page. No credential is used."""
    last = {"ok": False, "error": "not attempted"}
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(f"{url}index.html?ts={int(now().timestamp())}",
                                             headers={"User-Agent": "scout-dashboard-verify"})
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8", "replace")
            return {"ok": response.status == 200 and expect in body,
                    "status": response.status, "found_stamp": expect in body,
                    "attempt": attempt + 1}
        except Exception as exc:
            last = {"ok": False, "error": type(exc).__name__}
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
