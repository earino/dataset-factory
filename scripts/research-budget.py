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
import subprocess
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
    "reserve_usd": 0.40,
    "sessions_per_week": 3,
    "session_max_minutes": 40,
    "session_max_turns": 60,
    "session_token_cap": 600000,
    "catch_up_window_minutes": 120,
    "research_job_ids": [],
    "research_sources": ["scout-research"],
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
    research_sources = [str(s) for s in (config.get("research_sources") or [])]
    excluded = excluded_set(config)
    for session_id, task, calls, in_tok, out_tok, cost, cost_status, source in rows:
        if session_id in excluded:
            continue
        task = (task or "").strip()
        session_id = session_id or ""
        source = (source or "").strip()
        # Session membership decides first: auxiliary calls made *inside* a research session
        # (approval classification, compression, titles) are part of that session's spend and
        # are charged to it. Only outside a research session do they stand alone.
        in_research = (
            any(session_id.startswith(f"cron_{job_id}_") for job_id in research_ids)
            # A session started by the research wrapper via `hermes chat --source`, i.e. a
            # scheduled research run rather than the operator's own chat.
            or source in research_sources
        )
        if in_research:
            kind = "research"
        elif task.lower() in AUXILIARY_TASKS:
            kind = "auxiliary"
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


def _process_alive(pid):
    if not pid:
        return None
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError, TypeError):
        return False
    return True


def lock_state(config):
    """Liveness/age of the research session lock; stale locks are reported, not honoured.

    The lock is the overlap signal: the wrapper writes it once it is allowed to run and removes
    it when the session ends. A lock whose owning process is gone is stale immediately, so a
    crashed session does not block the next tick for the whole timeout.
    """
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
    owner_alive = _process_alive(payload.get("pid"))
    payload["owner_alive"] = owner_alive
    payload["stale"] = age_seconds > stale_after or owner_alive is False
    return payload


def excluded_set(config):
    """Session ids explicitly excluded from research accounting.

    Used for sessions that were verification of the routine itself rather than research inside
    it. Recorded by id in config so the exclusion is auditable and cannot silently grow.
    """
    return {str(s) for s in (config.get("excluded_sessions") or [])}


def research_sessions(config, since):
    """Research sessions started since `since`, measured from the session ledger.

    One wrapper run produces exactly one session tagged with a research source, so this is the
    real unit of the weekly cap - counting scheduler fires alone would miss a session started by
    hand and would count a held tick as if it had run.
    """
    research_sources = [str(s) for s in (config.get("research_sources") or [])]
    if not research_sources:
        return []
    excluded = excluded_set(config)
    placeholders = ",".join("?" for _ in research_sources)
    rows = _rows(
        f"select s.id, s.started_at, coalesce(u.tokens, 0), coalesce(u.cost, 0.0) from sessions s "
        f"left join (select session_id, sum(input_tokens + output_tokens) as tokens, "
        f"sum(estimated_cost_usd) as cost from session_model_usage group by session_id) u "
        f"on u.session_id = s.id "
        f"where s.source in ({placeholders}) and s.started_at >= ?",
        tuple(research_sources) + (since.timestamp(),),
    )
    cap = int(config.get("session_token_cap", 600000))
    out = []
    for session_id, started_at, tokens, cost in rows:
        if session_id in excluded:
            continue
        # started_at is stored as an epoch in the ledger; tolerate an ISO string too.
        try:
            started = datetime.fromtimestamp(float(started_at), tz=timezone.utc)
        except (TypeError, ValueError):
            try:
                started = datetime.fromisoformat(str(started_at))
            except ValueError:
                started = since
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
        out.append({"session_id": session_id, "started_at": started.isoformat(),
                    "tokens": int(tokens or 0), "cost_usd": round(cost or 0.0, 6),
                    "over_cap": int(tokens or 0) > cap})
    return out


