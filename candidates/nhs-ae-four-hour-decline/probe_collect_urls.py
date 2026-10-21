#!/usr/bin/env python3
"""Probe: collect NHS England monthly A&E CSV URLs from all year pages."""
import re
import urllib.request
import json

BASE = "https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

YEAR_PAGES = [
    "ae-attendances-and-emergency-admissions-2026-27/",
    "ae-attendances-and-emergency-admissions-2025-26/",
    "ae-attendances-and-emergency-admissions-2024-25/",
    "ae-attendances-and-emergency-admissions-2023-24/",
    "ae-attendances-and-emergency-admissions-2022-23/",
    "ae-attendances-and-emergency-admissions-2021-22/",
    "ae-attendances-and-emergency-admissions-2020-21/",
    "ae-attendances-and-emergency-admissions-2019-20/",
    "ae-attendances-and-emergency-admissions-2018-19/",
    "ae-attendances-and-emergency-admissions-2017-18/",
    "statistical-work-areasae-waiting-times-and-activityae-attendances-and-emergency-admissions-2016-17/",
    "statistical-work-areasae-waiting-times-and-activityae-attendances-and-emergency-admissions-2015-16-monthly-3/",
]

out = {}
for page in YEAR_PAGES:
    url = BASE + page
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:
        out[page] = {"error": repr(e)}
        continue
    # monthly CSV links: exclude ECDS and system-mapping files
    links = re.findall(r'https://www\.england\.nhs\.uk/statistics/wp-content/uploads/sites/2/[^"\']*?\.csv',
                       html)
    monthly = [u for u in links if not re.search(r'ECDS', u, re.I)]
    out[page] = {"n_csv_links": len(links), "n_monthly": len(monthly),
                 "monthly": monthly}

with open("/opt/data/cache/scratch/ae_csv_urls.json", "w") as f:
    json.dump(out, f, indent=1)
for k, v in out.items():
    print(k, v.get("n_csv_links"), v.get("n_monthly"), v.get("error", ""))
    for u in v.get("monthly", [])[:3]:
        print("   ", u.split("/")[-1])
    if len(v.get("monthly", [])) > 3:
        print("    ... total", len(v["monthly"]))
