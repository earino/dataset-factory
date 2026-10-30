# Download the full readable quarterly series + measure per-file events, dates, judgement mix.
# Stdlib-only: csv, ods, xlsx readers. Discovery evidence for the Ofsted children's homes candidate.
import csv, io, json, re, time, zipfile
import xml.etree.ElementTree as ET
from collections import Counter
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

def colnum(ref):
    m = re.match(r"([A-Z]+)", ref)
    n = 0
    for ch in m.group(1):
        n = n * 26 + ord(ch) - 64
    return n - 1

def xlsx_rows(content):
    z = zipfile.ZipFile(io.BytesIO(content))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root:
            shared.append("".join(t.text or "" for t in si.iter() if t.text))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.get("Id"): r.get("Target") for r in rels}
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    sheets = {}
    for sh in wb.iter(f"{ns}sheet"):
        name = sh.get("name")
        tgt = relmap.get(sh.get(f"{rns}id"))
        if not tgt:
            continue
        path = "xl/" + tgt if not tgt.startswith("xl/") else tgt
        root = ET.fromstring(z.read(path))
        rows = []
        for r in root.iter(f"{ns}row"):
            vals = {}
            for c in r.iter(f"{ns}c"):
                i = colnum(c.get("r", "A1"))
                v = c.find(f"{ns}v")
                if c.get("t") == "s" and v is not None:
                    val = shared[int(v.text)]
                elif c.get("t") == "inlineStr":
                    val = "".join(t.text or "" for t in c.iter() if t.text)
                else:
                    val = v.text if v is not None else ""
                vals[i] = val or ""
            if vals:
                width = max(vals) + 1
                rows.append([vals.get(j, "") for j in range(width)])
            if any(str(x).strip() for x in rows[-1] if rows):
                pass
            rows = [r for r in rows if any(str(x).strip() for x in r)]
        sheets[name] = rows
    return sheets

def pick_table(sheets):
    # return (header, data) for the inspection-level sheet
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
    for i, h in enumerate(hdr):
        if str(h).strip().lower() in {k.lower() for k in keys}:
            return i
    return None

def d(s):
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(str(s).strip(), f)
        except Exception:
            pass
    return None

stats = {}
total_bytes = 0
t_all = time.time()
for label, url in sorted(ASSETS.items()):
    t0 = time.time()
    try:
        content = http_get(url) if url.startswith("http") else open(url, "rb").read()
        if url.endswith(".csv") or url.endswith("csv"):
            text = content.decode("cp1252", errors="replace")
            delim = "\t" if "\t" in text.splitlines()[0] else ","
            rows = list(csv.reader(io.StringIO(text), delimiter=delim))
            # June 2019 quirk: comma-CSV where each line is one quoted field containing tab-separated values
            if rows and len(rows[0]) == 1 and "\t" in rows[0][0]:
                rows = [r[0].split("\t") for r in rows]
            hdr, data = rows[0], [r for r in rows[1:] if any(v.strip() for v in r)]
        elif url.endswith(".ods"):
            hdr, data = pick_table(ods_rows(content))
        else:
            hdr, data = pick_table(xlsx_rows(content))
        if not hdr:
            stats[label] = {"error": "no table found"}
            print(label, "ERR no table")
            continue
        i_date = find_col(hdr, ["Inspection date"])
        i_urn = find_col(hdr, ["URN", "Provider URN"])
        i_type = find_col(hdr, ["Event type", "Inspection type group", "Inspection type"])
        if i_type is None and find_col(hdr, ["Inspection date"]) is not None:
            # annual 2025 sheet: the Event-type header cell is blank; data sits just before Inspection date
            cand = find_col(hdr, ["Inspection date"]) - 1
            vals = {str(r[cand]).strip() if cand < len(r) else "" for r in data[:200]}
            if vals & {"Full inspection", "Monitoring inspection", "Assurance visit"}:
                i_type = cand
        i_over = find_col(hdr, ["Overall experiences and progress of children and young people", "Overall Effectiveness"])
        i_ptype = find_col(hdr, ["Provision type", "Provider type"])
        if i_date is None or i_over is None:
            stats[label] = {"error": "missing cols", "hdr": [str(x) for x in hdr[:22]]}
            print(label, "ERR cols")
            continue

        def col(r, i):
            return str(r[i]) if i is not None and i < len(r) else ""

        ch = [r for r in data if "children" in col(r, i_ptype).lower()]
        dates = [x for x in (d(col(r, i_date)) for r in data) if x]
        ch_full = [r for r in ch if "full" in col(r, i_type).lower()]
        all_over = Counter(col(r, i_over).strip() for r in ch)
        full_over = Counter(col(r, i_over).strip() for r in ch_full)
        stats[label] = {
            "n_rows_all_provisions": len(data),
            "n_childrens_home_events": len(ch),
            "n_ch_full_inspections": len(ch_full),
            "date_min": min(dates).date().isoformat() if dates else None,
            "date_max": max(dates).date().isoformat() if dates else None,
            "distinct_ch_urns": len({col(r, i_urn) for r in ch}),
            "ch_event_type_mix": Counter(col(r, i_type) for r in ch).most_common(),
            "ch_overall_all": all_over.most_common(),
            "ch_overall_full_only": full_over.most_common(),
            "bytes": len(content),
            "sec": round(time.time() - t0, 1),
        }
        total_bytes += len(content)
        s = stats[label]
        print(f"{label}: rows(CH)={s['n_childrens_home_events']} full={s['n_ch_full_inspections']} "
              f"{s['date_min']}..{s['date_max']} urns={s['distinct_ch_urns']} {s['sec']}s")
    except Exception as e:
        stats[label] = {"error": repr(e)[:200]}
        print(label, "FAIL", repr(e)[:150])

print("TOTAL bytes:", total_bytes, "wall:", round(time.time() - t_all, 1), "s")
json.dump(stats, open("series_summary.json", "w"), indent=1, default=str)
print("saved series_summary.json")
