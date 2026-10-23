#!/usr/bin/env python3
"""Hosted, sequential, no-tool evaluation using the existing research admission.

Initialize ONE evaluation directory with --init; all subsequent calls share it.
Missing/corrupt accounting or an interrupted attempt requires explicit reconciliation,
never a zero-use fallback. Raw responses stay local until reviewed for publication.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
# Revised-bundle comparison extension under the operator's explicit token authority.
# Reuse the original ledger; these are cumulative checkpoints, never a fresh allowance.
MAX_CALLS, MAX_TOKENS, RESERVE = 120, 5_000_000, 100_000
MARKERS = ('AGENTS.md','CLAUDE.md','.cursorrules','.git','Makefile')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_ledger(path):
    data = json.loads(path.read_text())  # absence/corruption is fatal
    if data.get('schema') != 1 or not isinstance(data.get('runs'), list):
        raise ValueError('invalid evaluation ledger')
    for key in ('calls','tokens'):
        if type(data.get(key)) is not int or data[key] < 0:
            raise ValueError('invalid evaluation counters')
    if data['calls'] != len(data['runs']):
        raise ValueError('invocation ledger disagrees with count')
    for run in data['runs']:
        if run.get('status') == 'reconciled_no_inference':
            # Manual, evidence-backed reconciliation only. Preserve the failed
            # attempt and count it; absence of usage is never enough for this state.
            audit = run.get('reconciliation', {})
            if (type(run.get('tokens')) is not int or run['tokens'] != 0
                    or audit.get('original_status') != 'failed'
                    or not all(isinstance(audit.get(k), str) and audit[k].strip()
                               for k in ('reviewer', 'evidence', 'reason'))):
                raise ValueError('no-inference reconciliation lacks evidence')
        elif run.get('status') != 'ok':
            raise ValueError('prior failed/pending invocation needs reconciliation')
        elif type(run.get('tokens')) is not int or run['tokens'] <= 0:
            raise ValueError('invalid per-invocation tokens')
    if sum(r['tokens'] for r in data['runs']) != data['tokens']:
        raise ValueError('token ledger disagrees with count')
    return data


def save(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.evaluation-')
    try:
        with os.fdopen(fd,'w') as handle:
            json.dump(data,handle,indent=2); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp,path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def neutral(path):
    path = path.resolve()
    if not path.is_dir():
        raise ValueError('neutral fixture directory must exist')
    if any((parent / marker).exists() for parent in (path,*path.parents) for marker in MARKERS):
        raise ValueError('fixture has a project/context marker in its ancestry')
    return path


def measured_session(db, sid):
    con = sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)
    try:
        row = con.execute('select source,tool_names from sessions where id=?',(sid,)).fetchone()
        if row is None or row[0] != 'scout-research':
            raise ValueError('session not recorded as research')
        # Current Hermes may omit an empty pin, or store a hash into system_prompts.
        # A NULL pin is not proof of emptiness: retain it as unrecorded and combine
        # with the installed zero-tool preflight and zero executed tool messages.
        pin = row[1]
        if isinstance(pin,str) and re.fullmatch('[a-f0-9]{64}',pin):
            payload = con.execute('select prompt from system_prompts where hash=?',(pin,)).fetchone()
            if payload is None:
                raise ValueError('missing tool pin payload')
            names = json.loads(payload[0]).get('tools')
        else:
            names = json.loads(pin) if isinstance(pin,str) else pin
        if (pin is not None and names != []) or (pin is None and names is not None):
            raise ValueError('tool definitions were present')
        if con.execute("select count(*) from messages where session_id=? and role='tool'",(sid,)).fetchone()[0]:
            raise ValueError('tool execution was recorded')
        rows = con.execute('select task,api_call_count,input_tokens,output_tokens,cache_read_tokens,cache_write_tokens from session_model_usage where session_id=?',(sid,)).fetchall()
        if not rows:
            raise ValueError('missing model usage')
        totals={'calls':0,'input_tokens':0,'output_tokens':0,'cache_read_tokens':0,'cache_write_tokens':0,'tasks':[],
                'recorded_tool_pin':'unrecorded' if pin is None else 'verified_empty'}
        for task,calls,inputs,outputs,cache_read,cache_write in rows:
            if any(type(n) is not int or n < 0 for n in (calls,inputs,outputs,cache_read,cache_write)):
                raise ValueError('invalid model usage')
            totals['calls']+=calls; totals['input_tokens']+=inputs; totals['output_tokens']+=outputs
            totals['cache_read_tokens']+=cache_read; totals['cache_write_tokens']+=cache_write
            totals['tasks'].append({'task':task,'calls':calls,'input_tokens':inputs,'output_tokens':outputs,
                                    'cache_read_tokens':cache_read,'cache_write_tokens':cache_write})
        totals['tokens']=sum(totals[k] for k in ('input_tokens','output_tokens','cache_read_tokens','cache_write_tokens'))
        if totals['tokens'] <= 0:
            raise ValueError('no measured tokens')
        return totals
    finally:
        con.close()


def research_sessions(db):
    con = sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)
    try:
        return {row[0] for row in con.execute("select id from sessions where source='scout-research'")}
    finally:
        con.close()


def new_session(db, before):
    created = research_sessions(db) - before
    if len(created) != 1:
        raise ValueError('expected exactly one new research session; reconcile before continuing')
    return created.pop()


def main_routes(db, sid):
    con = sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)
    try:
        return [{'model':model, 'provider':provider, 'calls':calls}
                for model,provider,calls in con.execute(
                    "select model,billing_provider,api_call_count from session_model_usage "
                    "where session_id=? and coalesce(task,'')=''", (sid,))]
    finally:
        con.close()


def wrapper(live):
    path=ROOT/'scripts/scout_research_session.py'
    spec=importlib.util.spec_from_file_location('eval_admission',path)
    module=importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    module.REPO=live; module.BUDGET=live/'scripts/research-budget.py'
    module.FACTORY_DIR=live/'.factory'; module.LOCK=module.FACTORY_DIR/'research-session.lock'
    module.LOG=module.FACTORY_DIR/'research-sessions.jsonl'
    return module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--init',action='store_true')
    p.add_argument('--request',type=Path)
    p.add_argument('--sha256')
    p.add_argument('--case'); p.add_argument('--arm',choices=('baseline','revised'))
    p.add_argument('--model'); p.add_argument('--provider')
    p.add_argument('--fixture',type=Path)
    p.add_argument('--live',type=Path,default=Path('/opt/data/dataset-factory'))
    p.add_argument('--hermes-root',type=Path,default=Path('/opt/hermes'))
    p.add_argument('--hermes-home',type=Path,default=Path('/opt/data'))
    a=p.parse_args()
    if a.init:
        a.out.mkdir(parents=True,exist_ok=False)
        save(a.out/'ledger.json',{'schema':1,'calls':0,'tokens':0,'runs':[]})
        return 0
    if not all((a.request,a.sha256,a.case,a.arm,a.model,a.provider,a.fixture)):
        p.error('a run requires request/hash/case/arm/model/provider/fixture')
    out=a.out.resolve(); fixture=neutral(a.fixture)
    req=a.request.resolve()
    if req.stat().st_size > 256*1024 or sha(req) != a.sha256:
        raise ValueError('request size or digest mismatch')
    w=wrapper(a.live.resolve())
    with w.admission_lock() as fd:
        ledger=read_ledger(out/'ledger.json')
        if ledger['calls'] >= MAX_CALLS or ledger['tokens']+RESERVE > MAX_TOKENS:
            raise ValueError('evaluation ceiling/reserve reached')
        allowed,_,reason=w.run_gate()
        if not allowed:
            print(json.dumps({'status':'held','reason':reason})); return 3
        # Read-only source introspection, in the same installed interpreter. Fail closed
        # if an upgrade changes the undocumented empty-toolset behavior.
        preflight=out/'tool_preflight.py'
        preflight.write_text('from model_tools import get_tool_definitions as g\n'
                             'assert g(enabled_toolsets=["__none__"],quiet_mode=True)==[]\n')
        env={**os.environ,'PYTHONPATH':str(a.hermes_root)}
        probe=subprocess.run([str(a.hermes_root/'.venv/bin/python3'),str(preflight)],
                             cwd=a.hermes_root,env=env,capture_output=True,timeout=30)
        if probe.returncode:
            raise ValueError('installed zero-tool preflight failed')
        run_dir=out/f"run-{ledger['calls']+1:02d}"
        run_dir.mkdir(exist_ok=False)
        entry={'case':a.case,'arm':a.arm,'model_requested':a.model,'provider_requested':a.provider,
               'request_sha256':a.sha256,'status':'pending','directory':run_dir.name,
               'context_scope':'chat --ignore-rules suppresses discovered context and built-in memory',
               'runtime_sha256':{name:sha(a.hermes_root/name) for name in ('model_tools.py','hermes_cli/main.py','hermes_cli/cli_agent_setup_mixin.py','hermes_cli/cli_single_query.py')},
               'started_at':time.time(),'tokens':None}
        db=a.hermes_home/'state.db'
        before=research_sessions(db)
        entry['research_sessions_before']=sorted(before)
        ledger['calls']+=1; ledger['runs'].append(entry)
        save(out/'ledger.json',ledger)  # a killed/unknown-cost attempt blocks future calls
        args=argparse.Namespace(max_turns=1,run_budget=300)
        command=[str(a.hermes_root/'.venv/bin/python3'),str(a.hermes_root/'hermes'),'chat',
                 '--oneshot','-Q','--query-file',str(req),'--source','scout-research',
                 '-m',a.model,'--provider',a.provider,'-t','__none__','--max-turns','1',
                 '--run-budget','300','--in',str(fixture),'--ignore-rules']
        started=time.monotonic()
        try:
            with w.session_marker(args):
                w.REPO=fixture  # gate/config/marker paths above remain the live ones
                result=w.run_agent(command,360,fd)
            (run_dir/'response.txt').write_text(result.stdout)
            # Private diagnostic only; inspect/redact before exporting results.
            (run_dir/'stderr.txt').write_text(result.stderr)
            sid=new_session(db,before)
            entry['session_id']=sid
            measurement=measured_session(db,sid)
            entry.update(measurement)
            ledger['tokens']+=measurement['tokens']  # charge BEFORE judging outcome/model
            entry['dollar_spend']=None
            entry['exit_code']=result.returncode
            entry['route_scope']='session usage rows; not independent provider served-model attestation'
            routes=main_routes(db,sid)
            entry['main_routes']=routes
            if result.returncode:
                raise ValueError('provider/invocation incomplete')
            if not result.stdout.strip():
                raise ValueError('empty decision response')
            if not routes or any(r['model'] != a.model or r['provider'] != a.provider
                                 or type(r['calls']) is not int or r['calls'] <= 0 for r in routes):
                raise ValueError('usage route mismatch; preserve and inspect before continuing')
            if ledger['tokens'] > MAX_TOKENS:
                raise ValueError('measured ceiling exceeded within invocation; stop')
            entry['status']='ok'
        except Exception as exc:
            entry['status']='failed'; entry['error_type']=type(exc).__name__
            if isinstance(exc, subprocess.TimeoutExpired):
                for name, value in (('response.txt',exc.output),('stderr.txt',exc.stderr)):
                    if value:
                        if isinstance(value,bytes):
                            value=value.decode(errors='replace')
                        (run_dir/name).write_text(value[:256*1024])
                entry['partial_capture']='timeout; bounded excerpt, usage may be unavailable'
            # No raw provider exception or credential-bearing output in shared diagnostics.
            raise
        finally:
            entry['elapsed_seconds']=round(time.monotonic()-started,3)
            save(out/'ledger.json',ledger)
            print(json.dumps({'status':entry['status'],'run':entry['directory'],
                              'calls':ledger['calls'],'tokens':ledger['tokens']}))
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'Evaluation stopped ({type(exc).__name__}); inspect local evidence.',file=sys.stderr)
        sys.exit(2)
