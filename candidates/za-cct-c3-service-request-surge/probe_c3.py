#!/usr/bin/env python3
"""Bounded discovery probes for za-cct-c3-service-request-surge (City of Cape Town C3).

Reproduces the measurements in record.json / notes.md with read-only aggregate
queries against the public ArcGIS FeatureServer table (no bulk download):

  --panel        total rows, min/max CreatedOnDT, category mix, suburb coverage
  --series CAT   day-level created-count series for one complaint category
                 (paged group-by; writes/prints weekly aggregation)
  --surge        surge base rates for the 5 measured categories, per split window
  --timing       which created-dates are present at the probe instant
  --mask         (water/electricity billing sibling) mask-by-month evidence for
                 the April-2026 unmask regime change - the billing-family veto

The full 4.5M-row panel extraction is construction work for a worker, not run here.
"""
import argparse
import collections
import datetime
import json
import ssl
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (dataset-factory discovery probe)"}
CTX = ssl.create_default_context()

C3 = ("https://services6.arcgis.com/nyYfO9SxHU2ChQd9/arcgis/rest/services/"
      "schema_jan2023_iso/FeatureServer/0")
WATER = ("https://services6.arcgis.com/nyYfO9SxHU2ChQd9/arcgis/rest/services/"
         "Suburb_Level_Water_Billing_2021_to_March_2026/FeatureServer/0")


def get_json(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.loads(r.read())


def q(svc, params, timeout=90):
    params = dict(params)
    params["f"] = "json"
    return get_json(svc + "/query?" + urllib.parse.urlencode(params), timeout)


def iso(ms):
    """Epoch ms -> aware UTC datetime; raises if ms is missing."""
    if not ms:
        raise ValueError("missing timestamp")
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc)


CATS = ["No Power", "SEW: Blocked/Overflow", "Street Lights - All Lights Out",
        "Illegal Dumping", "Damaged Bin - 240L"]


def day_counts(category):
    """Day-level created-count series for one category (paged group-by query)."""
    out = {}
    offset = 0
    while True:
        j = q(C3, {"where": f"C3_Complaint_Type='{category}'", "outFields": "",
                   "groupByFieldsForStatistics": "CreatedOnDT",
                   "outStatistics": json.dumps([{"statisticType": "count",
                                                 "onStatisticField": "Notification",
                                                 "outStatisticFieldName": "n"}]),
                   "resultRecordCount": 1000, "resultOffset": offset,
                   "orderByFields": "CreatedOnDT ASC", "returnGeometry": "false"})
        feats = j.get("features") or []
        for f in feats:
            a = f["attributes"]
            if a.get("CreatedOnDT"):
                out[iso(a["CreatedOnDT"]).date()] = a["n"]
        if len(feats) < 1000:
            break
        offset += 1000
    return out


def week_of(d):
    return d - datetime.timedelta(days=d.weekday())


def panel():
    meta = get_json(C3.rsplit("/", 1)[0] + "?f=pjson")
    entries = meta.get("layers") or meta.get("tables") or []
    for f in get_json(C3.rsplit("/", 1)[0] + f"/{entries[0]['id']}?f=pjson").get("fields", []):
        print(f"  {f.get('name'):18s} {f.get('type')}")
    print("TOTAL ROWS:", q(C3, {"where": "1=1", "returnCountOnly": "true"}).get("count"))
    st = q(C3, {"where": "1=1", "outFields": "",
                "outStatistics": json.dumps([
                    {"statisticType": "min", "onStatisticField": "CreatedOnDT", "outStatisticFieldName": "mn"},
                    {"statisticType": "max", "onStatisticField": "CreatedOnDT", "outStatisticFieldName": "mx"}])})
    a = (st.get("features") or [{}])[0].get("attributes", {})
    mn, mx = a.get("mn"), a.get("mx")
    print("min CreatedOnDT:", iso(mn) if mn else "?", "max:", iso(mx) if mx else "?")
    ct = q(C3, {"where": "1=1", "outFields": "", "groupByFieldsForStatistics": "C3_Complaint_Type",
                "outStatistics": json.dumps([{"statisticType": "count", "onStatisticField": "Notification", "outStatisticFieldName": "n"}]),
                "resultRecordCount": 1000, "returnGeometry": "false"})
    print(f"complaint types (capped at 1000): {len(ct.get('features') or [])}")
    for f in sorted(ct.get("features") or [], key=lambda x: -x["attributes"]["n"])[:25]:
        print(f"   {str(f['attributes'].get('C3_Complaint_Type'))[:45]:47s} {f['attributes']['n']:>10,}")


