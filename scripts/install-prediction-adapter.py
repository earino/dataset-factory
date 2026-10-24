#!/usr/bin/env python3
"""Create a separate execution clone; never modify the read-only harness checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    a=p.parse_args(); source=a.source.resolve(); dest=a.destination.resolve()
    if dest.exists() or dest==source or dest.is_relative_to(source):
        p.error('destination must be a new path outside the read-only source')
    if not (source/'bench/score_holdout.py').is_file():p.error('existing harness scorer not found')
    subprocess.run(['git','clone','--local','--no-hardlinks',str(source),str(dest)],check=True)
    original=dest/'bench/score_holdout.py'
    before=hashlib.sha256(original.read_bytes()).hexdigest()
    content=(ROOT/'adapters/score_holdout.py').read_bytes(); original.write_bytes(content)
    receipt={'protocol':'chronological-row-stream-v1','source':str(source),
             'source_commit':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),
             'original_scorer_sha256':before,'adapter_sha256':hashlib.sha256(content).hexdigest(),
             'deployment_status':'installed; worker smoke required before benchmark use'}
    (dest/'.factory-execution-copy.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
