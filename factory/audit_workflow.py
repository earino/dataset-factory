"""Prepare, execute and admit an autonomous release audit using existing workers."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote

from . import adversarial_execution as execution
from . import release_audit as audit
from . import worker
from .asset_integrity import safe_path, sha256
from .common import FactoryError, identifier, read_json, write_json, locked
from .leakage_battery import digest
from .reconciliation import committed_record, bookkeep
from .site_github import GitHub


def hub_state(root, repo, tag):
    """Use the existing publishing environment and write credential for metadata only."""
    interpreter=Path('/opt/data/.venvs/hf/bin/python')
    if not interpreter.is_file():raise ValueError('existing Hugging Face publishing environment is unavailable')
    code=('import json,sys; from huggingface_hub import HfApi; '
          'from factory.http import secret; from factory.hub_integrity import refs; '
          'api=HfApi(token=secret("FACTORY_HF_WRITE_TOKEN")); '
          'info=api.repo_info(sys.argv[1],repo_type="dataset",revision=sys.argv[2]); '
          'main,tags=refs(api,sys.argv[1]); '
          'print(json.dumps({"private":info.private,"commit":info.sha,"main":main,"tag":tags.get(sys.argv[2])}))')
    result=subprocess.run([str(interpreter),'-c',code,repo,tag],cwd=root,capture_output=True,timeout=60)
    if result.returncode or len(result.stdout)>4096:
        raise ValueError('bounded Hugging Face staging read-back failed')
    return json.loads(result.stdout)


def verify_staging(root, dataset, *, api=None, hub_reader=None):
    root=Path(root);api=api or GitHub();hub_reader=hub_reader or hub_state
    destinations=execution.bounded_json(root/'release'/dataset/'DESTINATIONS.json')
    tag=destinations['release_tag'];entries=destinations['destinations'];gh=entries['github'];hf=entries['huggingface']
    info=api.request('GET',f'repos/{gh["repo"]}')
    if info.get('private') is not True:raise ValueError('GitHub staging is no longer private')
    commits=[]
    for ref in (tag,info['default_branch']):
        commits.append(api.request('GET',f'repos/{gh["repo"]}/commits/{quote(ref,safe="")}')['sha'])
    if commits!=[gh['target_commit']]*2:raise ValueError('GitHub staging commits changed')
    hub=hub_reader(root,hf['repo'],tag)
    if hub.get('private') is not True or any(hub.get(k)!=hf['commit'] for k in ('commit','main','tag')):
        raise ValueError('Hugging Face staging privacy or commits changed')
    return {'destinations_sha256':sha256(root/'release'/dataset/'DESTINATIONS.json'),
            'github_commit':commits[0],'huggingface_commit':hub['commit'],'both_private':True}


def copy_once(source, destination):
    source,destination=Path(source),Path(destination)
    if source.is_symlink() or source.stat().st_size>=execution.LIMIT:
        raise ValueError('audit evidence must be a bounded regular file')
    if destination.exists():
        if destination.is_symlink() or source.read_bytes()!=destination.read_bytes():
            raise ValueError('audit evidence path already contains different bytes')
        return
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as handle:handle.write(source.read_bytes())


def worker_plan(root, model_directory, *, api=None, hub_reader=None):
    root=Path(root);api=api or GitHub()
    value,session,response,_=audit.model_evidence(root,model_directory)
    binding=value['binding'];dataset=binding['dataset'];key=digest(binding)[:16]
    if response['verdict']!='pass':
        raise ValueError('model blocked or could not complete this package; worker spend is not admitted')
    verify_staging(root,dataset,api=api,hub_reader=hub_reader)
    job_id=identifier('audit-'+dataset[:24]+'-'+key)
    directory=safe_path(root,f'candidates/{dataset}/autonomous-audit/{key}')
    relative=directory.relative_to(root).as_posix()
    manifest=execution.bounded_json(root/'release'/dataset/'MANIFEST.json')
    destinations=execution.bounded_json(root/'release'/dataset/'DESTINATIONS.json')['destinations']
    github=destinations['github'];repo=github['repo']
    info=api.request('GET',f'repos/{repo}')
    if info.get('private') is not True:raise ValueError('autonomous audit requires private GitHub staging')
    for ref in (binding['release_tag'],info['default_branch']):
        commit=api.request('GET',f'repos/{repo}/commits/{quote(ref,safe="")}')['sha']
        if commit!=github['target_commit']:raise ValueError('GitHub staging changed after model audit')
    release=api.request('GET',f'repos/{repo}/releases/tags/{quote(binding["release_tag"],safe="")}')
    if release.get('id')!=github['release_id']:raise ValueError('GitHub staging release changed')
    assets=[]
    for page in range(1,12):
        batch=api.request('GET',f'repos/{repo}/releases/{release["id"]}/assets?per_page=100&page={page}')
        assets+=batch
        if len(batch)<100:break
    else:raise ValueError('staged asset listing exceeds bounded audit')
    if len({a['name'] for a in assets})!=len(assets):raise ValueError('duplicate staged asset names')
    by_name={a['name']:a for a in assets};fetch=[]
    for name,entry in manifest['assets'].items():
        if not name.endswith('.csv'):continue
        actual=by_name.get(entry['asset_name'],{})
        if actual.get('size')!=entry['bytes'] or actual.get('digest')!='sha256:'+entry['sha256']:
            raise ValueError('staged data asset differs from manifest')
        fetch.append({'asset_id':actual['id'],'dest':name,'size':entry['bytes'],'sha256':entry['sha256']})
    if len(fetch)!=3:raise ValueError('autonomous audit needs all three full labelled splits')
    directory.mkdir(parents=True,exist_ok=True)
    for name in ('capsule.json','response.json','proposal.json','session.json','usage.json','prompt.txt','attempt.json'):
        copy_once(Path(model_directory)/name,directory/'model'/name)
    files=[[f'factory/{p.name}',f'factory/{p.name}'] for p in sorted((root/'factory').glob('*.py'))]
    files += [[name,name] for name in ('scripts/check-package.py','scripts/audit-release-worker.py',
                                      'config/frozen-releases.json','config/licensing-policy.json')]
    files += [['capsule.json',relative+'/model/capsule.json'],['response.json',relative+'/model/response.json']]
    job={'id':job_id,'candidate':dataset,'image':'python:3.13-slim',
         'command':['python3','-B','/workspace/scripts/audit-release-worker.py'],
         'server_type':'cpx32','location':'hel1','cpus':4,'memory_mb':6144,
         'timeout_minutes':120,'lifetime_minutes':180,'max_disk_mb':20000,
         'max_artifact_mb':20,'release':True,'fetch':{'repo':repo,'assets':fetch}}
    bundle={'name':job_id,'files':files,'overrides':{}}
    for name,data in (('job.json',job),('bundle.json',bundle)):
        path=directory/name
        if path.exists():
            if execution.bounded_json(path)!=data:raise ValueError('sealed audit job declaration changed')
        else:execution.write_json(path,data)
    return {'job_id':job_id,'declaration':relative+'/bundle.json','model_directory':relative+'/model',
            'next':['python3 scripts/assemble-job.py '+job_id,
                    'sh scripts/scout-factory worker plan .factory/jobs/'+job_id+'/job.json',
                    'sh scripts/scout-factory worker launch .factory/jobs/'+job_id+'/job.json'],
            'scope':'Preparation only; existing admission, allowance and single-worker rules apply'}


def download_report(repo, entry, path):
    """Fetch only a ledger-pinned compact report; never a row file or source archive."""
    if (type(entry.get('id')) is not int or type(entry.get('size')) is not int
            or not 0<entry['size']<execution.LIMIT or not audit.SHA.fullmatch(entry.get('sha256',''))):
        raise ValueError('staged audit report metadata is invalid or oversized')
    if Path(path).exists():
        data=Path(path).read_bytes()
    else:
        result=subprocess.run(['gh','api',f'repos/{repo}/releases/assets/{entry["id"]}',
                               '-H','Accept: application/octet-stream'],capture_output=True,timeout=60)
        if result.returncode:raise ValueError('staged audit report download failed')
        data=result.stdout
    if len(data)!=entry['size'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
        raise ValueError('staged audit report digest/size mismatch')
    if not Path(path).exists():
        with Path(path).open('xb') as handle:handle.write(data)
    return execution.bounded_json(path)


def collect_evidence(root, job_id, destination, config):
    root=Path(root);destination=Path(destination)
    record,ledger_sha,commit=committed_record(root,job_id)
    if record.get('result',{}).get('exit_code') not in (0,1,2):
        raise ValueError('worker audit interrupted; preserve diagnostics and reconcile')
    # The existing mechanical path checks live staging digests and provider absence.
    cleanup=bookkeep(root,job_id,config)
    if not cleanup.get('handled') or not cleanup.get('live_verified'):
        raise ValueError('worker evidence/cleanup is incomplete: '+str(cleanup.get('reason','unknown')))
    report=record['result'];assets=report['assets']
    manifests=[a for a in assets if a.get('name')=='manifest.json']
    if len(manifests)!=1:raise ValueError('worker staging manifest is ambiguous')
    destination.mkdir(parents=True,exist_ok=True)
    report_paths=set((root/'.factory').glob('*/result.json'))
    report_paths.update(root.glob('audits/**/*.json'))
    report_paths.update(root.glob('candidates/*/autonomous-audit/**/worker/*.json'))
    if sum(p.stat().st_size for p in report_paths if p.is_file())+5*execution.LIMIT > min(
            20*1024*1024,config['max_coordinator_reports_bytes']):
        raise ValueError('coordinator compact report allowance exhausted')
    raw=download_report(record['staging_repo'],manifests[0],destination/'staging-manifest.json')
    if raw.get('job',{}).get('id')!=job_id:raise ValueError('raw staging manifest belongs to another job')
    verified=[]
    names=[name for name in ('autonomous-audit.json','battery.json','model-attacks.json','model-freeze.json','incomplete.json')
           if any(a.get('file')=='output/'+name for a in raw.get('assets',[]))]
    if not names:raise ValueError('worker preserved no audit outcome report')
    for name in names:
        matches=[a for a in raw.get('assets',[]) if a.get('file')=='output/'+name]
        if len(matches)!=1 or matches[0].get('offset')!=0:
            raise ValueError('worker report logical path is missing, duplicated or chunked')
        entry=matches[0]
        ledger=[a for a in assets if a['id']==entry['id']]
        if len(ledger)!=1 or any(ledger[0].get(k)!=entry.get(k) for k in ('size','sha256','name')):
            raise ValueError('report is not bound by collected worker ledger')
        download_report(record['staging_repo'],entry,destination/name)
        verified.append({'file':name,'sha256':entry['sha256'],'asset_id':entry['id']})
    value={'job_id':job_id,'source_sha256':record['source_sha256'],'ledger_sha256':ledger_sha,
           'ledger_commit':commit,'staging_release_id':report['release_id'],
           'raw_manifest_sha256':sha256(destination/'staging-manifest.json'),'files':verified,
           'cleanup_receipt_sha256':sha256(safe_path(root,cleanup['receipt']))}
    path=destination/'collection.json'
    if path.exists():
        if execution.bounded_json(path)!=value:raise ValueError('prior audit collection differs')
    else:execution.write_json(path,value)
    return value


def check(root, dataset, directory):
    """Revalidate every local evidence binding before trusting awaiting_operator."""
    root,directory=Path(root),Path(directory)
    value,session,response,proposal=audit.model_evidence(root,directory/'model')
    binding=value['binding']
    if binding['dataset']!=dataset:raise ValueError('audit belongs to another candidate')
    collection=execution.bounded_json(directory/'worker/collection.json')
    record,ledger_sha,_=committed_record(root,collection['job_id'])
    if ledger_sha!=collection['ledger_sha256'] or record['source_sha256']!=collection['source_sha256']:
        raise ValueError('audit worker ledger/source changed')
    if record['job'].get('candidate')!=dataset or record.get('status')!='deleted':
        raise ValueError('audit worker does not name this candidate or cleanup is incomplete')
    if record.get('result',{}).get('exit_code')!=0 or record['result'].get('status')!='succeeded':
        raise ValueError('audit worker did not complete successfully')
    if record['job'].get('command')!=['python3','-B','/workspace/scripts/audit-release-worker.py']:
        raise ValueError('worker ledger did not execute the canonical audit entry point')
    sources=record['job'].get('source_files',[])
    pins={s['bundled_as']:s['sha256'] for s in sources}
    expected={**binding['implementation'],'capsule.json':sha256(directory/'model/capsule.json'),
              'response.json':sha256(directory/'model/response.json')}
    if len(pins)!=len(sources) or any(pins.get(name)!=expected_sha for name,expected_sha in expected.items()):
        raise ValueError('worker source inventory differs from audited implementation or model input')
    raw_path=directory/'worker/staging-manifest.json'
    if sha256(raw_path)!=collection['raw_manifest_sha256']:
        raise ValueError('raw worker staging manifest changed')
    ledger_assets=record['result']['assets']
    matching=[a for a in ledger_assets if a.get('name')=='manifest.json']
    if len(matching)!=1 or matching[0]['sha256']!=sha256(raw_path) or matching[0]['size']!=raw_path.stat().st_size:
        raise ValueError('raw worker manifest is not bound by committed collection')
    raw=execution.bounded_json(raw_path)
    if raw.get('job',{}).get('id')!=collection['job_id']:
        raise ValueError('raw worker manifest identifies another job')
    for item in collection['files']:
        path=safe_path(directory/'worker',item['file'])
        matches=[a for a in raw['assets'] if a.get('file')=='output/'+item['file']]
        ledger_matches=[a for a in ledger_assets if a.get('id')==item['asset_id']]
        if (len(matches)!=1 or len(ledger_matches)!=1 or matches[0].get('offset')!=0
                or matches[0]['id']!=item['asset_id']
                or any(a.get('sha256')!=item['sha256'] or a.get('size')!=path.stat().st_size
                       for a in (matches[0],ledger_matches[0]))
                or sha256(path)!=item['sha256']):
            raise ValueError('collected audit report changed')
    if {e['file'] for e in collection['files']}!={'autonomous-audit.json','battery.json','model-attacks.json','model-freeze.json'}:
        raise ValueError('audit collection is incomplete')
    staging=execution.bounded_json(directory/'worker/staging-readback.json')
    destinations=json.loads(value['documents']['DESTINATIONS.json']['text'])['destinations']
    if staging!={'destinations_sha256':binding['destinations_sha256'],
                 'github_commit':destinations['github']['target_commit'],
                 'huggingface_commit':destinations['huggingface']['commit'],'both_private':True}:
        raise ValueError('post-worker private staging verification differs from audited destinations')
    report=execution.bounded_json(directory/'worker/autonomous-audit.json')
    fixed=execution.bounded_json(directory/'worker/battery.json')
    novel=execution.bounded_json(directory/'worker/model-attacks.json')
    freeze=execution.bounded_json(directory/'worker/model-freeze.json')
    if (report.get('version')!=audit.VERSION or report.get('ok') is not True
            or report.get('completed') is not True or report.get('unchanged') is not True
            or report.get('deterministic_problems')!=[] or report.get('requires_semantic_review')!=[]
            or report.get('binding_digest')!=digest(binding) or report.get('artifact_digest')!=binding['artifact_digest']
            or report.get('implementation')!=audit.implementation(root)
            or report.get('model_response_sha256')!=sha256(directory/'model/response.json')
            or report.get('proposal_sha256')!=digest(proposal) or response['verdict']!='pass'
            or report.get('model_verdict')!='pass' or report.get('fixed_battery_passed') is not True):
        raise ValueError('autonomous audit refuses this package or has stale evidence')
    if (fixed.get('ok') is not True or fixed.get('failures')!=[] or fixed.get('code')!=execution.battery.code_identity()
            or novel.get('completed') is not True or novel.get('requires_semantic_review')!=[]
            or novel.get('artifact_digest')!=binding['artifact_digest'] or novel.get('proposal_sha256')!=digest(proposal)
            or novel.get('code')!=execution.code_identity()
            or freeze.get('code')!=execution.code_identity() or freeze.get('inputs')!=binding['files']
            or freeze.get('proposal')!=proposal or freeze.get('artifact_digest')!=binding['artifact_digest']
            or novel.get('freeze_sha256')!=sha256(directory/'worker/model-freeze.json')
            or report.get('model_freeze_sha256')!=sha256(directory/'worker/model-freeze.json')
            or report.get('fixed_battery_sha256')!=sha256(directory/'worker/battery.json')
            or report.get('model_attacks_sha256')!=sha256(directory/'worker/model-attacks.json')):
        raise ValueError('fixed or novel recovery evidence refuses queue admission')
    return {'version':audit.VERSION,'ok':True,'dataset':dataset,'binding_digest':digest(binding),
            'artifact_version':binding['artifact_version'],'manifest_sha256':binding['manifest_sha256'],
            'model_session_id':session['session_id'],'worker_job':collection['job_id'],
            'collection_sha256':sha256(directory/'worker/collection.json'),
            'staging_readback_sha256':sha256(directory/'worker/staging-readback.json'),
            'scope':'Internal audit passed; independent operator-relayed audit and explicit flip approval still required'}


def queue_ready(root, record):
    if record.get('status')!='packaged' or record.get('awaiting_operator') is not True:return False
    try:
        pointer=record['autonomous_audit'];directory=safe_path(Path(root),pointer['directory'])
        verdict=execution.bounded_json(directory/'verdict.json')
        return (sha256(directory/'verdict.json')==pointer['sha256']
                and verdict==check(root,record['id'],directory))
    except (FactoryError,OSError,ValueError,KeyError,TypeError,AttributeError):
        return False


def main(root, argv):
    root=Path(root)
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    for name in ('prepare','model'):
        sub.add_parser(name).add_argument('dataset')
    plan=sub.add_parser('worker-plan');plan.add_argument('model_directory',type=Path)
    accept=sub.add_parser('accept');accept.add_argument('directory',type=Path);accept.add_argument('job_id')
    verify=sub.add_parser('check');verify.add_argument('dataset');verify.add_argument('directory',type=Path)
    args=parser.parse_args(argv)
    if args.action in ('prepare','model'):
        value=audit.capsule(root,args.dataset)
        output=root/'.factory/autonomous'/digest(value['binding'])/'model'
        if args.action=='prepare':
            result={'binding':value['binding'],'prompt_bytes':len(audit.prompt(value).encode()),
                    'model_directory':str(output.relative_to(root)),'model_started':False}
        else:
            from .audit_model_session import run
            result=run(root,args.dataset,output)
            with locked(root):
                path=safe_path(root,'candidates/'+args.dataset+'/record.json')
                record=execution.bounded_json(path)
                record['awaiting_operator']=False
                record['last_autonomous_audit']={'stage':'model','verdict':result['verdict'],
                    'directory':output.relative_to(root).as_posix(),'receipt_sha256':sha256(output/'session.json')}
                write_json(path,record)
    elif args.action=='worker-plan':result=worker_plan(root,args.model_directory)
    elif args.action=='check':result=check(root,args.dataset,args.directory)
    else:
        directory=args.directory.resolve()
        if not directory.is_relative_to(root.resolve()):raise ValueError('audit evidence must stay in repository')
        value,_,_,_=audit.model_evidence(root,directory/'model')
        staging=verify_staging(root,value['binding']['dataset'])
        collection=collect_evidence(root,args.job_id,directory/'worker',read_json(root/'config/local.json'))
        staging_path=directory/'worker/staging-readback.json'
        if staging_path.exists():
            if execution.bounded_json(staging_path)!=staging:raise ValueError('staging read-back changed')
        else:execution.write_json(staging_path,staging)
        try:
            verdict=check(root,value['binding']['dataset'],directory)
        except ValueError as exc:
            with locked(root):
                candidate=safe_path(root,'candidates/'+value['binding']['dataset']+'/record.json')
                record=execution.bounded_json(candidate)
                record['awaiting_operator']=False
                record['last_autonomous_audit']={'stage':'worker','verdict':'not_accepted',
                    'directory':directory.relative_to(root).as_posix(),
                    'collection_sha256':sha256(directory/'worker/collection.json'),'reason':str(exc)[:1000]}
                write_json(candidate,record)
            print(json.dumps({'ok':False,'verdict':'not_accepted','reason':str(exc)[:1000]}))
            return 1
        path=directory/'verdict.json'
        if path.exists():
            if execution.bounded_json(path)!=verdict:raise ValueError('existing audit verdict changed')
        else:execution.write_json(path,verdict)
        with locked(root):
            # Check again under the worker ledger lock before changing the queue.
            if check(root,value['binding']['dataset'],directory)!=verdict:raise ValueError('audit state changed')
            candidate=root/'candidates'/value['binding']['dataset']/'record.json'
            record=execution.bounded_json(candidate)
            if record.get('status')!='packaged':raise ValueError('candidate is not packaged')
            record.update(awaiting_operator=True,autonomous_audit={
                'directory':directory.relative_to(root).as_posix(),'sha256':sha256(path)})
            record['next_action']='Internal adversarial audit passed. Obtain operator-relayed independent audit and digest-bound publication approval.'
            write_json(candidate,record)
        result=verdict
    print(json.dumps(result,indent=2))
    return 0