def surge():
    def win(wstart):
        if wstart <= datetime.date(2024, 12, 31):
            return "train"
        if wstart <= datetime.date(2025, 12, 31):
            return "eval"
        return "holdout"

    for c in CATS:
        dc = day_counts(c)
        wk = collections.Counter()
        for d, n in dc.items():
            wk[week_of(d)] += n
        weeks = sorted(wk)
        res = {"train": [0, 0], "eval": [0, 0], "holdout": [0, 0]}
        for i, w in enumerate(weeks):
            if i < 8:
                continue
            hist = sorted(wk[weeks[j]] for j in range(i - 8, i))
            med = (hist[3] + hist[4]) / 2
            res[win(w)][1 if wk[w] > 1.25 * med else 0] += 1
        print(f"{c:32s} " + " ".join(f"{k}: surge {res[k][1]}/{res[k][0]+res[k][1]}" for k in ("train", "eval", "holdout")))


def timing():
    now = datetime.datetime.now(datetime.timezone.utc)
    print("probe instant (UTC):", now.isoformat(), "| (SAST):", iso_r(now))
    for d in ["2026-10-27", "2026-10-28", "2026-10-29"]:
        d2 = (datetime.date.fromisoformat(d) + datetime.timedelta(days=1)).isoformat()
        r = q(C3, {"where": f"CreatedOnDT >= DATE '{d}' AND CreatedOnDT < DATE '{d2}'",
                   "returnCountOnly": "true"})
        print(f"  created {d}: {r.get('count')} rows present")


def iso_r(now):
    return (now + datetime.timedelta(hours=2)).isoformat()


def mask():
    """Billing-family mask evidence: Domestic water, mask-by-month (bounded: 2 fields)."""
    by_month = collections.defaultdict(lambda: [0, 0])
    offset = 0
    t0 = datetime.datetime.now()
    where = "Billing_Class='Domestic customers'"
    while True:
        page = q(WATER, {"where": where, "outFields": "Date,Quantity", "orderByFields": "ObjectId",
                         "resultRecordCount": 1000, "resultOffset": offset, "returnGeometry": "false"})
        feats = page.get("features") or []
        for f in feats:
            a = f["attributes"]
            m = iso(a["Date"]).strftime("%Y-%m") if a.get("Date") else "?"
            by_month[m][0] += 1
            try:
                float(a.get("Quantity"))
            except (TypeError, ValueError):
                by_month[m][1] += 1
        if len(feats) < 1000:
            break
        offset += 1000
    dt = (datetime.datetime.now() - t0).total_seconds()
    print(f"fetched {offset + len(feats)} rows in {dt:.1f}s (measured fetch cost, 2 fields)")
    for m in sorted(by_month):
        n, k = by_month[m]
        print(f"  {m}: rows={n} masked={k} ({k * 100 / n:.1f}%)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", action="store_true")
    ap.add_argument("--series")
    ap.add_argument("--surge", action="store_true")
    ap.add_argument("--timing", action="store_true")
    ap.add_argument("--mask", action="store_true")
    args = ap.parse_args()
    if args.panel:
        panel()
    if args.series:
        dc = day_counts(args.series)
        wk = collections.Counter()
        for d, n in dc.items():
            wk[week_of(d)] += n
        for w in sorted(wk):
            print(w, wk[w])
    if args.surge:
        surge()
    if args.timing:
        timing()
    if args.mask:
        mask()
    if not any([args.panel, args.series, args.surge, args.timing, args.mask]):
        print(__doc__)
        sys.exit(1)
