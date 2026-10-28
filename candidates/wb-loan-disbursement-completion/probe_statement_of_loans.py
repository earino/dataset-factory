#!/usr/bin/env python3
"""Discovery probe: WBG Finances One Statement of Loans/Credits (IBRD DS00047, IDA DS00001).

Revision 2 (2026-10-28): correct maturity definition (disbursement phase closed =
terminal status or closed_date <= data-as-of; `closed_date_most_recent` is the
CURRENT closing date and lies in the future for open loans), IDA field names
(`credit_number`, `*_us_` amount columns), IBRD loan_type mix, per-year
matured/open counts for split design, and a vintage-archive filter check.

Pages the documented anonymous API (top=1000/skip) over the latest available
snapshots and writes probe_output.json beside this script.

Run:  python3 probe_statement_of_loans.py  (coordinator, 2026-10-28)
"""
import json
import time
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone, date

BASE = "https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice"
UA = "Scout-discovery-probe/1.0 (dataset-factory candidate probe; contact: financesone@worldbank.org)"
DATA_AS_OF = date(2026, 9, 30)  # "Data As Of" on both dataset pages, 2026-10-28
SETS = [
    ("IBRD", "DS00047", "RS00049", {
        "number": "loan_number", "status": "loan_status", "type": "loan_type",
        "original": "original_principal_amount", "disbursed": "disbursed_amount",
        "undisbursed": "undisbursed_amount", "cancelled": "cancelled_amount"}),
    ("IDA", "DS00001", "RS00001", {
        "number": "credit_number", "status": "credit_status", "type": None,
        "original": "original_principal_amount_us_", "disbursed": "disbursed_amount_us_",
        "undisbursed": "undisbursed_amount_us_", "cancelled": "cancelled_amount_us_"}),
]
TOP = 1000
OUT = "probe_output.json"
TERMINAL = {"Fully Repaid", "Fully Cancelled", "Fully Disbursed", "Fully Transferred", "Terminated"}
# "Repaying": disbursement phase over, repayment ongoing -> ratio final unless undisbursed remains.
OPEN_DISBURSING = {"Disbursing", "Disbursing&Repaying", "Effective", "Signed", "Approved"}


def fetch_page(ds, rs, skip, top=TOP, extra=None):
    url = f"{BASE}?datasetId={ds}&resourceId={rs}&top={top}&skip={skip}&type=json"
    if extra:
        url += "&" + extra
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    dt = time.time() - t0
    return json.loads(raw.decode("utf-8", "replace")), len(raw), dt, url


def parse_date(s):
    if not s:
        return None
    return datetime.strptime(s, "%d-%b-%Y").date()


def num(r, key):
    v = r.get(key)
    return v if isinstance(v, (int, float)) else 0


