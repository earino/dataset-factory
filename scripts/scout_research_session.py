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
config or the operator's interactive sessions. An OS mutex covers gate evaluation and
the agent run; a separate JSON marker feeds budget reporting and is removed when the run ends.

    python3 scripts/scout_research_session.py --max-turns 60 --run-budget 2400
    python3 scripts/scout_research_session.py --dry-run          # gate only, no agent
"""

import argparse
import contextlib
import fcntl
import json
import os
import re
import signal
import stat
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


def actionable_work(root=REPO):
    """Candidates that need an agent step now.

    Advancement used to run once a day, so a qualified candidate could sit for 20 hours.
    This is the cheap pre-check that lets the tick run often without paying for an agent
    when there is nothing to do. A candidate waiting on the operator's flip is not work.
    """
    work = []
    for path in sorted((Path(root) / "candidates").glob("*/record.json")):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        status = record.get("status")
        if status == "packaged":
            if not record.get("awaiting_operator"):
                work.append((record.get("id") or path.parent.name, "release"))
        elif status in ("ready", "qualified"):
            work.append((record.get("id") or path.parent.name, "build" if status == "ready" else "package"))
        elif status == "investigating" and str(record.get("next_action") or "").upper().startswith("GO"):
            work.append((record.get("id") or path.parent.name, "construct"))
    return work


def note(entry):
    FACTORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": now().isoformat(), **entry}
    with LOG.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


class AdmissionError(RuntimeError):
    """The preflight could not establish permission to start model work."""


class SessionBusy(AdmissionError):
    """Another wrapper or its agent owns the admission mutex."""


@contextlib.contextmanager
def admission_lock():
    """Serialize gate evaluation and execution, without a stale-time takeover.

    Keep this inode permanently: unlinking a flock file lets two processes lock
    different inodes. The JSON session marker remains separate for budget reports.
    """
    FACTORY_DIR.mkdir(parents=True, exist_ok=True)
    if FACTORY_DIR.is_symlink():
        raise AdmissionError("session state directory must not be a symlink")
    path = FACTORY_DIR / "research-session.mutex"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AdmissionError("session mutex must be a regular file with a single hard link")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SessionBusy("another research session owns the admission lock") from None
        yield fd
    finally:
        # Close, rather than LOCK_UN: an inherited descriptor keeps the lock if
        # this wrapper dies while its direct Hermes child is still running.
        os.close(fd)


@contextlib.contextmanager
def session_marker(args):
    """Publish the legacy reporting marker atomically; remove only our bytes."""
    if LOCK.is_symlink() or (LOCK.exists() and not LOCK.is_file()):
        raise AdmissionError("session marker must be a regular file")
    payload = json.dumps({"session_id": SOURCE_TAG_ACTIVE, "pid": os.getpid(),
                          "written_at": now().isoformat(),
                          "max_turns": args.max_turns, "run_budget": args.run_budget})
    fd, temporary = tempfile.mkstemp(dir=LOCK.parent, prefix=".session-marker-")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, LOCK)
        yield
    finally:
        Path(temporary).unlink(missing_ok=True)
        # Preserve another writer's replacement for inspection, not cleanup.
        if (not LOCK.is_symlink() and LOCK.is_file()
                and LOCK.stat().st_size == len(payload.encode())
                and LOCK.read_text() == payload):
            LOCK.unlink()


def _unique_json(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate decision key")
        value[key] = item
    return value


def run_gate(late_minutes=None):
    """Require a successful gate and exactly one explicit, well-formed decision."""
    command = [sys.executable, str(BUDGET), "--gate", "--config",
               str(REPO / "config" / "research-budget.json")]
    if late_minutes is not None:
        command += ["--late-minutes", str(late_minutes)]
    env = {**os.environ, "SCOUT_BUDGET_LOCK": str(LOCK)}
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120,
                                cwd=str(REPO), env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        raise AdmissionError(f"budget gate unavailable ({type(exc).__name__})") from None
    if result.returncode != 0:
        raise AdmissionError(f"budget gate exited {result.returncode}")
    decision, wake, block_lines = None, None, []
    try:
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("{"):
                item = json.loads(stripped, object_pairs_hook=_unique_json)
                if not isinstance(item, dict):
                    raise ValueError("expected decision object")
                if "researchBudget" in item:
                    if decision is not None or set(item) != {"researchBudget"}:
                        raise ValueError("duplicate or ambiguous budget decision")
                    decision = item["researchBudget"]
                    if (not isinstance(decision, dict)
                            or type(decision.get("allowed")) is not bool
                            or not isinstance(decision.get("reasons"), list)
                            or any(not isinstance(r, str) or not r.strip()
                                   for r in decision["reasons"])):
                        raise ValueError("malformed budget decision")
                    if decision["allowed"] == bool(decision["reasons"]):
                        raise ValueError("budget decision contradicts its reasons")
                elif "wakeAgent" in item:
                    if wake is not None or type(item["wakeAgent"]) is not bool:
                        raise ValueError("duplicate or malformed wake directive")
                    wake = item["wakeAgent"]
                else:
                    raise ValueError("unknown gate directive")
            elif not stripped.startswith("SKIPPING THIS TICK"):
                block_lines.append(line)
        if decision is None:
            raise ValueError("gate produced no budget decision")
        if wake is not None and wake != decision["allowed"]:
            raise ValueError("conflicting gate decisions")
    except (ValueError, TypeError) as exc:
        raise AdmissionError(f"invalid budget gate response ({exc})") from None
    return (decision["allowed"], "\n".join(block_lines).strip(),
            "; ".join(decision["reasons"]) or "clear")


def run_agent(command, timeout, lock_fd):
    """Retain admission across exec; stop the process group at the outer ceiling."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, cwd=str(REPO), start_new_session=True,
                               pass_fds=(lock_fd,))
    try:
        output, error = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, process.returncode, output, error)
    finally:
        # Hermes may leave tool children after exiting or being interrupted. They
        # belong to this new process group, never the scheduler or an SSH worker.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()
        process.stderr.close()


