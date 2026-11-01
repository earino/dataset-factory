# Per-school aggregate probe for Saber 11 sittings with punt_global on kgxf-xxbe.
# One SoQL query per sitting: per-school examinee counts and mean global score
# (server-side aggregation, no bulk microdata transfer). Writes per-school rows
# to per_school/<period>.csv plus a summary printed to stdout.
import json
import csv
import io
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://www.datos.gov.co/resource/kgxf-xxbe.json"
UA = {"User-Agent": "dataset-factory-discovery-probe"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "per_school")
os.makedirs(OUT, exist_ok=True)

# sittings with punt_global present (measured by probe_period_coverage.py)
PERIODS = ["20151", "20161", "20171", "20181", "20191", "20201", "20211", "20221",   # Calendario B
           "20142", "20152", "20162", "20172", "20194", "20224"]                     # Calendario A era


def soql(params, retries=3):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  retry {i+1} after {e}", file=sys.stderr)


def main():
    summary = {}
    for p in PERIODS:
        rows = soql({
            "$select": "cole_calendario,cole_codigo_icfes,cole_cod_dane_establecimiento,count(*) as n,"
                       "avg(punt_global::number) as mean_global",
            "$where": f"periodo='{p}' AND punt_global IS NOT NULL AND cole_codigo_icfes IS NOT NULL",
            "$group": "cole_calendario,cole_codigo_icfes,cole_cod_dane_establecimiento",
            "$limit": "50000",
        })
        out_path = os.path.join(OUT, f"{p}.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["cole_calendario", "cole_codigo_icfes",
                                               "cole_cod_dane_establecimiento", "n", "mean_global"])
            w.writeheader()
            for r in rows:
                w.writerow(r)
        n_schools = len(rows)
        n_schools10 = sum(1 for r in rows if int(r["n"]) >= 10)
        cal_a = sum(1 for r in rows if r["cole_calendario"] == "A")
        cal_b = sum(1 for r in rows if r["cole_calendario"] == "B")
        summary[p] = {"schools": n_schools, "schools_n10": n_schools10, "cal_a": cal_a, "cal_b": cal_b}
        print(f"{p}: schools={n_schools} (A {cal_a} / B {cal_b}), n>=10: {n_schools10} -> {out_path}")
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