def evaluate(config, moment=None, late_minutes=None):
    """Decide whether a research session may run now, with the reasons either way."""
    moment = moment or now_utc()
    start = period_start(config, moment)
    usage = usage_by_kind(config, start, moment)
    research_cost = usage.get("research", {}).get("cost_usd", 0.0)
    allowance = config.get("allowance_usd")
    reserve = float(config.get("reserve_usd") or 0)
    stop_fraction = float(config.get("stop_fraction", 0.95))
    reasons = []

    if not allowance:
        reasons.append("no allowance configured (allowance_usd is null) - refusing to wake "
                       "the model until the operator sets one")
    else:
        used_fraction = research_cost / float(allowance)
        if used_fraction >= stop_fraction:
            reasons.append(
                f"research spend {research_cost:.4f} USD is {used_fraction:.1%} of the "
                f"{allowance} USD period allowance (stop at {stop_fraction:.0%})"
            )
        elif research_cost + reserve > float(allowance):
            # The reserve is what keeps the *next* session affordable. Starting one that eats
            # into it would leave a session that cannot be paid for, so it is held instead.
            reasons.append(
                f"holding {reserve:.2f} USD in reserve would need "
                f"{research_cost + reserve:.4f} USD of the {allowance} USD allowance - not "
                "enough left for the next session"
            )

    # Overlap is decided by the session lock, never by the scheduler's execution ledger: the
    # ledger carries a 'running' row for this very job from the moment the scheduler fires it,
    # so consulting it held every fire of the job against itself.
    lock = lock_state(config)
    if lock and not lock.get("stale"):
        reasons.append(
            f"lock held for {lock['age_seconds']:.0f}s by {lock.get('session_id', 'unknown')}"
        )

    week_start = moment - timedelta(days=7)
    weeks_runs = cron_runs(config, week_start)
    completed = [run for run in weeks_runs if str(run["status"]) in ("completed", "failed")]
    cap = int(config.get("sessions_per_week", 3))
    sessions = research_sessions(config, week_start)
    over_cap = [entry for entry in sessions if entry["over_cap"]]
    used = len(sessions)
    weighted = used + len(over_cap)
    if weighted >= cap:
        detail = f"{used} research session(s) already ran in the last 7 days"
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
        "runs_last_7_days": used,
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
        reserve = float(config.get("reserve_usd") or 0)
        lines.append(f"remaining: {remaining:.4f} USD (reserve for the next session: "
                     f"{reserve:.2f} USD)")
    for kind, bucket in sorted(decision["usage"].items()):
        lines.append(
            f"usage[{kind}]: {bucket['cost_usd']:.4f} USD, {bucket['calls']} calls, "
            f"{bucket['input_tokens']:,} in / {bucket['output_tokens']:,} out"
        )
    lines.append(f"sessions in the last 7 days: {decision['runs_last_7_days']}"
                 f"/{decision['session_cap_per_week']}")
    lines.append(
        f"session limits: <= {config.get('session_max_turns')} tool-calling iterations and "
        f"<= {config.get('session_max_minutes')} min wall clock, ENFORCED by the runtime for "
        "this session (hermes chat --max-turns/--run-budget)"
    )
    lines.append(
        f"session token budget: <= {config.get('session_token_cap'):,} estimated tokens is "
        "ADVISORY - the runtime has no token control; stop well inside it"
    )
    return "\n".join(lines)


def completed_work(root, since, limit=8):
    """Completed work since `since`: repository commits, and the candidate queue's state.

    Deterministic and cheap - read from git and the candidate records rather than described by
    a model, so the digest reports what actually landed.
    """
    commits = []
    try:
        result = run_git(["log", f"--since={since.isoformat()}", "--pretty=%h %s"],
                         root, timeout=60)
        commits = [line.strip() for line in result.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        pass
    queue = []
    candidates = Path(root) / "candidates"
    if candidates.is_dir():
        for path in sorted(candidates.glob("*/record.json")):
            try:
                record = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            queue.append({
                "id": record.get("id") or path.parent.name,
                "status": record.get("status") or "unknown",
                "next_action": record.get("next_action") or "",
            })
    return commits[:limit], len(commits), queue


def run_git(args, root, timeout=60):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                            timeout=timeout)
    return result.stdout if result.returncode == 0 else ""


def digest(config, moment=None, root=None):
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
        reserve = float(config.get("reserve_usd") or 0)
        if reserve:
            lines.append(f"  Reserve held for the next session: {reserve:.2f} USD")
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

    if root:
        commits, total_commits, queue = completed_work(root, moment - timedelta(days=7))
        lines.append("")
        lines.append(f"Completed work in the last 7 days: {total_commits} commit(s)")
        for commit in commits:
            lines.append(f"  {commit[:110]}")
        if queue:
            counts = {}
            for item in queue:
                counts[item["status"]] = counts.get(item["status"], 0) + 1
            summary = ", ".join(f"{count} {status}" for status, count in sorted(counts.items()))
            lines.append(f"Candidate queue: {len(queue)} - {summary}")
            for item in queue:
                if item["status"] in ("investigating",) and not item["next_action"]:
                    lines.append(f"  {item['id']}: no next action recorded - needs a verdict")

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
        print(digest(config, root=Path(args.config).resolve().parents[1]))
        return 0

    if args.gate:
        print(resume_block(config, decision))
        # Always emit the decision, so a caller (the research wrapper) can read it either way.
        print(json.dumps({"researchBudget": {
            "allowed": decision["allowed"],
            "allowance_usd": decision["allowance_usd"],
            "research_cost_usd": decision["research_cost_usd"],
            "reasons": decision["reasons"],
        }}))
        if decision["allowed"]:
            if args.write_lock:
                LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
                LOCK_PATH.write_text(json.dumps(
                    {"session_id": "cron", "written_at": now_utc().isoformat()}))
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
