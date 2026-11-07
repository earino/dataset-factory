"""Compute the paper's defect tables from paper/evidence/defects.jsonl."""
import json, os, collections
HERE = os.path.dirname(__file__)
rows = [json.loads(l) for n in ('defects-data.jsonl', 'defects-pipeline.jsonl', 'defects-process.jsonl') for l in open(os.path.join(HERE, n))]
real = [r for r in rows if not r.get('false_alarm') and not r['umbrella'] and not r['triage']]
REACH = ['never-built', 'built-unqualified', 'qualified', 'private-staged', 'public']
TIERS = ['validity', 'legal', 'claims', 'pipeline', 'process', 'other']

def table(rs, rowkey, cols, title):
    print(f'\n### {title}\n')
    keys = [k for k, _ in collections.Counter(r[rowkey] for r in rs).most_common()]
    print('| ' + rowkey + ' | ' + ' | '.join(cols) + ' | total |')
    print('|' + '---|' * (len(cols) + 2))
    for k in keys:
        sub = [r for r in rs if r[rowkey] == k]
        print(f'| {k} | ' + ' | '.join(str(sum(1 for r in sub if c in (r["tier"], r["reached"]))) for c in cols) + f' | {len(sub)} |')

print(f'events: {len(rows)} merged; excluded false alarms {sum(1 for r in rows if r.get("false_alarm"))}, '
      f'umbrella {sum(r["umbrella"] for r in rows)}, licence triage {sum(r["triage"] for r in rows)}; analysed {len(real)}')
table(real, 'detected_by', TIERS, 'Detecting layer x defect tier (all analysed events)')
val = [r for r in real if r['tier'] == 'validity']
table(val, 'detected_by', REACH, f'Validity defects (n={len(val)}): detecting layer x furthest stage reached before detection')
leg = [r for r in real if r['tier'] in ('legal', 'claims')]
table(leg, 'detected_by', REACH, f'Licence + public-claim defects (n={len(leg)}): detecting layer x furthest stage reached')
esc = [r for r in real if r['reached'] in ('private-staged', 'public')]
print(f'\nEscapes past qualification (private-staged or public): {len(esc)} of {len(real)}; public: {sum(r["reached"]=="public" for r in real)}')
print('validity escapes to public:', sorted({r['candidate'] for r in val if r['reached']=='public'}))
print('\nfalse alarms by detector:', dict(collections.Counter(r['detected_by'] for r in rows if r.get('false_alarm'))))
print('human_involved share:', sum(1 for r in real if r.get('human_involved')), '/', len(real))
