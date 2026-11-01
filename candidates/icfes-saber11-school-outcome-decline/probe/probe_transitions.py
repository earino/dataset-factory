# Transition capacity probe: join per-school aggregates for adjacent sittings and
# measure overlap and decline base rates. Aggregate-level only (per-school means
# from Socrata, no student rows). Cal-A school-years from kgxf-xxbe + rnvb-vnyh (2020-2).
import csv
import io
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PER = os.path.join(HERE, "per_school")
UA = {"User-Agent": "dataset-factory-discovery-probe"}


def load(period):
    path = os.path.join(PER, f"{period}.csv")
    if os.path.exists(path):
        rows = list(csv.DictReader(open(path)))
    elif period == "20202":
        rows = fetch_rnvb(period)
    else:
        raise FileNotFoundError(f"no per-school aggregates for {period}")
    out = {}
    for r in rows:
        n = int(r["n"])
        if r.get("cole_calendario") not in ("A", "B"):
            continue
        out[r["cole_codigo_icfes"]] = {"cal": r["cole_calendario"], "n": n,
                                       "mean": float(r["mean_global"]), "period": period}
    return out


def fetch_rnvb(period):
    # Saber 11 2020-2 (rnvb-vnyh): Calendario A 2020, richer schema, same school keys
    base = "https://www.datos.gov.co/resource/rnvb-vnyh.json"
    q = urllib.parse.urlencode({
        "$select": "cole_calendario,cole_codigo_icfes,count(*) as n,avg(punt_global) as mean_global",
        "$where": "punt_global IS NOT NULL AND cole_codigo_icfes IS NOT NULL",
        "$group": "cole_calendario,cole_codigo_icfes",
        "$limit": "50000",
    })
    with urllib.request.urlopen(urllib.request.Request(f"{base}?{q}", headers=UA), timeout=180) as r:
        rows = json.loads(r.read().decode())
    out_path = os.path.join(PER, f"{period}.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cole_calendario", "cole_codigo_icfes", "n", "mean_global"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"fetched rnvb-vnyh per-school aggregates -> {out_path} ({len(rows)} rows)")
    return rows


def transition_stats(a, b, cal, min_n=10):
    A, B = load(a), load(b)
    keys = [k for k in A if k in B and A[k]["cal"] == cal and B[k]["cal"] == cal
            and A[k]["n"] >= min_n and B[k]["n"] >= min_n]
    if not keys:
        return {"pair": f"{a}->{b}", "cal": cal, "n_both": 0}
    declines = sum(1 for k in keys if B[k]["mean"] < A[k]["mean"])
    d5 = sum(1 for k in keys if B[k]["mean"] - A[k]["mean"] <= -5)
    d10 = sum(1 for k in keys if B[k]["mean"] - A[k]["mean"] <= -10)
    up = sum(1 for k in keys if B[k]["mean"] > A[k]["mean"])
    deltas = [B[k]["mean"] - A[k]["mean"] for k in keys]
    return {
        "pair": f"{a}->{b}", "cal": cal, "n_both": len(keys),
        "decline": declines, "decline_rate": round(declines / len(keys), 4),
        "decline_ge5": d5, "decline_ge5_rate": round(d5 / len(keys), 4),
        "decline_ge10": d10, "decline_ge10_rate": round(d10 / len(keys), 4),
        "increase": up,
        "mean_delta": round(sum(deltas) / len(deltas), 2),
    }


def main():
    results = []
    # Calendario A school-year transitions available on the anonymous channel
    # (2018 and 2021 school-years are absent from the published open record -
    # measured by probe_period_coverage.py; pairs need BOTH years present)
    for a, b in [("20142", "20152"), ("20152", "20162"), ("20162", "20172"),
                 ("20194", "20202")]:
        results.append(transition_stats(a, b, "A"))
    # Calendario B consecutive sittings 2015-1..2022-1 (all present, measured)
    for a, b in [("20151", "20161"), ("20161", "20171"), ("20171", "20181"),
                 ("20181", "20191"), ("20191", "20201"), ("20201", "20211"),
                 ("20211", "20221")]:
        results.append(transition_stats(a, b, "B"))
    for r in results:
        print(json.dumps(r, ensure_ascii=False))
    json.dump(results, open(os.path.join(HERE, "transition_stats.json"), "w"), indent=1)
    print("wrote transition_stats.json")


if __name__ == "__main__":
    main()
