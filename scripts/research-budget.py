#!/usr/bin/env python3
"""Budget gate, usage accounting and weekly digest for the research routine.

Three jobs, one script, no model calls of its own:

* **Gate** (`--gate`) - attached to a research cron job as its pre-check script. It decides
  whether the model should be woken at all for this tick and, when it is, prints a compact
  resume block so the session starts from saved state instead of re-deriving it. Emits
  `{"wakeAgent": false}` as its final line to skip the tick.
* **Status** (`--status` / `--json`) - measured usage for the current period.
* **Digest** (`--digest`) - the weekly Telegram digest: progress, usage, remaining allowance,
  decisions needed.

What is measured, and what is not: every figure here comes from Hermes's own records
(`state.db:session_model_usage`, `cron/usage_audit.jsonl`, `cron/executions.db`). Hermes records
these as **estimates** and no provider-reported actual exists, so the allowance is a budget
guard, not a billing statement. Nothing here can see the portal's subscription quota.

**Fail closed.** With no allowance configured the gate refuses to wake the model. An
unconfigured budget is not an unlimited budget.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME") or Path.home())
DEFAULT_HOME = HOME if (HOME / "cron" / "jobs.json").exists() else Path("/opt/data")
STATE_DB = Path(os.environ.get("SCOUT_STATE_DB") or DEFAULT_HOME / "state.db")
CRON_DIR = Path(os.environ.get("SCOUT_CRON_DIR") or DEFAULT_HOME / "cron")
EXECUTIONS_DB = CRON_DIR / "executions.db"
USAGE_AUDIT = CRON_DIR / "usage_audit.jsonl"
LOCK_PATH = Path(os.environ.get("SCOUT_BUDGET_LOCK") or DEFAULT_HOME / "dataset-factory"
                 / ".factory" / "research-session.lock")

# Interactive platforms are reported for context but never enforced against the research
# allowance: they are the operator's own conversation, not the routine's spend.
INTERACTIVE_SOURCES = ("telegram", "tui", "desktop", "cli", "api_server")
# Auxiliary work inside a session: approval classification, title generation, compression,
# summarisation. Measured separately because it is easy to overlook and never discretionary.
AUXILIARY_TASKS = ("approval", "title_generation", "compression", "summarization", "summarise",
                   "memory", "curation")

DEFAULTS = {
    "allowance_usd": None,
    "period": {"kind": "monthly", "reset_day": 1},
    "stop_fraction": 0.95,
    "warn_fraction": 0.80,
    "sessions_per_week": 3,
    "session_max_minutes": 45,
    "session_token_cap": 600000,
    "catch_up_window_minutes": 120,
    "research_job_ids": [],
    "notes": "",
}


def now_utc():
    return datetime.now(timezone.utc)


def load_config(path):
    config = dict(DEFAULTS)
    path = Path(path)
    if not path.is_file():
        return config, None
    try:
        loaded = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return config, f"{path} is not valid JSON: {exc}"
    for key, value in loaded.items():
        if key == "period" and isinstance(value, dict):
            config["period"] = {**DEFAULTS["period"], **value}
        else:
            config[key] = value
    return config, None


def period_start(config, moment):
    """Start of the allowance period containing `moment`, in UTC."""
    kind = (config.get("period") or {}).get("kind", "monthly")
    if kind == "weekly":
        start = moment - timedelta(days=moment.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    reset_day = int((config.get("period") or {}).get("reset_day", 1))
    reset_day = min(max(reset_day, 1), 28)
    if moment.day >= reset_day:
        return moment.replace(day=reset_day, hour=0, minute=0, second=0, microsecond=0)
    previous = (moment.replace(day=1) - timedelta(days=1))
    return previous.replace(day=reset_day, hour=0, minute=0, second=0, microsecond=0)


def _rows(query, params=(), db=None):
    path = Path(db or STATE_DB)
    if not path.is_file():
        return []
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        return con.execute(query, params).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()


def usage_by_kind(config, start, end):
    """Measured usage in [start, end), split by session kind and by task class."""
    epoch_start, epoch_end = start.timestamp(), end.timestamp()
    rows = _rows(
        "select u.session_id, u.task, u.api_call_count, u.input_tokens, u.output_tokens, "
        "u.estimated_cost_usd, u.cost_status, s.source "
        "from session_model_usage u left join sessions s on s.id = u.session_id "
        "where u.last_seen >= ? and u.first_seen < ?",
        (epoch_start, epoch_end),
    )
    buckets = {}
    research_ids = [str(j) for j in (config.get("research_job_ids") or [])]
    for session_id, task, calls, in_tok, out_tok, cost, cost_status, source in rows:
        task = (task or "").strip()
        session_id = session_id or ""
        source = (source or "").strip()
        if task.lower() in AUXILIARY_TASKS:
            kind = "auxiliary"
        elif any(session_id.startswith(f"cron_{job_id}_") for job_id in research_ids):
            kind = "research"
        elif session_id.startswith("cron_"):
            kind = "scheduled-other"
        elif source in INTERACTIVE_SOURCES:
            kind = "interactive"
        else:
            kind = "unclassified"
        bucket = buckets.setdefault(
            kind, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                   "cost_status": set()}
        )
        bucket["calls"] += calls or 0
        bucket["input_tokens"] += in_tok or 0
        bucket["output_tokens"] += out_tok or 0
        bucket["cost_usd"] += cost or 0.0
        if cost_status:
            bucket["cost_status"].add(str(cost_status))
    for bucket in buckets.values():
        bucket["cost_usd"] = round(bucket["cost_usd"], 6)
        bucket["cost_status"] = sorted(bucket["cost_status"]) or ["unknown"]
    return buckets


def cron_runs(config, since, limit=200):
    """Runs of the research jobs since `since`, from the cron execution ledger."""
    if not EXECUTIONS_DB.is_file():
        return []
    research_ids = [str(j) for j in (config.get("research_job_ids") or [])]
    try:
        con = sqlite3.connect(f"file:{EXECUTIONS_DB}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        rows = con.execute(
            "select id, job_id, status, started_at, finished_at, error, scheduled_instant "
            "from executions order by rowid desc limit ?", (limit,)
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    out = []
    for run_id, job_id, status, started_at, finished_at, error, scheduled in rows:
        if research_ids and str(job_id) not in research_ids:
            continue
        if not research_ids:
            continue
        try:
            started = datetime.fromisoformat(str(started_at))
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if started < since:
            continue
        out.append({"run_id": run_id, "job_id": job_id, "status": status,
                    "started_at": started, "finished_at": finished_at, "error": error,
                    "scheduled_instant": scheduled})
    return out


def running_session(config):
    """A research run currently in flight, from the ledger - the overlap guard."""
    research_ids = [str(j) for j in (config.get("research_job_ids") or [])]
    if not research_ids or not EXECUTIONS_DB.is_file():
        return None
    try:
        con = sqlite3.connect(f"file:{EXECUTIONS_DB}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        rows = con.execute(
            "select job_id, status, claimed_at, started_at from executions "
            "where status in ('running','claimed','handoff') order by rowid desc limit 10"
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    for job_id, status, claimed_at, started_at in rows:
        if str(job_id) in research_ids:
            return {"job_id": job_id, "status": status, "claimed_at": claimed_at,
                    "started_at": started_at}
    return None


def lock_state(config):
    """Liveness/age of the research session lock; stale locks are reported, not honoured."""
    if not LOCK_PATH.is_file():
        return None
    age_seconds = time.time() - LOCK_PATH.stat().st_mtime
    stale_after = int(config.get("session_max_minutes", 45)) * 60 + 300
    try:
        payload = json.loads(LOCK_PATH.read_text() or "{}")
    except json.JSONDecodeError:
        payload = {}
    payload = dict(payload)
    payload["age_seconds"] = round(age_seconds, 1)
    payload["stale"] = age_seconds > stale_after
    return payload


def session_costs(config, since):
    """Per-fire token usage for the research jobs since `since`, from the cron usage audit.

    Returns a list of {job_id, tokens, over_cap}. The token cap cannot interrupt a session
    that is already running, so it is given a mechanical consequence instead: a session that
    overshoots counts as two against the weekly cap.
    """
    if not USAGE_AUDIT.is_file():
        return []
    research_ids = [str(j) for j in (config.get("research_job_ids") or [])]
    if not research_ids:
        return []
    cap = int(config.get("session_token_cap", 600000))
    out = []
    try:
        lines = USAGE_AUDIT.read_text().splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(entry.get("job_id")) not in research_ids:
            continue
        try:
            when = datetime.fromisoformat(str(entry.get("ts")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        if when < since:
            continue
        tokens = int(entry.get("total_tokens") or 0)
        out.append({"job_id": entry.get("job_id"), "tokens": tokens,
                    "over_cap": tokens > cap, "fire_id": entry.get("fire_id")})
    return out


def evaluate(config, moment=None, late_minutes=None):
    """Decide whether a research session may run now, with the reasons either way."""
    moment = moment or now_utc()
    start = period_start(config, moment)
    usage = usage_by_kind(config, start, moment)
    research_cost = usage.get("research", {}).get("cost_usd", 0.0)
    allowance = config.get("allowance_usd")
    reasons = []

    if not allowance:
        reasons.append("no allowance configured (allowance_usd is null) - refusing to wake "
                       "the model until the operator sets one")
    else:
        used_fraction = research_cost / float(allowance)
        if used_fraction >= float(config.get("stop_fraction", 0.95)):
            reasons.append(
                f"research spend {research_cost:.4f} USD is {used_fraction:.1%} of the "
                f"{allowance} USD period allowance (stop at "
                f"{float(config.get('stop_fraction', 0.95)):.0%})"
            )

    running = running_session(config)
    if running:
        reasons.append(f"research job {running['job_id']} is already {running['status']}")
    lock = lock_state(config)
    if lock and not lock.get("stale"):
        reasons.append(
            f"lock held for {lock['age_seconds']:.0f}s by {lock.get('session_id', 'unknown')}"
        )

    week_start = moment - timedelta(days=7)
    weeks_runs = cron_runs(config, week_start)
    completed = [run for run in weeks_runs if str(run["status"]) in ("completed", "failed")]
    cap = int(config.get("sessions_per_week", 3))
    costs = session_costs(config, week_start)
    over_cap = [entry for entry in costs if entry["over_cap"]]
    weighted = len(completed) + len(over_cap)
    if weighted >= cap:
        detail = f"{len(completed)} research session(s) already ran in the last 7 days"
        if over_cap:
            detail += (f", {len(over_cap)} of which overshot the "
                       f"{config.get('session_token_cap'):,}-token cap and count double")
        reasons.append(f"{detail} (cap {cap})")

    window = int(config.get("catch_up_window_minutes", 120))
    if late_minutes is not None and late_minutes > window:
        reasons.append(
            f"fired {late_minutes:.0f} min late, beyond the {window} min window - a missed "
            "slot is skipped rather than caught up"
        )

    return {
        "moment": moment.isoformat(),
        "period_start": start.isoformat(),
        "allowance_usd": allowance,
        "research_cost_usd": round(research_cost, 6),
        "usage": usage,
        "runs_last_7_days": len(completed),
        "runs_weighted_last_7_days": weighted,
        "sessions_over_token_cap": len(over_cap),
        "session_cap_per_week": cap,
        "allowed": not reasons,
        "reasons": reasons,
    }


def resume_block(config, decision):
    """Compact saved state for the session that is about to run. Cheap to build, cheap to read."""
    lines = ["RESEARCH SESSION CONTEXT (generated by research-budget.py, not by a model)"]
    allowance = decision["allowance_usd"]
    lines.append(
        f"allowance: {allowance} USD per {config.get('period', {}).get('kind', 'monthly')} "
        f"period starting {decision['period_start'][:10]}"
    )
    lines.append(
        f"research spend so far this period: {decision['research_cost_usd']:.4f} USD "
        f"(estimated by Hermes; no provider-reported actual exists)"
    )
    if allowance:
        remaining = float(allowance) - decision["research_cost_usd"]
        lines.append(f"remaining: {remaining:.4f} USD")
    for kind, bucket in sorted(decision["usage"].items()):
        lines.append(
            f"usage[{kind}]: {bucket['cost_usd']:.4f} USD, {bucket['calls']} calls, "
            f"{bucket['input_tokens']:,} in / {bucket['output_tokens']:,} out"
        )
    lines.append(f"sessions in the last 7 days: {decision['runs_last_7_days']}"
                 f"/{decision['session_cap_per_week']}")
    lines.append(
        f"session limits: <= {config.get('session_max_minutes')} min, "
        f"<= {config.get('session_token_cap'):,} tokens; stop cleanly at either"
    )
    return "\n".join(lines)


def digest(config, moment=None):
    moment = moment or now_utc()
    decision = evaluate(config, moment)
    start = period_start(config, moment)
    runs = cron_runs(config, start)
    lines = [f"Scout research digest - {moment.date().isoformat()}", ""]
    allowance = decision["allowance_usd"]
    if allowance:
        used = decision["research_cost_usd"]
        lines.append(
            f"Research allowance: {used:.4f} / {allowance} USD used "
            f"({used / float(allowance):.1%}), {float(allowance) - used:.4f} USD remaining "
            f"(period from {start.date().isoformat()})"
        )
    else:
        lines.append("Research allowance: NOT ESTABLISHED - recurring model work is held "
                     "(fail-closed). Decision needed from the operator.")
    lines.append(f"Sessions this period: {len(runs)} (cap {decision['session_cap_per_week']}/week)")
    if decision.get("sessions_over_token_cap"):
        lines.append(
            f"Token cap: {decision['sessions_over_token_cap']} session(s) overshot the "
            f"{config.get('session_token_cap'):,}-token cap and counted double"
        )
    failed = [run for run in runs if str(run["status"]) == "failed" or run["error"]]
    if failed:
        lines.append(f"Failed sessions: {len(failed)} - latest {failed[0]['run_id'][:12]} "
                     f"({failed[0]['error'] or 'no error text'})")
    for kind, bucket in sorted(decision["usage"].items()):
        lines.append(f"  {kind}: {bucket['cost_usd']:.4f} USD, {bucket['calls']} calls")
    lines.append("")
    lines.append("Estimates only: Hermes records these as estimated; it cannot see the "
                 "portal's subscription quota or reset period.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_HOME / "dataset-factory" / "config"
                                                / "research-budget.json"))
    parser.add_argument("--gate", action="store_true", help="cron pre-check: allow or skip")
    parser.add_argument("--status", action="store_true", help="measured usage summary")
    parser.add_argument("--digest", action="store_true", help="weekly digest text")
    parser.add_argument("--json", action="store_true", help="machine-readable decisions")
    parser.add_argument("--late-minutes", type=float, default=None,
                        help="how late this tick fired, for the catch-up window")
    parser.add_argument("--write-lock", action="store_true",
                        help="refresh the session lock (gate mode does this when allowing)")
    args = parser.parse_args(argv)

    config, error = load_config(args.config)
    if error:
        print(error, file=sys.stderr)
    decision = evaluate(config, late_minutes=args.late_minutes)

    if args.json:
        print(json.dumps({"decision": decision, "config": config}, indent=2, default=str))
        return 0

    if args.digest:
        print(digest(config))
        return 0

    if args.gate:
        print(resume_block(config, decision))
        if decision["allowed"]:
            if args.write_lock:
                LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
                LOCK_PATH.write_text(json.dumps(
                    {"session_id": "cron", "written_at": now_utc().isoformat()}))
            print(json.dumps({"researchBudget": {
                "allowed": True,
                "allowance_usd": decision["allowance_usd"],
                "research_cost_usd": decision["research_cost_usd"],
            }}))
            return 0
        print("SKIPPING THIS TICK - " + "; ".join(decision["reasons"]))
        print(json.dumps({"wakeAgent": False, "reason": "; ".join(decision["reasons"])}))
        return 0

    # default: status
    print(resume_block(config, decision))
    if decision["reasons"]:
        print("HELD: " + "; ".join(decision["reasons"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
