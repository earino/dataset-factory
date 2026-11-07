"""One fresh, no-tool audit session through existing Hermes admission/accounting.

No direct provider API, new allowance, model override or authentication change.
The installed-version zero-tool capability must be reviewed and pinned first.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

from .admission import require
from .adversarial_execution import bounded_json, write_json
from .asset_integrity import sha256, safe_path
from .leakage_battery import digest
from .release_audit import capsule, prompt, validate_response

RUNTIME_FILES = ('model_tools.py','hermes_cli/main.py','hermes_cli/cli_agent_setup_mixin.py',
                 'hermes_cli/cli_single_query.py')


def wrapper(root):
    path=Path(root)/'scripts/scout_research_session.py'
    spec=importlib.util.spec_from_file_location('audit_research_admission',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def db_open(db):
    return sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True,timeout=1)


def sessions(db, source):
    with closing(db_open(db)) as con:
        return {row[0] for row in con.execute('select id from sessions where source=?',(source,))}


def measured(db, sid, source):
    with closing(db_open(db)) as con:
        row=con.execute('select source,tool_names from sessions where id=?',(sid,)).fetchone()
        if row is None or row[0]!=source:raise ValueError('audit session source accounting mismatch')
        pin=row[1]
        if pin is not None:
            try: names=json.loads(pin)
            except (ValueError,TypeError):
                record=con.execute('select prompt from system_prompts where hash=?',(pin,)).fetchone()
                if record is None:raise ValueError('audit tool pin cannot be resolved')
                names=json.loads(record[0]).get('tools')
            if names!=[]:raise ValueError('audit session offered tools')
        if con.execute("select count(*) from messages where session_id=? and role='tool'",(sid,)).fetchone()[0]:
            raise ValueError('audit session executed a tool')
        for (calls,) in con.execute("select tool_calls from messages where session_id=? and role='assistant'",(sid,)):
            if calls not in (None,'','[]'):raise ValueError('audit session attempted a tool call')
        rows=con.execute('select task,model,billing_provider,api_call_count,input_tokens,output_tokens,'
                         'cache_read_tokens,cache_write_tokens from session_model_usage where session_id=?',
                         (sid,)).fetchall()
        if not rows:raise ValueError('audit session has no measured usage')
        tasks=[];tokens=0
        for task,model,provider,calls,inputs,outputs,read,write in rows:
            if any(type(n) is not int or n<0 for n in (calls,inputs,outputs,read,write)):
                raise ValueError('audit session usage is invalid')
            tokens+=inputs+outputs+read+write
            tasks.append({'task':task,'model':model,'provider':provider,'calls':calls,
                          'input_tokens':inputs,'output_tokens':outputs,
                          'cache_read_tokens':read,'cache_write_tokens':write})
        if not tokens or not any(t['calls'] for t in tasks if t['task'] in (None,'')):
            raise ValueError('audit has no recorded main inference')
        return {'session_id':sid,'source':source,'tokens':tokens,'tasks':tasks,
                'tool_pin':'unrecorded' if pin is None else 'verified_empty',
                'executed_tools':0,'attempted_tool_calls':0,
                'scope':'Recorded usage/route, not independent provider model attestation'}


def preflight(root, hermes_root, runner=subprocess.run):
    policy=bounded_json(Path(root)/'config/adversarial-runtime.json')
    if policy.get('reviewed') is not True or set(policy.get('source_sha256',{}))!=set(RUNTIME_FILES):
        raise ValueError('installed audit runtime has not been reviewed and pinned')
    actual={name:sha256(safe_path(hermes_root,name)) for name in RUNTIME_FILES}
    if actual!=policy['source_sha256']:raise ValueError('installed audit runtime changed; review capability again')
    if any(key.startswith('HERMES_KANBAN') for key in os.environ):
        raise ValueError('dispatcher environment is incompatible with no-tool audit')
    # Reuse the deployed evaluation's demonstrated capability, never assume an
    # unknown toolset disables tools. This assertion runs before any model call.
    code='from model_tools import get_tool_definitions as g; assert g(enabled_toolsets=["__none__"], quiet_mode=True)==[]'
    result=runner([str(hermes_root/'.venv/bin/python3'),'-c',code],cwd=hermes_root,
                  env={**os.environ,'PYTHONPATH':str(hermes_root)},capture_output=True,timeout=30)
    if result.returncode:raise ValueError('installed zero-tool capability failed; model was not started')
    return {'source_sha256':actual,'policy_sha256':sha256(Path(root)/'config/adversarial-runtime.json'),
            'preflight_empty_definitions':True}


def run(root, dataset, output, *, hermes_root=Path('/opt/hermes'), hermes_home=Path('/opt/data')):
    root,output,hermes_root=Path(root).resolve(),Path(output),Path(hermes_root)
    require(root,'autonomous adversarial audit')
    w=wrapper(root)
    with w.admission_lock() as fd:
        value=capsule(root,dataset)
        allowed,_,reason=w.run_gate()
        if not allowed:raise ValueError('audit held by research budget: '+reason)
        runtime=preflight(root,hermes_root)
        from .audit_workflow import verify_staging
        staging=verify_staging(root,dataset)
        limits=bounded_json(root/'config/research-budget.json')
        seconds=min(600,int(limits['session_max_minutes'])*60)
        turns=min(2,int(limits['session_max_turns']))
        if seconds<1 or turns<1:raise ValueError('configured session bounds refuse audit')
        output.mkdir(parents=True,exist_ok=False)
        write_json(output/'capsule.json',value)
        text=prompt(value);(output/'prompt.txt').write_text(text)
        db=Path(hermes_home)/'state.db';before=sessions(db,w.LAUNCH_SOURCE)
        pending={'version':'1.0.0','status':'pending','binding_digest':digest(value['binding']),
                 'prompt_sha256':sha256(output/'prompt.txt'),'runtime':runtime,
                 'staging_readback':staging,
                 'started_at':datetime.now(timezone.utc).isoformat(),'source':w.LAUNCH_SOURCE,
                 'max_turns':turns,'run_budget':seconds}
        write_json(output/'attempt.json',pending)  # Interrupted attempts remain visible, never a pass.
        w.note({'event':'adversarial_audit_started','dataset':dataset,
                'binding_digest':pending['binding_digest'],'submitted_brief_sha256':pending['prompt_sha256'],
                'max_turns':turns,'run_budget':seconds})
        started=time.monotonic()
        try:
            with tempfile.TemporaryDirectory(prefix='factory-audit-context-') as neutral:
                directory=Path(neutral)
                markers=('AGENTS.md','CLAUDE.md','.cursorrules','.git','Makefile')
                if any((parent/name).exists() for parent in (directory,*directory.parents) for name in markers):
                    raise ValueError('neutral audit context has inherited project instructions')
                command=[str(hermes_root/'.venv/bin/python3'),str(hermes_root/'hermes'),'chat',
                         '--oneshot','-Q','--query-file',str((output/'prompt.txt').resolve()),
                         '--source',w.LAUNCH_SOURCE,'-t','__none__','--ignore-rules','--in',neutral,
                         '--max-turns',str(turns),'--run-budget',str(seconds)]
                with w.session_marker(argparse.Namespace(max_turns=turns,run_budget=seconds)):
                    w.REPO=directory
                    result=w.run_agent(command,seconds+60,fd)
            created=sessions(db,w.LAUNCH_SOURCE)-before
            if len(created)!=1:raise ValueError('audit session identity is ambiguous; reconcile attempt')
            usage=measured(db,created.pop(),w.LAUNCH_SOURCE)
            write_json(output/'usage.json',usage)  # Preserve measured usage before judging model output.
            if result.returncode:raise ValueError('audit model invocation did not complete')
            response_text=w.strip_footer(result.stdout).strip()
            # The reviewed installed toolset emits this exact notice before the final response.
            notice='Warning: Unknown toolsets: __none__\n'
            if response_text.startswith(notice):response_text=response_text[len(notice):]
            if len(response_text.encode())>=256*1024:raise ValueError('model audit response exceeds report limit')
            (output/'response.json').write_text(response_text+'\n')
            response=bounded_json(output/'response.json')
            proposal=validate_response(value,response)
            write_json(output/'proposal.json',proposal)
            if sha256(output/'prompt.txt')!=pending['prompt_sha256']:
                raise ValueError('submitted audit prompt changed during the session')
            if capsule(root,dataset)!=value:raise ValueError('staged audit inputs changed during model session')
            receipt={**pending,'status':'completed','elapsed_seconds':round(time.monotonic()-started,3),
                     'response_sha256':sha256(output/'response.json'),'proposal_sha256':sha256(output/'proposal.json'),
                     'capsule_sha256':sha256(output/'capsule.json'),'usage_sha256':sha256(output/'usage.json'),
                     'session_id':usage['session_id'],'verdict':response['verdict'],
                     'scope':'Internal model audit only; worker attacks and operator independent audit still required'}
            write_json(output/'session.json',receipt)
            w.note({'event':'adversarial_audit_completed','dataset':dataset,'session_id':usage['session_id'],
                    'submitted_brief_sha256':pending['prompt_sha256'],'tokens':usage['tokens'],
                    'verdict':response['verdict'],'elapsed_seconds':receipt['elapsed_seconds']})
            return receipt
        except Exception as exc:
            write_json(output/'failure.json',{'status':'incomplete','error_type':type(exc).__name__,
                       'elapsed_seconds':round(time.monotonic()-started,3),'release_authorized':False})
            w.note({'event':'adversarial_audit_incomplete','dataset':dataset,'error_type':type(exc).__name__})
            raise
