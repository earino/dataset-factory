#!/usr/bin/env python3
"""IAAC registry page stratified sample (2026-11-05 discovery tick).

Answers the iaac-registry-assessment-termination next-action items:
  (a) share of pages exposing a dated, machine-parseable terminal event line
  (b) per-page fetch cost (bytes, seconds) -> total estimate for 6,600 pages
  (c) determination-outcome wording mix among Completed pages
  (d) bulk export check is done separately (listing page fetch + grep)

Stratified sample: 24 Terminated + 24 Completed + 12 In progress,
spread over start-years with a 2019+ emphasis. ~60 requests, anonymous.
Results printed as aggregates; raw per-page results saved to iaac_pages_sample.json.
"""
import json, random, re, time, urllib.parse, urllib.request
from collections import Counter

BASE = ("https://maps-cartes.services.geo.ca/server_serveur/rest/services/"
        "IAAC/assessment_inventory_en/MapServer/{L}/{action}")
UA = {"User-Agent": "Mozilla/5.0 (dataset-factory discovery probe)"}

def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# --- 1. full attribute fetch (measured 2026-10-30: 9 requests, 1 MB, 6.6 s) ---
t0, reqs, nbytes, rows = time.time(), 0, 0, []
for L, state in ((0, "Completed"), (1, "In progress"), (2, "Terminated")):
    offset = 0
    while True:
        q = urllib.parse.urlencode({
            "where": "1=1",
            "outFields": "project_id,project_cat_en,province_codes,start_date,project_state_en",
            "returnGeometry": "false",
            "resultOffset": offset,
            "resultRecordCount": 1000,
            "f": "json",
        })
        data = json.loads(get(BASE.format(L=L, action="query?") + q))
        reqs += 1; nbytes += len(json.dumps(data))
        feats = data.get("features", [])
        rows += [f["attributes"] for f in feats]
        if len(feats) < 1000 or data.get("exceededTransferLimit") is not True:
            if len(feats) < 1000:
                break
        offset += 1000
        if not feats:
            break
print(f"inventory: {len(rows)} rows, {reqs} requests, {nbytes} bytes, {time.time()-t0:.2f}s")

for r in rows:
    d = str(r.get("start_date") or "")
    r["start_year"] = int(d[:4]) if d[:4].isdigit() else None

# --- 2. stratified sample ---
random.seed(20261105)
by_state = {}
for r in rows:
    by_state.setdefault(r["project_state_en"], []).append(r)

def strat(pool, n, recent_bias=True):
    """Spread over start-years, biased to 2019+ when asked and available."""
    recent = [r for r in pool if (r["start_year"] or 0) >= 2019]
    older = [r for r in pool if (r["start_year"] or 0) < 2019]
    random.shuffle(recent); random.shuffle(older)
    take_recent = min(len(recent), max(1, int(n * 0.6))) if recent_bias else 0
    return recent[:take_recent] + older[: n - take_recent]

sample = []
sample += strat(by_state.get("Terminated", []), 24)
sample += strat(by_state.get("Completed", []), 24)
sample += strat(by_state.get("In progress", []), 12)
print(f"sample: {len(sample)} pages "
      f"(Terminated {sum(1 for s in sample if s['project_state_en']=='Terminated')}, "
      f"Completed {sum(1 for s in sample if s['project_state_en']=='Completed')}, "
      f"In progress {sum(1 for s in sample if s['project_state_en']=='In progress')})")
year_mix = sorted(Counter(s["start_year"] for s in sample).items(),
                  key=lambda x: (x[0] is None, x[0] or 0))
print("sample start-year mix:", year_mix)

# --- 3. per-page fetch + parse ---
DATE_RE = re.compile(r"^([A-Z][a-z]+ \d{1,2}, \d{4})\s*-\s*(.*)$")
out, cost = [], []
for i, s in enumerate(sample):
    pid = str(s["project_id"])
    url = f"https://iaac-aeic.gc.ca/050/evaluations/proj/{pid}?culture=en-CA"
    t1 = time.time()
    try:
        html = get(url, timeout=90).decode("utf-8", errors="replace")
    except Exception as e:
        out.append({"project_id": pid, "state": s["project_state_en"], "error": repr(e)})
        continue
    el = time.time() - t1
    cost.append((len(html), el))
    meta_status = re.search(r'<meta name="Status" content="([^"]*)"', html)
    meta_mod = re.search(r'<meta name="Modified Date" content="([^"]*)"', html)
    lu = re.search(r'<div id="latestUpdates">(.*?)</div>', html, re.S)
    lu_text = re.sub(r"<[^>]+>", " ", lu.group(1)).strip() if lu else None
    lu_text = re.sub(r"\s+", " ", lu_text) if lu_text else None
    m = DATE_RE.match(lu_text or "")
    out.append({
        "project_id": pid,
        "state": s["project_state_en"],
        "start_year": s["start_year"],
        "meta_status": meta_status.group(1) if meta_status else None,
        "meta_modified": meta_mod.group(1) if meta_mod else None,
        "lu_date": m.group(1) if m else None,
        "lu_text": lu_text,
        "bytes": len(html), "seconds": round(el, 2),
    })

json.dump(out, open("/opt/data/cache/scratch/ca-tick/iaac_pages_sample.json", "w"), indent=1)

# --- 4. aggregates ---
print(f"\npages fetched: {len(out)} (errors: {sum(1 for o in out if o.get('error'))})")
b = [c[0] for c in cost]; e = [c[1] for c in cost]
print(f"per-page cost: mean bytes {sum(b)/len(b):,.0f}, mean s {sum(e)/len(e):.2f}")
print(f"6,600-page ESTIMATE: {sum(b)/len(b)*6600/1e9:.2f} GB, {sum(e)/len(e)*6600/3600:.2f} h serial")

dated = [o for o in out if o.get("lu_date")]
print(f"\ndated latestUpdates line: {len(dated)}/{len(out)}")
for st in ("Terminated", "Completed", "In progress"):
    sub = [o for o in out if o["state"] == st and not o.get("error")]
    dsub = [o for o in sub if o.get("lu_date")]
    term = [o for o in sub if o.get("lu_text") and re.search(
        r"terminat|withdran|determination|decision|dismiss", o["lu_text"], re.I)]
    print(f"  {st}: dated line {len(dsub)}/{len(sub)}; terminal-ish wording {len(term)}/{len(sub)}")

# wording mix among Completed
print("\nCompleted outcome wording mix:")
mix = Counter()
for o in out:
    if o["state"] == "Completed" and o.get("lu_text"):
        t = o["lu_text"].lower()
        if "not likely to cause significant adverse" in t:
            mix["not likely to cause significant adverse environmental effects"] += 1
        elif "likely to cause significant adverse" in t:
            mix["LIKELY to cause significant adverse environmental effects"] += 1
        elif "determination" in t or "decision" in t:
            mix["determination/decision, other wording"] += 1
        else:
            mix["other"] += 1
            print("   other wording:", o["project_id"], "->", o["lu_text"][:140])
print(dict(mix))

print("\nmeta Status == inventory state:",
      sum(1 for o in out if o.get("meta_status") == o["state"]), "/", len(out))
mism = [o for o in out if o.get("meta_status") and o["meta_status"] != o["state"]]
for o in mism[:5]:
    print("   mismatch:", o["project_id"], o["state"], "vs meta", o["meta_status"])

print("\nTerminated wording examples:")
for o in [o for o in out if o["state"] == "Terminated" and o.get("lu_text")][:6]:
    print(f"   {o['project_id']} ({o['start_year']}): {o['lu_text'][:150]}")
