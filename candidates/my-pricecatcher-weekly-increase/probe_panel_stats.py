"""PriceCatcher panel probe: 10% premise subsample (premise_code % 10 == 0).

Executed during the 2026-10-21 discovery session from the repository's scratch
directory (.factory/probe), with two full month files downloaded there as
bounded samples (pc_2026-08.csv, 50,122,871 B; pc_2026-09.csv, 45,137,790 B;
both deleted afterwards and never committed) plus lookup_item.csv. Outputs the
row counts, duplicate check, panel dimensions and the weekly modal-price
transition statistics recorded in this candidate's record.json and notes.md.

The full-panel version of this probe OOMs on the 1.9 GiB coordinator; the 10%
premise subsample measures the same base rates at a tenth of the memory. A
worker aggregates the full panel trivially during construction.

Usage: place the two month CSVs next to this file and run
    python3 probe_panel_stats.py
"""
import csv, json, os
from collections import Counter, defaultdict

def isoweek(d):
    import datetime
    y, m, dd = map(int, d.split('-'))
    return datetime.date(y, m, dd).isocalendar()[1]

PW = defaultdict(list)
dates = set()
rowcount = Counter()
dup = 0
seen = set()
for month in ('2026-08', '2026-09'):
    with open(f'pc_{month}.csv', newline='') as f:
        r = csv.reader(f)
        assert next(r) == ['date', 'premise_code', 'item_code', 'price']
        for d, p, i, pr in r:
            rowcount[month] += 1
            dates.add(d)
            k = (d, p, i)
            if k in seen:
                dup += 1
            seen.add(k)
            if int(p) % 10 == 0:
                PW[(p, i, d[:4] + 'W' + str(isoweek(d)))].append(float(pr))
print('rows per month:', dict(rowcount), 'dup(date,premise,item):', dup)
print('subsampled pair-weeks:', len(PW), 'kept rows:', sum(len(v) for v in PW.values()))

stat = {}
for k, v in PW.items():
    stat[k] = (Counter(v).most_common(1)[0][0], len(v))
weeks = sorted({k[2] for k in stat})
days_in = Counter(d[:4] + 'W' + str(isoweek(d)) for d in dates)

trans = []
for a, b in zip(weeks, weeks[1:]):
    if days_in[a] < 6 or days_in[b] < 6:
        continue
    A = {(k[0], k[1]): v for k, v in stat.items() if k[2] == a}
    B = {(k[0], k[1]): v for k, v in stat.items() if k[2] == b}
    n = inc = dec = 0
    inc_by_item = Counter()
    for key in set(A) & set(B):
        if A[key][1] < 3 or B[key][1] < 3:
            continue
        ma, mb = A[key][0], B[key][0]
        n += 1
        if mb > ma:
            inc += 1
            inc_by_item[key[1]] += 1
        elif mb < ma:
            dec += 1
    top10 = sum(c for _, c in inc_by_item.most_common(10))
    row = {'from': a, 'to': b, 'pairs': n, 'inc': inc, 'inc_rate': round(inc / n, 4),
           'dec': dec, 'dec_rate': round(dec / n, 4),
           'flat_rate': round((n - inc - dec) / n, 4),
           'items_with_inc': len(inc_by_item),
           'top10_share': round(top10 / inc, 3)}
    trans.append(row)
    print(json.dumps(row))

premises = {k[0] for k in stat}; items = {k[1] for k in stat}
print('subsample premises:', len(premises), 'subsample items:', len(items))
for m in ('2026-08', '2026-09'):
    print(m, 'bytes:', os.path.getsize(f'pc_{m}.csv'),
          'mean_row_bytes:', round(os.path.getsize(f'pc_{m}.csv') / rowcount[m], 2))
json.dump({'rows': dict(rowcount), 'dup': dup, 'transitions': trans,
           'panel_subsample': {'premises': len(premises), 'items': len(items)},
           'subsample_fraction': 'premise_code % 10 == 0'},
          open('pc_probe_results.json', 'w'), indent=1)
print('saved pc_probe_results.json')
