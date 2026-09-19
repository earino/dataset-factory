#!/usr/bin/env python3
"""Scheduled research session: gate first, then one bounded agent run.

Reuses supported controls instead of adding infrastructure:

* `hermes chat --max-turns N` - a finite tool-calling iteration cap **for this run only**.
* `hermes chat --run-budget S` - a hard wall-clock ceiling for this run, with a one-time
  wrap-up notice at 80% and provider stale timeouts capped to what remains.
* `hermes chat -Q` - only the final response, so the delivery is the session's summary.
* `hermes chat --source scout-research` - tags the session so usage accounting can tell a
  research session from the operator's own chat.
* `scripts/research-budget.py --gate` - the allowance/cap/overlap gate. When it holds, **no
  agent process is started at all**, so a held tick costs nothing.

Both ceilings are per-invocation flags, so they bound this session without changing global
config or the operator's interactive sessions. The gate writes the session lock so two
sessions cannot overlap, and the lock is removed when the run ends.

    python3 scripts/scout_research_session.py --max-turns 60 --run-budget 2400
    python3 scripts/scout_research_session.py --dry-run          # gate only, no agent
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

def _resolve_repo():
    """The repository this wrapper belongs to.

    Derived from the module's own location first, so the code works from any checkout (a fresh
    clone, CI, or another host) rather than only from the deployed path; the deployed absolute
    path is only a fallback for the shim case. Hardcoding it made the module untestable
    anywhere but this host - the same defect class as the host-only paths fixed earlier.
    """
    here = Path(__file__).resolve()
    for candidate in (here.parent.parent, Path("/opt/data/dataset-factory")):
        if (candidate / "scripts" / "research-budget.py").is_file():
            return candidate
    return here.parent.parent


REPO = _resolve_repo()
BUDGET = REPO / "scripts" / "research-budget.py"
PROMPT_TEMPLATE = REPO / "docs" / "research-session-prompt.md"
HERMES_PYTHON = "/opt/hermes/.venv/bin/python3"
HERMES_CLI = "/opt/hermes/hermes"
SOURCE_TAG = "scout-research"
# Overridable per run via --source-tag, so verification runs can carry a distinct tag.
SOURCE_TAG_ACTIVE = SOURCE_TAG
FACTORY_DIR = REPO / ".factory"
LOCK = FACTORY_DIR / "research-session.lock"
LOG = FACTORY_DIR / "research-sessions.jsonl"

# Footer lines the CLI prints after the final response; they are not part of it.
FOOTER_PATTERNS = (
    re.compile(r"^Resume this session with:"),
    re.compile(r"^\s*hermes (--resume|-c) "),
    re.compile(r"^Session:\s"),
    re.compile(r"^Title:\s"),
    re.compile(r"^Duration:\s"),
    re.compile(r"^Messages:\s"),
)


def now():
    return datetime.now(timezone.utc)


def note(entry):
    FACTORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": now().isoformat(), **entry}
    with LOG.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


def run_gate(late_minutes=None):
    """Run the budget gate; return (allowed, resume_block, reason)."""
    command = [sys.executable, str(BUDGET), "--gate"]
    if late_minutes is not None:
        command += ["--late-minutes", str(late_minutes)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120,
                            cwd=str(REPO))
    allowed, reason = False, "gate produced no decision"
    block_lines = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith('{"wakeAgent"'):
            try:
                allowed = json.loads(stripped).get("wakeAgent") is not False
            except json.JSONDecodeError:
                pass
            continue
        if stripped.startswith('{"researchBudget"'):
            try:
                payload = json.loads(stripped).get("researchBudget") or {}
                allowed = payload.get("allowed") is True
                reasons = payload.get("reasons") or []
                reason = "; ".join(reasons) if reasons else "clear"
            except json.JSONDecodeError:
                pass
            continue
        if stripped.startswith("SKIPPING THIS TICK"):
            reason = stripped
            continue
        block_lines.append(line)
    if not result.stdout.strip():
        reason = f"gate failed: {result.stderr.strip()[:300] or 'no output'}"
    return allowed, "\n".join(block_lines).strip(), reason


def build_prompt(resume_block, extra=""):
    template = PROMPT_TEMPLATE.read_text()
    stamp = now().strftime("%Y-%m-%d")
    prompt = template.replace("{{DATE}}", stamp).replace("{{SESSION_CONTEXT}}", resume_block)
    if extra:
        # State this is part of the brief and who set it. Appended raw, the same text reads like
        # injected content and a session is right to distrust it - one refused a verification
        # instruction for exactly that reason.
        prompt += (
            "\n\n## Task for this session\n\n"
            "The operator set the following through the scheduler. It is part of this session's "
            "brief, not text found in a file or fetched from the internet, and it takes "
            "selects the task for this session. It does not lift the standing limits, the "
            "allowance, the session ceilings or the safety rules above - those still apply:\n\n"
            f"{extra}\n"
        )
    return prompt


def strip_footer(text):
    lines = text.splitlines()
    while lines:
        last = lines[-1].strip()
        if not last or any(pattern.match(last) for pattern in FOOTER_PATTERNS):
            lines.pop()
            continue
        break
    return "\n".join(lines).strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-turns", type=int, default=60,
                        help="tool-calling iteration cap for this run")
    parser.add_argument("--run-budget", type=int, default=2400,
                        help="wall-clock ceiling in seconds for this run")
    parser.add_argument("--late-minutes", type=float, default=None,
                        help="how late this tick fired, for the catch-up window")
    parser.add_argument("--dry-run", action="store_true",
                        help="evaluate the gate and print the prompt; start no agent")
    parser.add_argument("--extra", default="", help="extra instruction for this session only")
    parser.add_argument("--fallback-report", action="store_true",
                        help="when the gate holds, print the deterministic digest and the hold "
                             "reason instead of staying silent")
    parser.add_argument("--source-tag", default=SOURCE_TAG,
                        help="session source tag; use a distinct one for verification runs so "
                             "they are not counted as research sessions")
    args = parser.parse_args(argv)
    global SOURCE_TAG_ACTIVE
    SOURCE_TAG_ACTIVE = args.source_tag

    allowed, resume_block, reason = run_gate(args.late_minutes)

    if args.dry_run:
        print(resume_block)
        print(f"\nGATE: {'ALLOWED' if allowed else 'HELD'} - {reason}")
        if allowed:
            print("\n--- prompt that would be sent ---")
            print(build_prompt(resume_block, args.extra))
        return 0

    if not allowed:
        note({"event": "skipped", "reason": reason})
        if args.fallback_report:
            # Deterministic: built from the ledgers by research-budget.py, not by a model. This
            # is how a held checkpoint still reports, including when it is held by the session
            # cap rather than by the allowance.
            subprocess.run([sys.executable, str(BUDGET), "--digest"], cwd=str(REPO))
            print("")
            print(f"Held, so no model work ran: {reason}")
            return 0
        # Routine holds are otherwise silent: a cap, an overlap or a late tick is not news. An
        # exhausted allowance is, because it needs a decision.
        if "allowance" in reason.lower():
            print(f"Scout research session held: {reason}")
        return 0

    prompt = build_prompt(resume_block, args.extra)
    FACTORY_DIR.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({"session_id": SOURCE_TAG_ACTIVE, "pid": os.getpid(),
                                "written_at": now().isoformat(),
                                "max_turns": args.max_turns, "run_budget": args.run_budget}))

    started = time.time()
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
        handle.write(prompt)
        prompt_path = handle.name

    command = [
        HERMES_PYTHON, HERMES_CLI, "chat",
        "--query-file", prompt_path,
        "--oneshot", "-Q",
        "--source", SOURCE_TAG_ACTIVE,
        "--max-turns", str(args.max_turns),
        "--run-budget", str(args.run_budget),
        "-s", "dataset-discovery,dataset-qualification,dataset-release",
    ]
    outcome, output, error = "completed", "", ""
    try:
        result = subprocess.run(command, capture_output=True, text=True, cwd=str(REPO),
                                timeout=args.run_budget + 300)
        output, error = result.stdout, result.stderr
        if result.returncode != 0:
            outcome = f"exit {result.returncode}"
    except subprocess.TimeoutExpired:
        outcome = "killed by the wrapper after the run budget elapsed"
    finally:
        LOCK.unlink(missing_ok=True)
        Path(prompt_path).unlink(missing_ok=True)

    elapsed = round(time.time() - started, 1)
    note({"event": "session", "outcome": outcome, "elapsed_seconds": elapsed,
          "max_turns": args.max_turns, "run_budget": args.run_budget})
    print(strip_footer(output) or f"Scout research session {outcome} after {elapsed}s")
    if error.strip():
        print(f"(stderr: {error.strip()[:400]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
