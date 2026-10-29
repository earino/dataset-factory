# Probe 3: resolve (a) CSV grain for multiyear plans (funding per year vs total),
# (b) requirements vintage: CSV requirements vs plan-endpoint orig/revised,
# bounded to the 2016 and 2023 eligible cohorts.
import csv, json, time, urllib.request

rows = []
with open('/opt/data/cache/scratch/fts/reqfund_global.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        rows.append(r)
elig = [r for r in rows if r['id'] and r['requirements']]

by_id_year = {}
for r in elig:
    by_id_year.setdefault(r['id'], {})[r['year']] = r

# (a) multiyear-plan grain: print all CSV rows for plans appearing in >1 year
multi = {pid: y for pid, y in by_id_year.items() if len(y) > 1}
print('plans with >1 year row in CSV:', len(multi))
shown = 0
for pid, ymap in sorted(multi.items()):
    if shown >= 4:
        break
    print(f'  plan {pid} years {sorted(ymap)}:')
    for y in sorted(ymap):
        r = ymap[y]
        print(f'    {y}: req {r["requirements"]} fund {r["funding"]} pctFunded {r["percentFunded"]} name {r["name"][:40]} start {r["startDate"]} end {r["endDate"]}')
    shown += 1

# Yemen 1116 CSV rows vs measured API total (1,774,327,599 for usage-year 2023)
print('\nYemen plan 1116 CSV rows:', [(y, r['requirements'], r['funding'], r['percentFunded']) for y, r in by_id_year.get('1116', {}).items()])

def fetch(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'scout-discovery-probe/1.0'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)

# (b) requirements vintage on bounded cohorts
for cohort_year in ('2016', '2023'):
    ids = sorted({r['id'] for r in elig if r['year'] == cohort_year})
    print(f'\ncohort {cohort_year}: {len(ids)} plan ids')
    orig_eq_rev = orig_lt_rev = csv_matches_orig = csv_matches_rev = neither = 0
    reqs = []
    for pid in ids:
        try:
            d = fetch(f'https://api.hpc.tools/v2/public/plan/{pid}')['data']
        except Exception as e:
            print('  fetch err', pid, e)
            continue
        o, v = d.get('origRequirements'), d.get('revisedRequirements')
        csv_req = by_id_year[pid][cohort_year]['requirements']
        if o is not None and v is not None:
            if o == v:
                orig_eq_rev += 1
            elif o < v:
                orig_lt_rev += 1
            if o is not None and csv_req and abs(float(csv_req) - o) < 1:
                csv_matches_orig += 1
            elif v is not None and csv_req and abs(float(csv_req) - v) < 1:
                csv_matches_rev += 1
            else:
                neither += 1
                reqs.append((pid, o, v, csv_req))
        time.sleep(0.15)
    print(f'  orig==revised: {orig_eq_rev} | orig<revised: {orig_lt_rev}')
    print(f'  CSV req == orig: {csv_matches_orig} | == revised: {csv_matches_rev} | neither: {neither}')
    for t in reqs[:5]:
        print('   mismatch sample:', t)
