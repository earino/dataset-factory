#!/usr/bin/env python3
"""Recheck a private staged package and freeze/score fixed and novel attacks on a worker."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from factory import adversarial_execution as execution
from factory import leakage_battery as battery
from factory import release_audit as audit
from factory.asset_integrity import safe_path, sha256
from factory.qualification_receipt import check as qualification_check
from factory.suitability import publication_check


def run(root, capsule_path, response_path, data, output):
    root,data,output=Path(root),Path(data),Path(output)
    value=execution.bounded_json(capsule_path)
    response=execution.bounded_json(response_path)
    proposal=audit.validate_response(value,response)
    binding=value['binding']
    if binding['implementation']!=audit.implementation(root):
        raise ValueError('worker audit implementation differs from model review')
    output.mkdir(parents=True,exist_ok=True)
    result={'version':audit.VERSION,'completed':False,'ok':False,
            'binding_digest':battery.digest(binding),'artifact_digest':binding['artifact_digest'],
            'implementation':binding['implementation'],
            'model_response_sha256':sha256(Path(response_path)),
            'proposal_sha256':battery.digest(proposal),'release_authorized':False}
    with tempfile.TemporaryDirectory(prefix='release-adversary-') as temporary:
        scratch=Path(temporary);package=scratch/'package';review=scratch/'review'
        package.mkdir();review.mkdir()
        for name,expected in binding['files'].items():
            dest=safe_path(package,name);dest.parent.mkdir(parents=True,exist_ok=True)
            if name.endswith('.csv'):
                source=safe_path(data,name)
                if sha256(source)!=expected:raise ValueError('fetched data differs from staged manifest: '+name)
                shutil.copyfile(source,dest)
            else:
                source=value['documents'][name]
                dest.write_text(source['text'])
                if source['sha256']!=expected:raise ValueError('capsule file differs from staged manifest')
            if sha256(dest)!=expected:raise ValueError('materialized package differs from staged bytes')
        for name,expected in binding['review_files'].items():
            dest=safe_path(review,name);dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(value['documents']['review/'+name]['text'])
            if sha256(dest)!=expected:raise ValueError('current review evidence changed')
        if execution.artifact_identity(package)!=binding['files']:
            raise ValueError('full staged package inventory differs')
        manifest=execution.bounded_json(package/'MANIFEST.json')
        problems,notes=audit.check_package(root,package,external_assets=False,review_root=review)
        problems+=qualification_check(package,manifest)
        problems+=publication_check(review,manifest)[0]
        result['deterministic_problems']=problems
        result['deterministic_notes']=notes
        if problems:
            result['completed']=True
            execution.write_json(output/'autonomous-audit.json',result)
            return result
        execution.write_json(scratch/'proposal.json',proposal)
        # Both prediction sets are sealed before scoring begins. The proposed
        # interpreter receives only feature columns; it cannot read any labels.
        execution.freeze(package,scratch/'novel',scratch/'proposal.json')
        battery.freeze(package,scratch/'fixed')
        novel=execution.score(package,scratch/'novel')
        fixed=battery.score(package,scratch/'fixed')
        if execution.artifact_identity(package)!=binding['files']:
            raise ValueError('staged package changed during audit')
        execution.write_json(output/'model-attacks.json',novel)
        execution.write_json(output/'battery.json',fixed)
        shutil.copyfile(scratch/'novel/freeze.json',output/'model-freeze.json')
        total=sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        for name,entry in fixed['detail_files'].items():
            source=safe_path(scratch/'fixed',name)
            if source.stat().st_size>=execution.LIMIT or sha256(source)!=entry['sha256']:
                raise ValueError('fixed probe detail receipt is inconsistent')
            total+=source.stat().st_size
            if total>19*1024*1024:raise ValueError('aggregate audit diagnostics exceed staging allowance')
            shutil.copyfile(source,safe_path(output,name))
        result.update(completed=True,unchanged=True,fixed_battery_passed=fixed['ok'],
            fixed_battery_sha256=sha256(output/'battery.json'),
            model_attacks_sha256=sha256(output/'model-attacks.json'),
            model_freeze_sha256=sha256(output/'model-freeze.json'),
            model_verdict=response['verdict'],requires_semantic_review=novel['requires_semantic_review'],
            ok=(fixed['ok'] and response['verdict']=='pass' and not novel['requires_semantic_review']))
        execution.write_json(output/'autonomous-audit.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capsule',type=Path,default=ROOT/'capsule.json')
    parser.add_argument('--response',type=Path,default=ROOT/'response.json')
    parser.add_argument('--data',type=Path,default=Path('/data'))
    parser.add_argument('--output',type=Path,default=Path('/output'))
    args=parser.parse_args()
    try:
        result=run(ROOT,args.capsule,args.response,args.data,args.output)
        print(json.dumps({'completed':result['completed'],'ok':result['ok'],'release_authorized':False}))
        return 0 if result['ok'] else 1
    except Exception as exc:
        args.output.mkdir(parents=True,exist_ok=True)
        execution.write_json(args.output/'incomplete.json',{'completed':False,'ok':False,
                             'error_type':type(exc).__name__,'release_authorized':False})
        print('Autonomous audit incomplete: '+type(exc).__name__,file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
