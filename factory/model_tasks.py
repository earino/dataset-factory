"""Bounded judgment/code tasks through the installed Hermes CLI and allowance.

The model returns data. It cannot edit the coordinator, launch workers, publish,
or decide lifecycle transitions. Successful responses are reused after restart.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
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


def startup_diagnostic(stderr):
    """Keep bounded failure text while removing credential-like material."""
    text = str(stderr)[-8000:]
    for name, value in os.environ.items():
        if len(value) >= 4 and re.search(r'TOKEN|SECRET|PASSWORD|API_KEY', name, re.I):
            text = text.replace(value, '[redacted]')
    text = re.sub(r'https?://[^\s<>]+', '[url]', text)
    text = re.sub(r'(?i)\bBearer\s+\S+', 'Bearer [redacted]', text)
    text = re.sub(r'''(?i)(["']?(?:token|api_key|password|secret|authorization)["']?\s*[:=]\s*)("[^"]*"|'[^']*'|[^\s,}]+)''',
                  r'\1[redacted]', text)
    text = re.sub(r'\b(?:sk-|hf_|ghp_|github_pat_)[A-Za-z0-9_-]+', '[redacted]', text)
    text = re.sub(r'[A-Za-z0-9_+/=-]{32,}', '[opaque-value]', text)
    return text[-4000:]


def parse_response(text):
    text = text.strip()
    if text.startswith('Warning: Unknown toolsets: __none__\n'):
        text = text.split('\n', 1)[1].strip()
    lines = text.splitlines()
    if (len(lines) >= 3 and lines[0].strip().lower() in ('```', '```json')
            and lines[-1].strip() == '```'):
        text = '\n'.join(lines[1:-1]).strip()
    if len(text.encode()) >= 256 * 1024:
        raise TaskFailure('Model response exceeds compact report limit')
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        try:
            # Recover only a missing final object delimiter after a complete
            # nested object. Never finish a string, scalar, key or other token.
            if not (exc.pos == len(text) and text.startswith('{') and text.endswith('}')):
                raise ValueError('Not a final object delimiter')
            value = json.loads(text + '}')
        except ValueError:
            raise TaskFailure(f'Model response is not JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}') from exc
    if not isinstance(value, dict):
        raise TaskFailure('Model response must be an object')
    return value


def runtime_session(stderr):
    # The installed quiet CLI emits this automation field after syncing the
    # gateway's session ID. A separate oneshot outside our mutex is not ours.
    matches = re.findall(r'^session_id: ([A-Za-z0-9_-]+)\s*$', str(stderr), re.M)
    return matches[-1] if matches else None


def usage(db_path, before, session_id=None):
    """Read actual session accounting; price fields are not actual spend."""
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        created = {r[0] for r in db.execute("SELECT id FROM sessions WHERE source='oneshot'")} - set(before)
        if session_id is not None:
            if session_id not in created:
                raise TaskFailure('CLI session identity is not a new recorded oneshot session')
            sid = session_id
        else:
            if len(created) != 1:
                raise TaskFailure(f'Expected one model session; observed {len(created)} new sessions')
            sid = created.pop()
        rows = db.execute('SELECT task,model,billing_provider,api_call_count,input_tokens,output_tokens,'
                          'cache_read_tokens,cache_write_tokens FROM session_model_usage WHERE session_id=?',
                          (sid,)).fetchall()
        if not rows:
            raise TaskFailure('Model session has no measured usage')
        fields = ('task', 'model', 'provider', 'calls', 'input_tokens', 'output_tokens',
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

    def run(self, task_id, prompt, *, research=False, construction=False):
        from .common import identifier
        identifier(task_id)
        # Repairs include the accepted-size builder, semantic descriptor and
        # source evidence. The former 64 KiB bound rejected a real STATS19 repair.
        if len(prompt.encode()) > 128 * 1024:
            raise TaskFailure('Task context exceeds 128 KiB')
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
                toolsets = [self.policy['research_toolset']] if research else []
                expected = ['web_search', 'web_extract'] if research else []
                probe = ('from model_tools import get_tool_definitions as g; '
                         'd=g(enabled_toolsets=' + repr(toolsets) + ',quiet_mode=True); '
                         'assert sorted(x.get("function",x)["name"] for x in d)==sorted(' + repr(expected) + ')')
                checked = subprocess.run([str(self.hermes_root / '.venv/bin/python3'), '-c', probe],
                                         cwd=self.hermes_root, env={**os.environ, 'PYTHONPATH': str(self.hermes_root)},
                                         capture_output=True, timeout=30)
                if checked.returncode:
                    raise TaskFailure('Installed runtime does not expose the bounded task toolset')
                with closing(sqlite3.connect(self.db.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                    before = [r[0] for r in db.execute("SELECT id FROM sessions WHERE source='oneshot'")]
                (directory / 'prompt.txt').write_text(prompt)
                write_json(directory / 'attempt.json', {'started': time.time(), 'model': self.policy['model'],
                           'provider': self.policy.get('provider'), 'max_turns': turns, 'seconds': seconds,
                           'research': research, 'toolsets': toolsets, 'sessions_before': before})
                started = time.monotonic()
                with tempfile.TemporaryDirectory(prefix='factory-task-') as neutral:
                    command = [str(self.hermes_root / '.venv/bin/python3'), str(self.hermes_root / 'hermes'),
                               'chat', '--oneshot', '-Q', '--query-file', str(directory / 'prompt.txt'),
                               '--source', 'oneshot', '--model', self.policy['model'],
                               '--ignore-rules', '--in', neutral,
                               '-t', self.policy.get('research_toolset', 'web'),
                               '--max-turns', str(turns), '--run-budget', str(seconds)]
                    if not research:
                        command = [str(self.hermes_root / '.venv/bin/python3'),
                                   str(self.root / 'factory/hermes_write_task.py'),
                                   '--hermes-root', str(self.hermes_root),
                                   '--query-file', str(directory / 'prompt.txt'),
                                   '--model', self.policy['model'], '--max-turns', str(turns),
                                   '--run-budget', str(seconds)]
                    if self.policy.get('provider'):
                        command.extend(['--provider', self.policy['provider']])
                    with w.session_marker(argparse.Namespace(max_turns=turns, run_budget=seconds)):
                        w.REPO = Path(neutral)
                        try:
                            result = w.run_agent(command, seconds + 30, fd)
                        except subprocess.TimeoutExpired as exc:
                            stderr = exc.stderr or ''
                            if isinstance(stderr, bytes):
                                stderr = stderr.decode('utf-8', errors='replace')
                            failure = {'error': 'timeout', 'limit_seconds': seconds + 30,
                                       'diagnostic': startup_diagnostic(stderr)}
                            try:
                                measured = usage(self.db, before, runtime_session(stderr))
                                measured.update(elapsed_seconds=round(time.monotonic() - started, 3),
                                                partial=True, outcome='timeout')
                                write_json(directory / 'usage.json', measured)
                            except TaskFailure as accounting:
                                failure['accounting'] = str(accounting)
                            write_json(directory / 'failure.json', failure)
                            raise TaskFailure('Model task exceeded its wall-clock limit') from exc
                proposal = None
                if result.returncode:
                    # Preserve the startup failure, not just its missing session.
                    # Raw provider stderr is never persisted.
                    parser_error = [line for line in result.stderr.splitlines()
                                    if 'error: unrecognized arguments:' in line or 'error: argument ' in line]
                    failure = {'exit_code': result.returncode, 'parser_error': parser_error[-2:],
                               'diagnostic': startup_diagnostic(result.stderr),
                               'response_diagnostic': startup_diagnostic(result.stdout)}
                    try:
                        write_json(directory / 'usage.json', usage(self.db, before, runtime_session(result.stderr)))
                    except TaskFailure as exc:
                        failure['accounting'] = str(exc)
                    # Hermes can return exit 1 at its iteration cap after a
                    # complete code proposal. A proposal is not artifact acceptance:
                    # require its construction contract and the measured route,
                    # then let the worker qualification and semantic review decide.
                    if result.returncode == 1 and construction and 'accounting' not in failure:
                        from .construction import validate
                        try:
                            from .construction import merge_repair
                            proposal = validate(merge_repair(None, parse_response(w.strip_footer(result.stdout))))
                            failure['usable_construction_proposal'] = True
                        except (FactoryError, ValueError, TypeError, KeyError):
                            pass
                    if result.returncode == 1 and research and 'accounting' not in failure:
                        # A completed negative judgment needs no repeated research.
                        # It can only defer/reject; ready/accept still require exit 0.
                        try:
                            negative = parse_response(w.strip_footer(result.stdout))
                            if (negative.get('verdict') in ('defer', 'reject')
                                    and isinstance(negative.get('reason'), str)
                                    and negative['reason'].strip()):
                                proposal = negative
                                failure['usable_negative_verdict'] = True
                        except TaskFailure:
                            pass
                    write_json(directory / 'failure.json', failure)
                    if proposal is None:
                        raise TaskFailure('Model invocation failed: ' + json.dumps(failure))
                measured = usage(self.db, before, runtime_session(result.stderr))
                measured['elapsed_seconds'] = round(time.monotonic() - started, 3)
                measured['completion_exit_code'] = result.returncode
                write_json(directory / 'usage.json', measured)
                if not research and measured.get('tool_results') != 0:
                    raise TaskFailure('Write-only task unexpectedly executed tools')
                main_tasks = [task for task in measured['tasks'] if task['task'] in (None, '')]
                if not main_tasks or any(task['model'] != self.policy['model'] for task in main_tasks):
                    raise TaskFailure('Recorded inference route differs from the configured model')
                response_text = w.strip_footer(result.stdout)
                if len(response_text.encode()) < 256 * 1024:
                    (directory / 'response.txt').write_text(response_text)
                value = proposal if proposal is not None else parse_response(response_text)
                write_json(response_path, value)
                return value
        except w.SessionBusy as exc:
            raise BudgetWait('Another bounded research task is still running') from exc
