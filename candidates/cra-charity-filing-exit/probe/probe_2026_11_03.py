#!/usr/bin/env python3
"""CRA charity filing-exit dated-example probe (discovery, 2026-11-03).

Bounded, anonymous, coordinator-side. Fetches the 2023 and 2024 Identification
files plus the 2023 financial file (~47 MB total) to (a) reproduce the recorded
2023->2024 exit measurement, (b) name one exiting and one persisting charity
with FPE (fiscal period end) for the dated worked example, (c) measure the FPE
month mix and multi-return share of the 2023 filing population.

Bulk CSVs land in scratch and are left to the 24h sweep; only compact outputs
are written to probe/out/.
"""
import csv, hashlib, json, os, sys, time, urllib.request

SCRATCH = "/opt/data/cache/scratch/ca_charities_2026_11_03"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(SCRATCH, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

BASE = "https://open.canada.ca/data/dataset/"
FILES = {
    "ident_2023": BASE + "05b3abd0-e70f-4b3b-a9c5-acc436bd15b6/resource/31a52caf-fa79-4ab3-bded-1ccc7b61c17f/download/ident_2023_updated.csv",
    "ident_2024": BASE + "80c00cdb-1358-415c-bb8b-0de7f12675b8/resource/694fdc72-eae4-4ee0-83eb-832ab7b230e3/download/ident_2024_updated.csv",
    "fin_2023": BASE + "05b3abd0-e70f-4b3b-a9c5-acc436bd15b6/resource/0b9b4b01-5cb6-4981-b007-ae88f48cc799/download/financial_d_and_schedule_6_2023_updated.csv",
}

def fetch(key, url):
    dest = os.path.join(SCRATCH, key + ".csv")
    t0 = time.time()
    with urllib.request.urlopen(url, timeout=300) as r, open(dest, "wb") as f:
        data_len = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            data_len += len(chunk)
    dt = time.time() - t0
    h = hashlib.sha256(open(dest, "rb").read()).hexdigest()
    print(f"fetch {key}: {data_len} B in {dt:.1f}s sha256 {h[:16]}")
    return dest, data_len, dt, h

def read_csv(path):
    """Encoding is per-year, measured: 2023 Identification + financial decode
    cleanly as UTF-8; the 2012 file measured cp1252 on 2026-10-19. Try UTF-8
    first, fall back to cp1252; report which one each file used."""
    raw = open(path, "rb").read()
    try:
        text, enc = raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, enc = raw.decode("cp1252"), "cp1252"
    import io
    return enc, csv.DictReader(io.StringIO(text))

def main():
    result = {"fetched": {}, "measured": {}}
    for key, url in FILES.items():
        dest, n, dt, h = fetch(key, url)
        result["fetched"][key] = {"bytes": n, "seconds": round(dt, 1), "sha256": h, "url": url}

    # BN sets from both Identification files
    def bn_set(path):
        enc, rdr = read_csv(path)
        result.setdefault("measured", {}).setdefault("encodings", {})[os.path.basename(path)] = enc
        s, names = set(), {}
        for row in rdr:
            bn = (row.get("BN") or "").strip()
            if bn:
                s.add(bn)
                names[bn] = {k: (row.get(k) or "").strip() for k in
                             ("Legal Name", "City", "Province", "Category", "Designation")}
        return s, names

    s23, info23 = bn_set(SCRATCH + "/ident_2023.csv")
    s24, info24 = bn_set(SCRATCH + "/ident_2024.csv")
    exited = s23 - s24
    persisted = s23 & s24
    entrants = s24 - s23
    result["measured"]["ident_2023_bn"] = len(s23)
    result["measured"]["ident_2024_bn"] = len(s24)
    result["measured"]["exit_2023_to_2024"] = len(exited)
    result["measured"]["exit_rate"] = round(len(exited) / len(s23) * 100, 3)
    result["measured"]["entrants_2024"] = len(entrants)
    print(f"2023 BNs {len(s23)}, 2024 BNs {len(s24)}, exits {len(exited)} "
          f"({len(exited)/len(s23)*100:.3f}%), entrants {len(entrants)}")

    # FPE lookups from the 2023 financial file
    fpe_of, multi = {}, 0
    n_fin = 0
    enc_fin, rdr_fin = read_csv(SCRATCH + "/fin_2023.csv")
    result["measured"].setdefault("encodings", {})["fin_2023.csv"] = enc_fin
    for row in rdr_fin:
        n_fin += 1
        bn = (row.get("BN") or "").strip()
        fpe = (row.get("FPE") or "").strip()
        if not bn or not fpe:
            continue
        fpe_of.setdefault(bn, []).append(fpe)
    multi = sum(1 for v in fpe_of.values() if len(v) > 1)
    result["measured"]["fin_2023_rows"] = n_fin
    result["measured"]["fin_2023_bn_with_fpe"] = len(fpe_of)
    result["measured"]["fin_2023_bn_multi_return"] = multi
    fpe_months = {}
    for fpes in fpe_of.values():
        fpe_months[fpes[0][5:7] if len(fpes[0]) >= 7 else "?"] = fpe_months.get(fpes[0][5:7] if len(fpes[0]) >= 7 else "?", 0) + 1
    result["measured"]["fpe_month_mix_2023"] = dict(sorted(fpe_months.items()))
    print(f"financial 2023: {n_fin} rows, {len(fpe_of)} BNs with FPE, {multi} multi-return BNs")

    # named examples: one clean exit (prefer a single Dec-31 FPE), two persisting negatives
    def clean(bn):
        f = fpe_of.get(bn, [])
        return len(f) == 1 and f[0].endswith("12-31")

    exit_ex = None
    for bn in sorted(exited):
        if clean(bn) and info23.get(bn, {}).get("Legal Name") and info23.get(bn, {}).get("City"):
            exit_ex = bn
            break
    neg_ex, neg_ex2 = None, None
    for bn in sorted(persisted):
        if clean(bn) and info23.get(bn, {}).get("Legal Name") and info23.get(bn, {}).get("City"):
            neg_ex = bn
            break
    for bn in sorted(persisted):
        if clean(bn) and bn != neg_ex and info23.get(bn, {}).get("Legal Name"):
            neg_ex2 = bn
            break
    for tag, bn in (("exit_example", exit_ex), ("negative_example", neg_ex), ("negative_example_2", neg_ex2)):
        if bn:
            result["measured"][tag] = {"bn": bn, "fpe_2023": fpe_of.get(bn), "ident_2023": info23.get(bn)}
            print(tag, bn, fpe_of.get(bn), (info23.get(bn) or {}).get("Legal Name"), (info23.get(bn) or {}).get("City"))

    # exits with FPE coverage (how many of the exited BNs appear in the 2023 financial file)
    cov = sum(1 for bn in exited if bn in fpe_of)
    result["measured"]["exit_bn_in_fin_2023"] = cov
    ex_months = {}
    for bn in exited:
        f = fpe_of.get(bn, ["?"])[0]
        ex_months[f[5:7] if len(f) >= 7 else "?"] = ex_months.get(f[5:7] if len(f) >= 7 else "?", 0) + 1
    result["measured"]["exit_fpe_month_mix"] = dict(sorted(ex_months.items()))

    outp = os.path.join(OUT, "probe_2026_11_03.json")
    json.dump(result, open(outp, "w"), indent=1)
    print("wrote", outp)

if __name__ == "__main__":
    sys.exit(main())
