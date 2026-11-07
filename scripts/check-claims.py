#!/usr/bin/env python3
"""Measure on the worker; verify bound package claims without fetching data locally."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factory.claim_facts import measure
from factory.claim_checks import inspect
from factory.claim_contract import compute, validate, qualification_binding


def save(path,value):
    payload=(json.dumps(value,sort_keys=True,indent=1,allow_nan=False)+'\n').encode()
    if len(payload)>=256*1024:
        raise ValueError('claims report exceeds collection limit; inspection incomplete')
    path.write_bytes(payload)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',type=Path)
    parser.add_argument('--measure',action='store_true',help='Full-row worker measurement; requires qualification')
    parser.add_argument('--historical',action='store_true',help='Read-only diagnostic audit; never produces release clearance')
    parser.add_argument('--qualification',type=Path)
    parser.add_argument('--evidence-dir',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--facts',type=Path)
    parser.add_argument('--external-assets',action='store_true')
    args=parser.parse_args()
    try:
        if args.measure:
            if args.output is None or args.output.resolve().is_relative_to(args.package.resolve()):
                raise ValueError('write new measurement outside the artifact; never alter historical inputs')
            if args.output.exists():
                raise ValueError('measurement output already exists; preserve it')
            if args.historical:
                qualification_binding(args.package,args.qualification,historical=True)
                facts=measure(args.package)
                result=inspect(args.package,facts)
                facts['historical_only']=True
                save(args.output,{'facts':facts,'inspection':result,'release_clearance':False})
                print(json.dumps({'ok':result['ok'],'historical_only':True,'report':str(args.output)}))
                return 0 if result['ok'] else 1
            facts=compute(args.package,evidence_root=args.evidence_dir,qualification=args.qualification)
            save(args.output,facts)
            print(json.dumps({'ok':facts['ok'],'report':str(args.output)}))
            return 0 if facts['ok'] else 1
        facts=json.loads((args.facts or args.package/'claims-facts.json').read_text())
        result=validate(args.package,facts,external_assets=args.external_assets)
        print(json.dumps(result,sort_keys=True,indent=1))
        return 0 if result['ok'] else 1
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
