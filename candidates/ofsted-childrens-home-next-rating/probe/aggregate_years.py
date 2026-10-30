# Cross-file dedupe by inspection number; per-calendar-year counts of children's-home FULL
# inspections, graded outcomes and positives (below Good), plus distinct homes (clustered count).
# In-memory only; prints aggregates. Discovery evidence for ofsted-childrens-home-next-rating.
import csv, io, json, re, time, zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from urllib.request import urlopen, Request

TNS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
XNS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
M = "https://assets.publishing.service.gov.uk/media"

ASSETS = {
    "q2016Q4": f"{M}/5d41521540f0b60aa15f8868/Management_information_-_children_s_homes_-_31_December_2016__final_.csv",
    "q2017Q1": f"{M}/5d415215e5274a0a1caaa7bf/Management_information_-_children_s_homes_-_31_March_2017.csv",
    "q2017Q2": f"{M}/5d415214ed915d09d689dec0/Management_information_-_children_s_homes_-_30_June_2017.csv",
    "q2017Q3": f"{M}/5d415214e5274a0a2327fbd5/Management_information_-_children_s_homes_-_30_Sept_2017.csv",
    "q2017Q4": f"{M}/5d41521540f0b60a886d4e91/Management_information_-_children_s_homes_-_31_December_2017.csv",
    "q2018Q1": f"{M}/5d415215ed915d09d8945d90/Management_information_-_children_s_homes_-_31_March_2018.csv",
    "q2018Q2": f"{M}/5d41521440f0b60a82ce0a5b/Management_information_-_children_s_homes_-_30_June_2018.csv",
    "q2018Q3": f"{M}/5d415215ed915d09e2c9d57a/Management_information_-_children_s_homes_-_30_September_2018.csv",
    "q2018Q4": f"{M}/5d41a414e5274a0a0f2f2861/Management_information_-_children_s_homes_-_31_December_2018__2_.csv",
    "q2019Q2": f"{M}/5d419be7ed915d09e36362a2/Management_information_-_children_s_homes_-_30_June_2019.csv",
    "q2019Q4": f"{M}/5e42ac79ed915d0726c98911/Management_information_-_children_s_homes_-_31_December_2019.csv",
    "q2020Q2": f"{M}/5f33e352e90e0732df4dd226/Children_s_homes_management_information_June_2020.csv",
    "q2020Q4": f"{M}/60211c98d3bf7f70bc2e1f5a/Children_s_homes_management_information_December_2020.csv",
    "q2021Q2": f"{M}/610a9d88e90e0706c9570f4d/Management_information_children_s_homes_30_June_2021.ods",
    "q2021Q4": f"{M}/6203d43fd3bf7f3148fe3eb1/Management_information_children_s_homes_31_December_2021.ods",
    "q2022Q2": f"{M}/62dfe63ae90e0766ae82853e/Management_information_children_s_homes_30_June_2022.ods",
    "q2022Q4": f"{M}/63e65747e90e0706c77cc446/Management_information_children_s_homes_31_December_2022.ods",
    "q2023Q2": f"{M}/64d353c59865ab0013c8faaa/Management_information_children_s_homes_30_June_2023.ods",
    "q2023Q4": f"{M}/65dc64bb529bfa001ce954f4/Management_information_children_s_homes.ods",
    "q2024Q2": f"{M}/66b1f607a3c2a28abb50dd45/Management_information_children_s_homes_June_2024.ods",
    "a2024": "ch-2024.ods",
    "a2025": "ch-2025.ods",
    "sfr2026": "sfr2026.ods",
}

def http_get(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (research probe)"})
    with urlopen(req, timeout=60) as r:
        return r.read()

def ods_rows(content):
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(content)).read("content.xml"))
    sheets = {}
    for tbl in root.iter(f"{{{TNS}}}table"):
        name = tbl.get(f"{{{TNS}}}name")
        rows = []
        for r in tbl.findall(f"{{{TNS}}}table-row"):
            vals = []
            for c in r.findall(f"{{{TNS}}}table-cell"):
                rep = int(c.get(f"{{{TNS}}}number-columns-repeated", "1"))
                p = c.find(f"{{{XNS}}}p")
                v = p.text if p is not None and p.text else ""
                if rep > 100:
                    rep = 1
                vals.extend([v] * rep)
            if any(v.strip() for v in vals):
                rows.append(vals)
        sheets[name] = rows
    return sheets

def pick_table(sheets):
    cands = [n for n in sheets if "inspection_level" in n.lower() or "in_year" in n.lower()]
    if not cands:
        cands = list(sheets.keys())
    for name in cands:
        rows = sheets[name]
        for i, r in enumerate(rows[:10]):
            if r and str(r[0]).strip().lower() == "web link":
                return rows[i], rows[i + 1:]
    return None, None

