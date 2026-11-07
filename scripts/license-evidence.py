#!/usr/bin/env python3
"""Capture readable source terms, import native browser evidence, and generate terms."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factory.license_evidence import fetch, import_browser, verify, canonical
from factory.license_contract import build, validate, check_card


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for action in ('fetch','import-browser'):
        p=commands.add_parser(action);p.add_argument('source');p.add_argument('output')
        p.add_argument('--owner-host',action='append',required=True)
    p=commands.add_parser('verify-capture');p.add_argument('directory')
    p=commands.add_parser('generate');p.add_argument('package');p.add_argument('--card-template',required=True)
    p=commands.add_parser('check');p.add_argument('package')
    args=parser.parse_args(argv)
    try:
        if args.command in ('fetch','import-browser'):
            fn=fetch if args.command=='fetch' else import_browser
            result=fn(args.source,args.output,owner_hosts=args.owner_host)['inspection']
        elif args.command=='verify-capture':
            result=verify(args.directory)['inspection']
        elif args.command=='generate':
            package=Path(args.package);generated=build(package,fresh=True)
            text=Path(args.card_template).read_text()
            card=check_card(text,generated['card'],template=True)
            # First validate every output, then use exclusive creation: no frozen overwrite.
            outputs={'LICENSE.md':generated['license'].encode(),
                     'license-receipt.json':canonical(generated['receipt'])+b'\n',
                     'card.md':card.encode()}
            if any((package/n).exists() for n in outputs):
                raise ValueError('generated outputs already exist; use a fresh package preparation directory')
            for name,body in outputs.items():
                with (package/name).open('xb') as handle:handle.write(body)
            result={'ok':True,'generated':sorted(outputs)}
        else:
            package=Path(args.package)
            manifest_path=package/'MANIFEST.json'
            manifest=json.loads(manifest_path.read_text()) if manifest_path.is_file() else None
            validate(package,manifest=manifest)
            result={'ok':True}
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        result={'ok':False,'problems':[str(exc)]}
    print(json.dumps(result,indent=2))
    return 0 if result['ok'] else 1


if __name__=='__main__':
    raise SystemExit(main())
