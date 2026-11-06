#!/usr/bin/env python3
"""Discovery probe: OpenEFSA question API - health-claims application counts.

Reproduces the 2026-11-06 measurements recorded in record.json/notes.md.

The OpenEFSA API (https://open.efsa.europa.eu/api/...) answers anonymous HTTP
only with the SPA-computed header  x-security: 123*floor(epoch_seconds)+369
(found in main.<hash>.js, module 57591, read 2026-11-06). Without it the API
returns System.UnauthorizedAccessException "Security string is not valid".

Measures, with one small call per year (limit=1, totalCount + status facet):
  - health-claims (authorisationType=Health Claims, type=Application) questions
    by dossier-received year 2006..2026, with the status mix
    (Published / Application Withdrawn / Intake / Ongoing Risk Assessment);
  - optionally one question's event timeline: --timeline EFSA-Q-2021-00073

Run:  python3 probe_openefsa.py [--timeline EFSA-Q-YYYY-NNNNN]
"""
import json
import subprocess
import sys
import time

BASE = ("https://open.efsa.europa.eu/api/question/searchAdvanced"
        "?offset=0&limit=1&foodDomains=Nutrition"
        "&authorisationType=Health%20Claims&type=Application")


def sec():
    return 123 * int(time.time()) + 369


def call(url):
    r = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-H", f"x-security: {sec()}", url],
        capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def year_counts():
    for y in range(2006, 2027):
        d = call(f"{BASE}&dossierReceivedMinDate={y}-01-01"
                 f"&dossierReceivedMaxDate={y}-12-31")["data"]
        st = {v["label"]: v["count"] for f in d["facets"]
              if f.get("urlParamKey") == "status" for v in f.get("values", [])}
        print(f"{y}: total={d['totalCount']:4d} "
              f"pub={st.get('Published', 0):4d} "
              f"withdr={st.get('Application Withdrawn', 0):3d} "
              f"intake={st.get('Intake', 0):4d} "
              f"ongoing={st.get('Ongoing Risk Assessment', 0):2d}")


def timeline(qn):
    d = call("https://open.efsa.europa.eu/api/question/"
             f"getTimeline?questionNumber={qn}")["data"]
    for e in sorted(d, key=lambda x: str(x.get("date"))):
        print(f"  {str(e.get('date'))[:10]}  {e.get('title')}")


if __name__ == "__main__":
    if "--timeline" in sys.argv:
        timeline(sys.argv[sys.argv.index("--timeline") + 1])
    else:
        year_counts()
