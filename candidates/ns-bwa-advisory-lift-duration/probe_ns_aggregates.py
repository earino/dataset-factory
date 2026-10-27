#!/usr/bin/env python3
"""Socrata aggregate probe for ns-bwa-advisory-lift-duration (discovery, 2026-10-27).

Reproduces every count in the candidate record from the live anonymous API
(data.novascotia.ca/resource/7t68-9xmm.json): totals, per-year issue counts,
censoring, distinct sites, reason/facility mixes, per-window labeled counts and
lift14/lift30 base rates, and duration-by-year means. Aggregate queries only -
no full-file fetch (that is probe_ns_csv_verify.py).
"""
import json
import urllib.request
import urllib.parse

API = "https://data.novascotia.ca/resource/7t68-9xmm.json"
UA = {"User-Agent": "scout-discovery/1.0 (dataset-factory research)"}


def soql(params):
    qs = urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{API}?{qs}", headers=UA), timeout=45) as r:
            return json.loads(r.read())
    except Exception as e:
        return [{"error": repr(e)[:150]}]


WINDOWS = [("train_2008_2017", "2008-01-01", "2017-12-31"),
           ("eval_2018_2020", "2018-01-01", "2020-12-31"),
           ("hold_2021_2024", "2021-01-01", "2024-12-31")]


def main():
    out = {}
    out["total"] = soql({"$select": "count(*)"})
    out["resolved"] = soql({"$select": "count(*)",
                            "$where": "date_advisory_removed is not null"})
    out["censored"] = soql({"$select": "count(*)",
                            "$where": "date_advisory_removed is null"})
    out["distinct_sites"] = soql({"$select": "count(distinct site_name)"})
    out["by_issue_year"] = soql({
        "$select": "date_extract_y(date_advisory_issued) as yr, count(*) as n",
        "$group": "yr", "$order": "yr", "$limit": 100})
    out["censored_by_year"] = soql({
        "$select": "date_extract_y(date_advisory_issued) as yr, count(*)",
        "$where": "date_advisory_removed is null", "$group": "yr", "$order": "yr", "$limit": 100})
    out["reasons"] = soql({"$select": "reason_for_the_report, count(*)",
                           "$group": "reason_for_the_report",
                           "$order": "count(*) DESC", "$limit": 40})
    out["facility_types"] = soql({"$select": "facility_type, count(*)",
                                  "$group": "facility_type",
                                  "$order": "count(*) DESC", "$limit": 15})
    for label, lo, hi in WINDOWS:
        w = (f"date_advisory_issued between '{lo}' and '{hi}T23:59:59' "
             "and date_advisory_removed is not null")
        out[label] = soql({
            "$select": "count(*) as n, "
                       "avg(case when length_of_advisory_in_days <= 14 then 1.0 else 0.0 end) as lift14, "
                       "avg(case when length_of_advisory_in_days <= 30 then 1.0 else 0.0 end) as lift30, "
                       "avg(length_of_advisory_in_days) as avgdur",
            "$where": w})
        out[label + "_sites"] = soql({
            "$select": "count(distinct site_name) as sites",
            "$where": f"date_advisory_issued between '{lo}' and '{hi}T23:59:59'"})
    out["duration_by_year"] = soql({
        "$select": "date_extract_y(date_advisory_issued) as yr, count(*) as n, "
                   "avg(length_of_advisory_in_days) as avgdur",
        "$group": "yr", "$order": "yr", "$limit": 50})
    with open("probe_ns_aggregates_out.json", "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
