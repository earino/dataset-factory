#!/usr/bin/env python3
"""Offline, immutable code/document archives for worker comparison of frozen releases.

No dataset rows, network calls, reconstruction, historical edits or executable
imports. Archive members must match the pre-existing frozen editorial registry.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from factory.artifact_scrub import sha256


def safe_path(root, name):
    if not isinstance(name,str) or not name or name.startswith('/') or any(
            part in ('','.','..') for part in name.split('/')):
        raise ValueError('unsafe audit evidence path')
    path=root/name
    for parent in (path,*path.parents):
        if parent.is_symlink():raise ValueError('audit evidence path is a symlink')
        if parent==root:break
    return path


def prepare(root, output):
    root=Path(root);output=Path(output)
    registry_path=root/'config/frozen-releases.json'
    registry=json.loads(registry_path.read_text())
    output.mkdir(parents=True,exist_ok=False)
    (output/'audit-evidence-owner.json').write_text(json.dumps({
        'owner':'dataset-factory/prepare-frozen-audit','version':1})+'\n')
    inventory={'version':1,'registry_sha256':sha256(registry_path),'datasets':[]}
    for entry in registry['releases']:
        dataset=entry['dataset'];package=safe_path(root/'release',dataset)
        if sha256(safe_path(package,'MANIFEST.json'))!=entry['manifest_sha256']:
            raise ValueError('frozen manifest changed: '+dataset)
        archive_path=safe_path(output,dataset+'.tar');members=[]
        with tarfile.open(archive_path,'x:') as archive:
            for name,expected in sorted(entry['editorial_files'].items()):
                path=safe_path(package,name)
                if path.suffix.lower() in ('.csv','.tsv','.parquet','.arrow','.npy','.npz'):
                    raise ValueError('bulk data is never a coordinator audit input: '+name)
                if path.stat().st_size>=256*1024:
                    raise ValueError('frozen code/document exceeds bounded coordinator input: '+name)
                data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
                if digest!=expected:
                    raise ValueError('frozen file changed: '+dataset+'/'+name)
                member=tarfile.TarInfo('package/'+name);member.size=len(data);member.mode=0o600
                archive.addfile(member,io.BytesIO(data))
                members.append({'member':member.name,'path':member.name,'size':len(data),'sha256':digest})
        if archive_path.stat().st_size>2*1024*1024:
            raise ValueError('compact audit archive exceeds two MiB: '+dataset)
        inventory['datasets'].append({'dataset':dataset,'release_tag':entry['release_tag'],
            'artifact_version':entry['artifact_version'],'manifest_sha256':entry['manifest_sha256'],
            'archive':archive_path.name,'size':archive_path.stat().st_size,
            'sha256':sha256(archive_path),'members':members})
    text=json.dumps(inventory,indent=2)+'\n'
    if len(text.encode())>=256*1024:
        raise ValueError('archive inventory exceeds compact report limit')
    (output/'inventory.json').write_text(text)
    return inventory


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    args=parser.parse_args();result=prepare(ROOT,args.output)
    print(json.dumps({'datasets':len(result['datasets']),
                      'archive_bytes':sum(d['size'] for d in result['datasets']),
                      'inventory':str(args.output/'inventory.json'),'bulk_data_read':False}))


if __name__=='__main__':main()
