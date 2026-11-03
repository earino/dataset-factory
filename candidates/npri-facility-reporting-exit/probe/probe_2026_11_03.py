#!/usr/bin/env python3
"""NPRI facility reporting-exit dated-example probe (discovery, 2026-11-03).

Bounded, anonymous, coordinator-side. Fetches the 2023 and 2024 single-year
NPRI CSVs (~79 MB total) to (a) measure the fresh 2023->2024 exit pair (third
full-population measurement, first in the holdout-adjacent era), (b) name one
exiting and one persisting facility for the dated worked example, (c) record
per-file encodings. Bulk CSVs land in scratch and are left to the 24h sweep;
compact outputs go to probe/out/.
"""
import csv, hashlib, io, json, os, re, sys, time, urllib.parse, urllib.request

SCRATCH = "/opt/data/cache/scratch/ca_npri_2026_11_03"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(SCRATCH, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

API = "https://data-donnees.az.ec.gc.ca/api/file?path="
PATH = ("/substances/plansreports/reporting-facilities-pollutant-release-and-transfer-data/"
        "single-year-data-tables-by-facility-releases-transfers-and-disposals/"
        "NPRI-INRP_DataDonn\u00e9es_{year}.csv")

def fetch(year):
    url = API + urllib.parse.quote(PATH.format(year=year), safe="/")
    dest = os.path.join(SCRATCH, f"npri_{year}.csv")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        n = os.path.getsize(dest)
        h = hashlib.sha256(open(dest, "rb").read()).hexdigest()
        print(f"fetch {year}: cached {n} B sha256 {h[:16]}")
        return dest, n, 0.0, h, url
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "dataset-factory-discovery/1.0"})
    n = 0
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
    dt = time.time() - t0
    h = hashlib.sha256(open(dest, "rb").read()).hexdigest()
    print(f"fetch {year}: {n} B in {dt:.1f}s sha256 {h[:16]}")
    return dest, n, dt, h, url

def read_csv(path):
    raw = open(path, "rb").read()
    try:
        text, enc = raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, enc = raw.decode("cp1252"), "cp1252"
    return enc, csv.DictReader(io.StringIO(text))

def main():
    result = {"fetched": {}, "measured": {}}
    dest23, n23, dt23, h23, u23 = fetch(2023)
    dest24, n24, dt24, h24, u24 = fetch(2024)
    result["fetched"] = {
        "npri_2023": {"bytes": n23, "seconds": round(dt23, 1), "sha256": h23, "url": u23},
        "npri_2024": {"bytes": n24, "seconds": round(dt24, 1), "sha256": h24, "url": u24},
    }

    def load(path, year):
        enc, rdr = read_csv(path)
        result["measured"].setdefault("encodings", {})[os.path.basename(path)] = enc
        idcol = next((k for k in rdr.fieldnames if re.search(r"npri", k, re.I) and re.search(r"id", k, re.I)), None)
        rows_by_id, nrows, extra = {}, 0, {}
        for row in rdr:
            nrows += 1
            fid = (row.get(idcol) or "").strip()
            if not fid:
                continue
            d = rows_by_id.setdefault(fid, {"first": row, "n": 0})
            d["n"] += 1
        print(f"{year}: {nrows} rows, {len(rows_by_id)} distinct facilities, idcol={idcol!r}, enc={enc}")
        return idcol, rows_by_id, nrows

    idcol23, by23, n23r = load(dest23, 2023)
    idcol24, by24, n24r = load(dest24, 2024)
    s23, s24 = set(by23), set(by24)
    exited, persisted, entrants = s23 - s24, s23 & s24, s24 - s23
    result["measured"].update({
        "rows_2023": n23r, "rows_2024": n24r,
        "facilities_2023": len(s23), "facilities_2024": len(s24),
        "exit_2023_to_2024": len(exited), "exit_rate_pct": round(len(exited) / len(s23) * 100, 3),
        "entrants_2024": len(entrants),
        "id_column_2023": idcol23, "id_column_2024": idcol24,
    })
    print(f"2023->2024: exits {len(exited)} ({len(exited)/len(s23)*100:.3f}%), persisted {len(persisted)}, entrants {len(entrants)}")

    def info(d):
        r = d["first"]
        def get(*needles):
            for k in (r.keys() or []):
                kl = (k or "").lower()
                if any(nd in kl for nd in needles):
                    v = (r[k] or "").strip()
                    if v:
                        return v
            return None
        return {
            "facility_name": get("facility name", "nom de l'installation"),
            "company": get("company name", "entreprise"),
            "city": get("ville", "city"),
            "province": get("province"),
            "naics": get("naics 4"),
            "naics_title": get("naics 4 sector name (english)"),
            "n_rows_2023": d["n"],
        }

    # named examples: one exit, two persisting
    def pick(cands, exclude=()):
        for fid in sorted(cands):
            if fid in exclude:
                continue
            i = info(by23[fid] if fid in by23 else by24[fid])
            if i["facility_name"] and i["city"] and i["province"]:
                return fid, i
        return None, None

    ex_id, ex_info = pick(exited)
    neg_id, neg_info = pick(persisted)
    neg2_id, neg2_info = pick(persisted, exclude={neg_id})
    for tag, fid, i in (("exit_example", ex_id, ex_info), ("negative_example", neg_id, neg_info),
                        ("negative_example_2", neg2_id, neg2_info)):
        if fid:
            result["measured"][tag] = {"npri_id": fid, **i}
            print(tag, fid, i["facility_name"], "|", i["city"], i["province"], "| NAICS", i["naics"])

    # province mix of exits (clustering evidence)
    prov = {}
    for fid in exited:
        p = info(by23[fid]).get("province") or "?"
        prov[p] = prov.get(p, 0) + 1
    result["measured"]["exit_province_mix"] = dict(sorted(prov.items(), key=lambda kv: -kv[1]))

    outp = os.path.join(OUT, "probe_2026_11_03.json")
    json.dump(result, open(outp, "w"), indent=1)
    print("wrote", outp)

if __name__ == "__main__":
    sys.exit(main())
