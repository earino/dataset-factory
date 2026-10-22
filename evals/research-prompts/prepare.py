#!/usr/bin/env python3
"""Offline preparation of paired decision requests; never calls a model or a worker.

Each arm embeds versioned public operating instructions. Private Hermes context is
not exported. Grading criteria remain in cases.json, outside submitted requests.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '1cc921b'
COMMON = ['AGENTS.md', 'PROJECT.md', 'docs/OPERATIONS.md']
SKILLS = [f'skills/dataset-{name}/SKILL.md' for name in ('discovery','qualification','release')]
BRIEFS = {'discovery':'docs/discovery-session-prompt.md',
          'advancement':'docs/research-session-prompt.md',
          'watcher':'docs/worker-watch-prompt.md'}


def source(revision, name):
    if revision == 'working-tree':
        return (ROOT / name).read_text()
    return subprocess.check_output(['git','show',f'{revision}:{name}'],cwd=ROOT,text=True)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True, help='exact revised commit')
    parser.add_argument('--out',type=Path,required=True,help='new directory; existing paths refused')
    parser.add_argument('--partition',choices=('development','reserved'),default='development')
    args=parser.parse_args()
    revision=subprocess.check_output(['git','rev-parse',f'{args.revision}^{{commit}}'],cwd=ROOT,text=True).strip()
    baseline=subprocess.check_output(['git','rev-parse',f'{BASELINE}^{{commit}}'],cwd=ROOT,text=True).strip()
    cases=json.loads((ROOT/'evals/research-prompts/cases.json').read_text())['cases']
    args.out.mkdir(parents=True, exist_ok=False)
    manifest={'schema_version':1,'baseline':baseline,'revised':revision,
              'partition':args.partition,'requests':[]}
    for case in cases:
        if case['partition']!=args.partition: continue
        for arm,commit in (('baseline',baseline),('revised',revision)):
            paths=COMMON.copy()
            # Match role-specific eager loading. This is part of the bundle treatment,
            # not an isolated estimate of the effect of rewriting one brief.
            if arm == 'baseline':
                if case['role'] != 'watcher': paths += SKILLS
            elif case['role'] == 'discovery':
                paths += SKILLS[:1]
            else:
                paths += SKILLS[1:]
            sections=[]; identities={}
            for name in paths:
                text=source(commit,name); identities[name]=digest(text)
                sections.append(f'--- BEGIN {name} ---\n{text}\n--- END {name} ---')
            name=BRIEFS[case['role']]
            if case['role']=='watcher' and arm=='baseline':
                brief=(ROOT/'evals/research-prompts/baseline-worker-watch.md').read_text()
                origin='scheduler snapshot, PR #10 comment 6350828810'
            else:
                brief=source(commit,name); origin=name
            identities[origin]=digest(brief)
            brief=brief.replace('{{SESSION_CONTEXT}}',
                'Decision exercise: use the time/budget facts supplied in the case. '
                'No real worker or publication action is being requested.').replace('{{DATE}}','2026-10-22')
            prompt=('Use the following operating instructions for your assigned role. '
                    'Then decide the supplied case. This is a no-tool decision exercise; '
                    'state the actions you would take, do not execute them.\n\n'
                    +'\n\n'.join(sections)+'\n\n--- SESSION BRIEF ---\n'+brief
                    +'\n\n--- CASE EVIDENCE ---\n'+case['input']
                    +'\n\nAnswer in at most 600 words: decision; supporting evidence; uncertainty '
                    'and next discriminating check; ordered actions and stopping condition; '
                    'concise operator report. All case evidence is supplied; do not invent findings.\n')
            filename=f"{case['id']}--{arm}.txt"
            (args.out/filename).write_text(prompt)
            manifest['requests'].append({'case_id':case['id'],'role':case['role'],'arm':arm,
                'file':filename,'commit':commit,'sha256':digest(prompt),
                'bytes':len(prompt.encode()),'source_sha256':identities})
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'requests':len(manifest['requests']),'revision':revision,
                      'max_bytes':max(x['bytes'] for x in manifest['requests']),
                      'out':str(args.out)},indent=2))


if __name__=='__main__': main()
