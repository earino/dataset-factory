"""Bounded judgment/code tasks through the installed Hermes CLI and allowance.

The model returns data. It cannot edit the coordinator, launch workers, publish,
or decide lifecycle transitions. Successful responses are reused after restart.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

from .audit_model_session import wrapper
from .common import FactoryError, read_json, write_json


class BudgetWait(FactoryError):
    pass


class TaskFailure(FactoryError):
    pass


def parse_response(text):
    text = text.strip()
    if text.startswith('Warning: Unknown toolsets: __none__\n'):
        text = text.split('\n', 1)[1].strip()
    if text.startswith('```json\n') and text.endswith('```'):
        text = text[8:-3].strip()
    if len(text.encode()) >= 256 * 1024:
        raise TaskFailure('Model response exceeds compact report limit')
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise TaskFailure('Model response is not JSON') from exc
    if not isinstance(value, dict):
        raise TaskFailure('Model response must be an object')
    return value


def usage(db_path, before):
    """Read actual session accounting; price fields are not actual spend."""
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        created = {r[0] for r in db.execute("SELECT id FROM sessions WHERE source='oneshot'")} - set(before)
        if len(created) != 1:
            raise TaskFailure('Model session identity is ambiguous')
        sid = created.pop()
        rows = db.execute('SELECT model,billing_provider,api_call_count,input_tokens,output_tokens,'
                          'cache_read_tokens,cache_write_tokens FROM session_model_usage WHERE session_id=?',
                          (sid,)).fetchall()
        if not rows:
            raise TaskFailure('Model session has no measured usage')
        fields = ('model', 'provider', 'calls', 'input_tokens', 'output_tokens',
                  'cache_read_tokens', 'cache_write_tokens')
        tools = db.execute("SELECT count(*) FROM messages WHERE session_id=? AND role='tool'", (sid,)).fetchone()[0]
        return {'session_id': sid, 'tasks': [dict(zip(fields, row)) for row in rows],
                'tool_results': tools, 'scope': 'Recorded route and usage; not provider attestation or actual spend'}


class ModelTasks:
    def __init__(self, root, policy, *, hermes_root='/opt/hermes', hermes_home='/opt/data'):
        self.root = Path(root).resolve()
        self.policy = policy
        self.hermes_root = Path(hermes_root)
        self.db = Path(hermes_home) / 'state.db'

    def run(self, task_id, prompt, *, research=False):
        from .common import identifier
        identifier(task_id)
        if len(prompt.encode()) > 64 * 1024:
            raise TaskFailure('Task context exceeds 64 KiB')
        directory = self.root / '.factory' / 'model-tasks' / task_id
        directory.mkdir(parents=True, exist_ok=True)
        response_path = directory / 'response.json'
        if response_path.exists():
            if (directory / 'prompt.txt').read_text() != prompt:
                raise TaskFailure('Task identity was reused for different input')
            return read_json(response_path)
        w = wrapper(self.root)
        try:
            with w.admission_lock() as fd:
                # Holding the inherited lock proves any interrupted child is done.
                # Never silently call again under a paid task identity.
                if (directory / 'attempt.json').exists():
                    raise TaskFailure('Interrupted model task; retry with a new attempt identity')
                allowed, _, reason = w.run_gate()
                if not allowed:
                    raise BudgetWait(reason)
                limits = read_json(self.root / 'config/research-budget.json')
                turns = min(int(self.policy['research_turns'] if research else self.policy['code_turns']),
                            int(limits['session_max_turns']))
                seconds = min(int(self.policy['task_seconds']), int(limits['session_max_minutes']) * 60)
                if min(turns, seconds) < 1:
                    raise BudgetWait('Configured task limits disallow inference')
                with closing(sqlite3.connect(self.db.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                    before = [r[0] for r in db.execute("SELECT id FROM sessions WHERE source='oneshot'")]
                (directory / 'prompt.txt').write_text(prompt)
                write_json(directory / 'attempt.json', {'started': time.time(), 'model': self.policy['model'],
                           'provider': self.policy.get('provider'), 'max_turns': turns, 'seconds': seconds,
                           'research': research, 'sessions_before': before})
                started = time.monotonic()
                with tempfile.TemporaryDirectory(prefix='factory-task-') as neutral:
                    command = [str(self.hermes_root / '.venv/bin/python3'), str(self.hermes_root / 'hermes'),
                               'chat', '--oneshot', '-Q', '--query-file', str(directory / 'prompt.txt'),
                               '--source', 'oneshot', '--model', self.policy['model'],
                               '--ignore-rules', '--in', neutral,
                               '-t', self.policy['research_toolset'] if research else '__none__',
                               '--max-turns', str(turns), '--run-budget', str(seconds),
                               '--usage-file', str(directory / 'runtime-usage.json')]
                    if self.policy.get('provider'):
                        command.extend(['--provider', self.policy['provider']])
                    with w.session_marker(argparse.Namespace(max_turns=turns, run_budget=seconds)):
                        w.REPO = Path(neutral)
                        try:
                            result = w.run_agent(command, seconds + 30, fd)
                        except subprocess.TimeoutExpired as exc:
                            raise TaskFailure('Model task exceeded its wall-clock limit') from exc
                measured = usage(self.db, before)
                measured['elapsed_seconds'] = round(time.monotonic() - started, 3)
                write_json(directory / 'usage.json', measured)
                if result.returncode:
                    raise TaskFailure('Model task failed; recorded usage retained')
                response_text = w.strip_footer(result.stdout)
                if len(response_text.encode()) < 256 * 1024:
                    (directory / 'response.txt').write_text(response_text)
                value = parse_response(response_text)
                write_json(response_path, value)
                return value
        except w.SessionBusy as exc:
            raise BudgetWait('Another bounded research task is still running') from exc