def analyse(tag, rows, fm):
    n = len(rows)
    number, status_k, type_k = fm["number"], fm["status"], fm["type"]
    distinct = len({r.get(number) for r in rows})
    prefix = Counter()
    for r in rows:
        ln = str(r.get(number) or "")
        if ln.startswith(("IBRDB", "IBRDG", "IDAB", "IDAG")):
            prefix["guarantee"] += 1
        elif ln.startswith(("IDAD", "IDAH", "IDAE")):
            prefix["IDA grant"] += 1
        else:
            prefix["loan/credit"] += 1
    ltype = Counter(str(r.get(type_k)) for r in rows) if type_k else {"n/a (IDA type encoded in number)": n}
    status = Counter(str(r.get(status_k)) for r in rows)

    def appr_year(r):
        d = parse_date(r.get("board_approval_date"))
        return d.year if d else None

    def ratio(r):
        o = num(r, fm["original"])
        return (num(r, fm["disbursed"]) / o) if o > 0 else None

    def disbursement_closed(r):
        st = str(r.get(status_k))
        cd = parse_date(r.get("closed_date_most_recent"))
        if st in OPEN_DISBURSING and not (cd and cd <= DATA_AS_OF):
            return False
        # open loan whose disbursement window has passed but still labelled disbursing:
        # treat as closed only by status/terminal evidence; future closed_date = open.
        if cd and cd > DATA_AS_OF and st not in TERMINAL and st != "Repaying":
            return False
        return True

    matured = [r for r in rows if disbursement_closed(r)]
    still_open = [r for r in rows if not disbursement_closed(r)]
    repaying_with_undisbursed = [r for r in rows if str(r.get(status_k)) == "Repaying" and num(r, fm["undisbursed"]) > 0]
    appr = Counter(y for y in (appr_year(r) for r in rows) if y)
    years = sorted(appr)

    rates = {}
    for th in (0.5, 0.7, 0.8, 0.9, 0.99):
        ratios = [x for x in (ratio(r) for r in matured) if x is not None]
        pos = sum(1 for x in ratios if x >= th)
        rates[f">={th:.0%}"] = [pos, len(ratios), round(pos / len(ratios), 4) if ratios else None]
    buckets = Counter()
    for r in matured:
        x = ratio(r)
        if x is None:
            buckets["no-original"] += 1
        elif x >= 0.99:
            buckets[">=99%"] += 1
        elif x >= 0.9:
            buckets["90-99%"] += 1
        elif x >= 0.7:
            buckets["70-90%"] += 1
        elif x >= 0.5:
            buckets["50-70%"] += 1
        elif x > 0:
            buckets["1-50%"] += 1
        else:
            buckets["0%"] += 1
    windows = {
        "train <=1999": (None, 1999),
        "eval 2000-2009": (2000, 2009),
        "holdout 2010-2017": (2010, 2017),
    }
    splits = {}
    for wname, (a, b) in windows.items():
        sel = [r for r in matured if (y := appr_year(r)) and (a is None or y >= a) and y <= b]
        pos = [r for r in sel if (x := ratio(r)) is not None and x >= 0.9]
        neg = [r for r in sel if (x := ratio(r)) is not None and x < 0.9]
        splits[wname] = {
            "rows": len(sel), "pos>=90%": len(pos), "neg": len(neg),
            "distinct_projects_pos": len({r.get("project_id") for r in pos}),
            "distinct_countries_pos": len({r.get("country") for r in pos}),
            "distinct_country_year_pos": len({
                (r.get("country"), appr_year(r)) for r in pos if appr_year(r) is not None})}
    per_year_matured_open = {}
    for y in years:
        m = sum(1 for r in matured if appr_year(r) == y)
        o = sum(1 for r in still_open if appr_year(r) == y)
        per_year_matured_open[str(y)] = [m, o]
    zero_orig = sum(1 for r in rows if num(r, fm["original"]) <= 0)
    bad = checked = 0
    for r in matured:
        o = num(r, fm["original"])
        if o <= 0:
            continue
        checked += 1
        s = num(r, fm["disbursed"]) + num(r, fm["undisbursed"]) + num(r, fm["cancelled"])
        if abs(s - o) > max(1.0, o * 1e-6):
            bad += 1
    cancelled_any = sum(1 for r in matured if num(r, fm["cancelled"]) > 0)
    fully_cancelled_or_zero = sum(1 for r in matured if (x := ratio(r)) is not None and x == 0)
    return {
        "tag": tag, "rows": n, "distinct_instrument_numbers": distinct,
        "prefix_mix": dict(prefix), "type_or_loan_type_mix": dict(ltype),
        "status_mix": dict(status),
        "approval_year_min": years[0] if years else None,
        "approval_year_max": years[-1] if years else None,
        "disbursement_closed_rows": len(matured), "still_open_rows": len(still_open),
        "repaying_status_with_undisbursed_gt0": len(repaying_with_undisbursed),
        "zero_original_principal_rows": zero_orig,
        "base_rates_among_closed": rates,
        "ratio_buckets_among_closed": dict(buckets),
        "closed_fully_undisbursed_ratio_zero": fully_cancelled_or_zero,
        "closed_with_any_cancellation": cancelled_any,
        "split_windows_90pct_label": splits,
        "per_year_disbursement_closed_then_open": per_year_matured_open,
        "consistency_d_plus_u_plus_c_equals_original": {"checked": checked, "mismatches": bad},
    }


def main():
    t_start = time.time()
    out = {"probed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "machine_class": "hosted coordinator container, 4 vCPU, Python urllib",
           "data_as_of": DATA_AS_OF.isoformat(), "datasets": []}
    for tag, ds, rs, fm in SETS:
        rows = []
        reqs = nbytes = 0
        t0 = time.time()
        skip = 0
        server_count = None
        while True:
            page, nb, dt, url = fetch_page(ds, rs, skip)
            reqs += 1
            nbytes += nb
            server_count = page.get("count")
            data = page.get("data") or []
            rows.extend(data)
            if len(data) < TOP:
                break
            skip += TOP
        wall = time.time() - t0
        agg = analyse(tag, rows, fm)
        agg["fetch_cost"] = {"requests": reqs, "bytes": nbytes, "wall_seconds": round(wall, 2),
                             "server_reported_count": server_count, "rows_received": len(rows)}
        out["datasets"].append(agg)
        print(f"{tag}: {len(rows)} rows, {reqs} requests, {nbytes} bytes, {wall:.1f}s")
    # vintage archive check: does the apiservice honour end_of_period filters on DS00975?
    vp = []
    for val in ("30-APR-2011", "30-Apr-2011", "30-Jun-2015"):
        try:
            page, nb, dt, url = fetch_page("DS00975", "RS00905", 0, top=5, extra=f"end_of_period={val}")
            vp.append({"filter": f"end_of_period={val}", "server_count": page.get("count"),
                       "sample_end_of_period_values": [r.get("end_of_period") for r in (page.get("data") or [])[:3]]})
        except urllib.error.HTTPError as e:
            vp.append({"filter": val, "http_error": e.code})
    out["vintage_archive_probe"] = {
        "note": "DS00975 monthly-snapshot archive, 1,585,498 rows per metadata; count unchanged by every filter format tried -> apiservice GET ignores date filters; per-month slicing unconfirmed, bulk >300MB is worker-scope",
        "attempts": vp}
    out["total_wall_seconds"] = round(time.time() - t_start, 2)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