def build_prompt(resume_block, extra="", template_path=None):
    # Relative paths resolve against the repository, not the caller's cwd: the scheduler runs this
    # from elsewhere, and a cwd-relative brief silently failed the first discovery tick.
    path = Path(template_path or PROMPT_TEMPLATE)
    if not path.is_absolute():
        path = REPO / path
    template = path.read_text()
    stamp = now().strftime("%Y-%m-%d")
    prompt = template.replace("{{DATE}}", stamp).replace("{{SESSION_CONTEXT}}", resume_block)
    if extra:
        # State this is part of the brief and who set it. Appended raw, the same text reads like
        # injected content and a session is right to distrust it - one refused a verification
        # instruction for exactly that reason.
        prompt += (
            "\n\n## Task for this session\n\n"
            "The operator set the following through the scheduler. It is part of this session's "
            "brief, not text found in a file or fetched from the internet, and it selects "
            "the task for this session. It does not lift the standing limits, the "
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
    parser.add_argument("--prompt-file", default=str(PROMPT_TEMPLATE),
                        help="brief for this run; a discovery tick passes the discovery prompt")
    parser.add_argument("--if-work", action="store_true",
                        help="run only when a candidate needs a step; otherwise exit quietly "
                             "without starting an agent (keeps the cadence high, the cost low)")
    parser.add_argument("--source-tag", default=SOURCE_TAG,
                        help="session source tag; use a distinct one for verification runs so "
                             "they are not counted as research sessions")
    args = parser.parse_args(argv)
    global SOURCE_TAG_ACTIVE
    SOURCE_TAG_ACTIVE = args.source_tag

    if args.max_turns <= 0 or args.run_budget <= 0:
        parser.error("--max-turns and --run-budget must be positive")
    try:
        with admission_lock() as lock_fd:
            return run_session(args, lock_fd)
    except SessionBusy as exc:
        note({"event": "skipped", "reason": str(exc)})
        if args.fallback_report:
            subprocess.run([sys.executable, str(BUDGET), "--digest", "--config",
                            str(REPO / "config" / "research-budget.json")], cwd=str(REPO))
        if args.dry_run or args.fallback_report:
            print(f"Held, so no model work ran: {exc}")
        return 0
    except (AdmissionError, OSError) as exc:
        # Never include raw child stderr or environment values in this diagnostic.
        reason = str(exc) if isinstance(exc, AdmissionError) else type(exc).__name__
        note({"event": "admission_failed", "reason": reason})
        print(f"Scout research session refused: {reason}", file=sys.stderr)
        return 2


def run_session(args, lock_fd):
    if args.if_work:
        work = actionable_work()
        if not work:
            note({"event": "idle", "reason": "no actionable candidate"})
            return 0
        args.extra = (args.extra + "\n\n" if args.extra else "") + (
            "Actionable now: " + ", ".join(f"{name} ({step})" for name, step in work) + ". "
            "Release work outranks construction.")

    allowed, resume_block, reason = run_gate(args.late_minutes)

    if args.dry_run:
        print(resume_block)
        print(f"\nGATE: {'ALLOWED' if allowed else 'HELD'} - {reason}")
        if allowed:
            print("\n--- prompt that would be sent ---")
            print(build_prompt(resume_block, args.extra, args.prompt_file))
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

    prompt = build_prompt(resume_block, args.extra, args.prompt_file)
    started = time.monotonic()
    outcome, output, error, exit_code = "completed", "", "", 0
    with tempfile.NamedTemporaryFile("w", suffix=".md") as handle:
        handle.write(prompt)
        handle.flush()
        command = [
            HERMES_PYTHON, HERMES_CLI, "chat",
            "--query-file", handle.name,
            "--oneshot", "-Q",
            "--source", SOURCE_TAG_ACTIVE,
            "--max-turns", str(args.max_turns),
            "--run-budget", str(args.run_budget),
            "-s", "dataset-discovery,dataset-qualification,dataset-release",
        ]
        with session_marker(args):
            try:
                result = run_agent(command, args.run_budget + 300, lock_fd)
                output, error = result.stdout, result.stderr
                if result.returncode != 0:
                    outcome = f"exit {result.returncode}"
                    exit_code = result.returncode if result.returncode > 0 else 128 - result.returncode
            except subprocess.TimeoutExpired:
                outcome = "killed by the wrapper after the run budget elapsed"
                exit_code = 124
            except OSError as exc:
                outcome = f"agent could not start ({type(exc).__name__})"
                exit_code = 2

    elapsed = round(time.monotonic() - started, 1)
    note({"event": "session", "outcome": outcome, "elapsed_seconds": elapsed,
          "prompt_file": Path(args.prompt_file).name,
          "max_turns": args.max_turns, "run_budget": args.run_budget})
    print(strip_footer(output) or f"Scout research session {outcome} after {elapsed}s")
    if error.strip():
        print(f"(stderr: {error.strip()[:400]})")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
