# Probe 7: split-window counts on launch-vintage denominators (origRequirements).
import json
from collections import defaultdict, Counter

recs = [json.loads(l) for l in open('/opt/data/cache/scratch/fts/plan_orig_sweep.jsonl')]
print('plan-years swept:', len(recs), '| fetch errors:', sum(1 for r in recs if r.get('error')))

prim = [r for r in recs if r.get('n_country_rows') == 1 and (r.get('orig') or 0) > 0]
multi = [r for r in recs if r.get('n_country_rows', 0) > 1]
noorig = [r for r in recs if not (r.get('orig') or 0) and not r.get('error')]
print('primary (single-country, orig>0):', len(prim), '| multi-country regional:', len(multi), '| no orig req:', len(noorig))

def label(r, thr=0.5):
    return (r['csv_funding_sum'] / r['orig']) >= thr

for thr in (0.5, 0.4):
    print(f'\n=== threshold {thr:.0%} of ORIGINAL requirements, primary population ===')
    for lo, hi in [('2000', '2013'), ('2014', '2018'), ('2019', '2022'), ('2023', '2025')]:
        w = [r for r in prim if lo <= r['year'] <= hi]
        pos = sum(1 for r in w if label(r, thr))
        neg = len(w) - pos
        ctry = {c for r in w for c in r['countries']}
        print(f'window {lo}-{hi}: rows {len(w)}, pos {pos}, neg {neg} (rate {pos/len(w):.1%}), distinct countries {len(ctry)}')

# 2026 live-edge / censoring count
w26 = [r for r in prim if r['year'] == '2026']
print('\n2026 rows (live edge, excluded from scored windows):', len(w26))

# clustered independence: appearances per country series in primary population
sc = Counter(r['countries'][0] for r in prim)
print('distinct country series (primary):', len(sc), '| max appearances:', max(sc.values()))

# revised != orig share (vintage drift evidence)
rev_up = sum(1 for r in recs if (r.get('orig') or 0) > 0 and (r.get('revised') or 0) > (r.get('orig') or 0))
rev_dn = sum(1 for r in recs if (r.get('orig') or 0) > 0 and 0 < (r.get('revised') or 0) < (r.get('orig') or 0))
have = sum(1 for r in recs if (r.get('orig') or 0) > 0)
print(f'revisions: revised>orig {rev_up}/{have}, revised<orig {rev_dn}/{have}, unchanged {have-rev_up-rev_dn}/{have}')

# gho membership mix
print('isPartOfGHO mix (primary):', Counter(bool(r.get('gho')) for r in prim))
# type mix
print('type mix (primary):', Counter(r.get('type') for r in prim).most_common())
