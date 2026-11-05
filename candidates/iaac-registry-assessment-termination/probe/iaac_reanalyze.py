#!/usr/bin/env python3
"""Final re-analysis of the 60-page IAAC sample (2026-11-05), entity-normalized.

Produces the record-grade numbers:
  - dated-line share per state (date anywhere in latestUpdates, entities normalized)
  - terminal-wording and outcome-wording shares
  - start -> terminal-event lag where both dates parse (sample scale)
  - undated-terminal pages: meta Modified Date availability
"""
import json, re, time, urllib.parse, urllib.request
from datetime import datetime
from collections import Counter

BASE = ("https://maps-cartes.services.geo.ca/server_serveur/rest/services/"
        "IAAC/assessment_inventory_en/MapServer/{L}/{action}")
UA = {"User-Agent": "Mozilla/5.0 (dataset-factory discovery probe)"}

def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

rows = []
for L in (0, 1, 2):
    offset = 0
    while True:
        q = urllib.parse.urlencode({
            "where": "1=1",
            "outFields": "project_id,project_state_en,start_date",
            "returnGeometry": "false", "resultOffset": offset,
            "resultRecordCount": 1000, "f": "json"})
        data = json.loads(get(BASE.format(L=L, action="query?") + q))
        feats = data.get("features", [])
        rows += [f["attributes"] for f in feats]
        if len(feats) < 1000:
            break
        offset += 1000
start_by_pid = {str(r["project_id"]): r.get("start_date") for r in rows}
print("inventory rows:", len(rows))

out = json.load(open("/opt/data/cache/scratch/ca-tick/iaac_pages_sample.json"))

DATE = re.compile(r"([A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})")
def fix(t):
    t = (t or "").replace("&nbsp;", " ").replace("&ndash;", "-")
    t = t.replace("&mdash;", "-").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip()

def parse_date(s):
    s = s.replace(".", "").replace(",", ",").strip()
    for fmt in ("%B %d, %Y", "%B %d %Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

TERM = re.compile(r"terminat|withdran|cancel|not be proceeding|dismiss", re.I)
OUTC_NEG = re.compile(r"not likely to cause significant adverse", re.I)
OUTC_POS = re.compile(r"\bis likely to cause significant adverse|\bare likely to cause significant adverse", re.I)

stats = {}
lags = []
for st in ("Terminated", "Completed", "In progress"):
    sub = [o for o in out if o["state"] == st and not o.get("error")]
    dated = term = 0
    for o in sub:
        t = fix(o.get("lu_text"))
        m = DATE.search(t)
        o["lu_date_norm"] = m.group(1) if m else None
        o["lu_dt"] = parse_date(m.group(1)) if m else None
        if m:
            dated += 1
        if TERM.search(t):
            term += 1
        if st == "Terminated" and o.get("lu_dt") and start_by_pid.get(o["project_id"]):
            sd = str(start_by_pid[o["project_id"]])
            try:
                sdt = datetime.strptime(sd[:10], "%Y-%m-%d")
                lags.append((o["project_id"], (o["lu_dt"] - sdt).days))
            except ValueError:
                pass
    stats[st] = (len(sub), dated, term)
    print(f"{st}: n={len(sub)} dated-line={dated} ({dated/len(sub):.0%}) terminal-wording={term} ({term/len(sub):.0%})")

# outcome wording among Completed (with entity-normalized text)
comp = [o for o in out if o["state"] == "Completed" and not o.get("error")]
neg = sum(1 for o in comp if OUTC_NEG.search(fix(o.get("lu_text"))))
pos = sum(1 for o in comp if OUTC_POS.search(fix(o.get("lu_text"))))
nod = sum(1 for o in comp if "determination" in fix(o.get("lu_text") or "").lower())
print(f"Completed: not-likely wording {neg}/{len(comp)}, likely wording {pos}/{len(comp)}, any-determination wording {nod}/{len(comp)}")

# lag distribution (sample scale; Terminated only here)
if lags:
    vals = sorted(v for _, v in lags)
    print(f"\nTerminated start->event lag (n={len(vals)}): min {vals[0]}, p25 {vals[len(vals)//4]}, "
          f"median {vals[len(vals)//2]}, p75 {vals[3*len(vals)//4]}, max {vals[-1]} days")
    print("  values:", vals)

# undated terminal pages: is meta Modified Date present as a fallback?
undated_term = [o for o in out if o["state"] == "Terminated" and not o.get("lu_dt") and TERM.search(fix(o.get("lu_text") or ""))]
print(f"\nTerminated pages, terminal wording but NO parsable date: {len(undated_term)}")
for o in undated_term[:8]:
    print(f"   {o['project_id']} ({o['start_year']}): meta_modified={o.get('meta_modified')} :: {fix(o['lu_text'])[:110]}")

# also: dated share among 2019+ subsample specifically (the task window)
for st in ("Terminated", "Completed"):
    recent = [o for o in out if o["state"] == st and (o.get("start_year") or 0) >= 2019]
    d = sum(1 for o in recent if o.get("lu_dt"))
    print(f"{st} start>=2019: dated {d}/{len(recent)}")

# cross-check state agreement at sample scale
print("meta_status == state:", sum(1 for o in out if o.get("meta_status") == o["state"]), "/", len(out))
