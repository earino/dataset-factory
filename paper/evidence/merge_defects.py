"""Merge per-chunk defect extractions into one normalised table.

Inputs: raw/defects_[1-5].jsonl (STATE.md chunks) and raw/defects_audits.jsonl,
from the directory given as argv[1] (paper/evidence/raw). Brief: raw/EXTRACTION-BRIEF.md. Output: paper/evidence/defects.jsonl.
Merges and tiers are explicit below so every count can be traced and changed.
"""
import json, glob, sys, os, collections

SRC = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'defects.jsonl')

TIER = {
    'leakage': 'validity', 'prediction-timing': 'validity', 'label-definition': 'validity',
    'split-temporal': 'validity', 'units-frame': 'validity',
    'licence': 'legal', 'editorial-claim': 'claims',
    'source-format': 'pipeline', 'runner-contract': 'pipeline', 'infrastructure': 'pipeline',
    'agent-process': 'process', 'budget-ops': 'process', 'credential-security': 'process',
    'other': 'other',
}
# Same defect extracted from more than one chunk: secondary ids fold into the primary.
MERGE = {
    '5:60': '3:52', '5:61': '3:53',      # chilecompra selection / horizon
    '5:86': '3:25',                      # ec-merger NACE vintage
    '5:4': '4:104',                      # nhs-ae publication lag
    '3:5': '2:53',                       # ocha-fts country history
    '2:64': '3:4',                       # ns-bwa cumulative history
    '5:10': '2:21',                      # cpcb licence read from republisher
    '5:77': '3:49',                      # noaa day definition
}
# Umbrella records that summarise per-candidate events counted separately.
UMBRELLA = {'3:48'}

rows = []
for f in sorted(glob.glob(os.path.join(SRC, 'defects_*.jsonl'))):
    tag = os.path.basename(f)[8:-6]          # '1'..'5' or 'audits'
    for i, line in enumerate(open(f), 1):
        if line.strip():
            d = json.loads(line)
            d['id'] = f'{tag}:{i}'
            rows.append(d)

by_id = {r['id']: r for r in rows}
for sec, pri in MERGE.items():
    if sec in by_id and pri in by_id:
        by_id[pri].setdefault('merged_from', []).append(sec)
        by_id[pri]['evidence'] = list(dict.fromkeys(by_id[pri]['evidence'] + by_id[sec]['evidence']))
        by_id[sec]['merged_into'] = pri

# The audits extraction overlaps the STATE.md extractions. An audits event folds into a
# STATE.md event with the same candidate, defect class and detecting layer.
state_keys = {}
for r in rows:
    if not r['id'].startswith('audits:') and 'merged_into' not in r:
        state_keys.setdefault((r['candidate'], r['defect_class'], r['detected_by']), r)
for r in rows:
    if r['id'].startswith('audits:'):
        hit = state_keys.get((r['candidate'], r['defect_class'], r['detected_by']))
        if hit:
            hit.setdefault('merged_from', []).append(r['id'])
            hit['evidence'] = list(dict.fromkeys(hit['evidence'] + r['evidence']))
            r['merged_into'] = hit['id']

# Keep the published table under the repository's 256 KiB report limit.
for r in rows:
    r['evidence'] = [e[:140] for e in r['evidence']][:3]

out = []
for r in rows:
    if 'merged_into' in r:
        continue
    r['tier'] = TIER.get(r['defect_class'], 'other')
    r['umbrella'] = r['id'] in UMBRELLA
    # Routine licence vetting at discovery is triage, not a defect the system made.
    r['triage'] = (r['defect_class'] == 'licence' and r['reached'] == 'never-built'
                   and r['outcome'] in ('dropped', 'parked') and r['detected_by'] == 'agent-self-check')
    out.append(r)

# Two files, each under the repository's 256 KiB report limit.
PARTS = {'defects-data.jsonl': ('validity', 'legal', 'claims'),
         'defects-pipeline.jsonl': ('pipeline',),
         'defects-process.jsonl': ('process', 'other')}
for name, tiers in PARTS.items():
    path = os.path.join(os.path.dirname(OUT), name)
    part = [r for r in out if r['tier'] in tiers]
    with open(path, 'w') as fh:
        for r in part:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'{name}: {len(part)} events, {os.path.getsize(path)} bytes')
print(f'{len(rows)} extracted, {len(rows)-len(out)} merged, {len(out)} written')
