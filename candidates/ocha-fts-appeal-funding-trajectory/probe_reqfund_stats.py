# Probe: measure plan-year population, class balance and clustering from the
# publisher's own HDX distribution of FTS requirements/funding data.
import csv, json
from collections import Counter, defaultdict

rows = []
with open('/opt/data/cache/scratch/fts/reqfund_global.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        rows.append(r)

print('total rows:', len(rows))
print('columns:', list(rows[0].keys()))

# population structure
by_year = Counter(r['year'] for r in rows)
print('\nrows per year (all types):')
for y in sorted(by_year):
    print(f'  {y}: {by_year[y]}')

# type vocabulary and mix (provenance column)
print('\ntypeName mix:', Counter(r['typeName'] for r in rows))
print('requirements missing share:', sum(1 for r in rows if not r['requirements']), '/', len(rows))

# eligible rows: an appeal/plan with a stated requirement
elig = [r for r in rows if r['id'] and r['requirements']]
print('\neligible plan-year rows (id + requirements):', len(elig))
print('of which funding present:', sum(1 for r in elig if r['funding']))

# yearly eligible counts
ey = Counter(r['year'] for r in elig)
print('eligible per year:', dict(sorted(ey.items())))

# class balance at several coverage thresholds of requirements
for thr in (0.25, 0.4, 0.5, 0.6):
    pos = neg = 0
    for r in elig:
        req = float(r['requirements'] or 0)
        fund = float(r['funding'] or 0)
        if req <= 0:
            continue
        if fund / req >= thr:
            pos += 1
        else:
            neg += 1
    print(f'threshold {thr:.0%}: pos {pos} / neg {neg} (rate {pos/(pos+neg):.1%})' if pos+neg else f'threshold {thr}: no rows')

# distribution of percentFunded as published
pf = [float(r['percentFunded']) for r in elig if r['percentFunded']]
pf.sort()
import statistics
if pf:
    print('\npublished percentFunded: n=%d min=%.1f p25=%.1f median=%.1f p75=%.1f max=%.1f' % (
        len(pf), pf[0], pf[len(pf)//4], pf[len(pf)//2], pf[3*len(pf)//4], pf[-1]))

# clustering: distinct countries per window, repeat-country share
country_years = defaultdict(list)
for r in elig:
    country_years[r['countryCode']].append(r['year'])
print('\ndistinct countries with eligible plan-years:', len(country_years))
for lo, hi in [('2000','2009'), ('2010','2016'), ('2017','2019'), ('2020','2022'), ('2023','2026')]:
    c = [cc for cc, ys in country_years.items() if any(lo <= y <= hi for y in ys)]
    n = sum(1 for r in elig if lo <= r['year'] <= hi)
    print(f'window {lo}-{hi}: {n} plan-year rows, {len(c)} distinct countries')

# repeated-country share (same country appears in multiple years)
reps = Counter(len(ys) for ys in country_years.values())
print('appearances-per-country histogram:', dict(sorted(reps.items())))
