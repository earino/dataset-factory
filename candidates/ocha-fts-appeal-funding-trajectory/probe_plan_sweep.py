# Probe 6: full sweep - origRequirements (launch vintage) for every eligible
# plan-year, from the publisher's plan endpoint. Compact output: one JSON line
# per plan-year. Computes primary-population split counts at >=50% of orig.
import csv, json, time, urllib.request
from collections import defaultdict

CACHE = '/opt/data/cache/scratch/fts/plan_orig_sweep.jsonl'
rows = []
with open('/opt/data/cache/scratch/fts/reqfund_global.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        rows.append(r)
elig = [r for r in rows if r['id'] and r['requirements']]

g = defaultdict(list)
for r in elig:
    g[(r['id'], r['year'])].append(r)

# resume support: what is already swept
done = set()
try:
    with open(CACHE) as f:
        for line in f:
            d = json.loads(line)
            done.add((str(d['plan']), str(d['year'])))
except FileNotFoundError:
    pass

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'scout-discovery-probe/1.0'})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                return None
            time.sleep(2)

out = open(CACHE, 'a')
n_fetched = n_err = 0
t0 = time.time()
for (pid, yr), rlist in sorted(g.items()):
    if (pid, yr) in done:
        continue
    d = fetch(f'https://api.hpc.tools/v2/public/plan/{pid}')
    if d is None:
        n_err += 1
        out.write(json.dumps({'plan': pid, 'year': yr, 'error': 'fetch-failed'}) + '\n')
        continue
    data = d.get('data', d)
    pv = data.get('planVersion') or {}
    rec = {
        'plan': pid, 'year': yr,
        'name': (pv.get('name') or '')[:70],
        'orig': data.get('origRequirements'),
        'revised': data.get('revisedRequirements'),
        'revisionState': data.get('revisionState'),
        'start': pv.get('startDate'), 'end': pv.get('endDate'),
        'gho': pv.get('isPartOfGHO'),
        'countries': sorted({r['countryCode'] for r in rlist}),
        'n_country_rows': len(rlist),
        'type': rlist[0].get('typeName'),
        'csv_funding_sum': sum(float(r['funding']) for r in rlist if r['funding']),
        'csv_req': rlist[0].get('requirements'),
    }
    out.write(json.dumps(rec) + '\n')
    n_fetched += 1
    if n_fetched % 100 == 0:
        out.flush()
        print(f'  {n_fetched} fetched, {n_err} errors, {time.time()-t0:.0f}s', flush=True)
    time.sleep(0.1)
out.close()
print(f'sweep done: {n_fetched} fetched, {n_err} errors, {time.time()-t0:.0f}s')