def find_col(hdr, keys):
    kl = {k.lower() for k in keys}
    for i, h in enumerate(hdr):
        if str(h).strip().lower() in kl:
            return i
    return None

def d(s):
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(str(s).strip(), f)
        except Exception:
            pass
    return None

POS = {"Requires improvement to be good", "Inadequate"}
NEG = {"Good", "Outstanding"}

events = {}  # inspection number -> (urn, year, month, overall, type)
n_req = 0
t0 = time.time()
for label, url in sorted(ASSETS.items()):
    try:
        content = http_get(url) if url.startswith("http") else open(url, "rb").read()
        n_req += 1
        if url.endswith("csv"):
            text = content.decode("cp1252", errors="replace")
            delim = "\t" if "\t" in text.splitlines()[0] else ","
            rows = list(csv.reader(io.StringIO(text), delimiter=delim))
            if rows and len(rows[0]) == 1 and "\t" in rows[0][0]:
                rows = [r[0].split("\t") for r in rows]
            hdr, data = rows[0], [r for r in rows[1:] if any(v.strip() for v in r)]
        elif url.endswith(".ods"):
            hdr, data = pick_table(ods_rows(content))
        else:
            hdr, data = None, None
        if not hdr:
            print(label, "NO TABLE"); continue
        i_date = find_col(hdr, ["Inspection date"])
        i_urn = find_col(hdr, ["URN", "Provider URN"])
        i_num = find_col(hdr, ["Inspection number", "Inspection event number", "Event number"])
        i_type = find_col(hdr, ["Event type", "Inspection type group", "Inspection type"])
        if i_type is None and i_date is not None:
            cand = i_date - 1
            vals = {str(r[cand]).strip() if cand < len(r) else "" for r in data[:200]}
            if vals & {"Full inspection", "Monitoring inspection", "Assurance visit", "Monitoring visit"}:
                i_type = cand
        i_over = find_col(hdr, ["Overall experiences and progress of children and young people", "Overall Effectiveness"])
        i_ptype = find_col(hdr, ["Provision type", "Provider type"])

        def col(r, i):
            return str(r[i]).strip() if i is not None and i < len(r) else ""

        kept = added = 0
        for r in data:
            if "children" not in col(r, i_ptype).lower():
                continue
            if "full" not in col(r, i_type).lower():
                continue  # full inspections only (graded outcome events)
            dt = d(col(r, i_date))
            if not dt:
                continue
            num = col(r, i_num)
            key = (label, num) if not num else num
            kept += 1
            ev = (col(r, i_urn), dt.year, dt.month, col(r, i_over), label)
            if key in events:
                # dedupe check: prefer row with a graded outcome
                if col(r, i_over) and not events[key][3]:
                    events[key] = ev
            else:
                events[key] = ev
                added += 1
        print(f"{label}: full-CH rows kept={kept} new-after-dedupe={added}")
    except Exception as e:
        print(label, "FAIL", repr(e)[:120])

print(f"\nrequests={n_req} wall={time.time()-t0:.1f}s total deduped full-CH events={len(events)}")

# per-year aggregates
years = defaultdict(lambda: Counter())
homes = defaultdict(set)
vocab = Counter()
for urn, year, month, over, src in events.values():
    years[year]["n"] += 1
    vocab[over] += 1
    if over in POS:
        years[year]["pos"] += 1
    elif over in NEG:
        years[year]["neg"] += 1
    else:
        years[year]["ungraded"] += 1
    homes[year].add(urn)

print("\nyear | events | pos(RI/Inad) | neg(G/Out) | ungraded | distinct homes")
for y in sorted(years):
    c = years[y]
    print(f"{y} | {c['n']} | {c['pos']} | {c['neg']} | {c['ungraded']} | {len(homes[y])}")
print("\nfull-inspection overall-judgement vocabulary (deduped):")
for k, v in vocab.most_common():
    print(f"  {k!r}: {v}")

# suggested split windows (events by inspection year)
def window(a, b):
    ev = pos = 0
    for y in range(a, b + 1):
        ev += years[y]["n"]; pos += years[y]["pos"]
    return ev, pos

for name, (a, b) in {"train 2017-2019": (2017, 2019), "eval 2021-2023": (2021, 2023),
                     "holdout 2024-2026": (2024, 2026)}.items():
    ev, pos = window(a, b)
    print(f"{name}: full inspections={ev} positives={pos}")

json.dump(
    {str(y): {"events": years[y]["n"], "pos": years[y]["pos"], "neg": years[y]["neg"],
              "ungraded": years[y]["ungraded"], "homes": len(homes[y])} for y in sorted(years)},
    open("per_year_counts.json", "w"), indent=1)
print("saved per_year_counts.json")
