"""Schema + label-base-rate probe: bounded ranged samples of the RODSdb occurrence CSV.

Run: python3 candidates/tsb-railway-occurrence-casualty/probe_era_samples.py

Established (2026-10-21): file ordered newest-first, spans 1983-01..2026-08
(vintage 2026-09-15); 345 columns; injury label rates by era (13.9-18.0% modern,
30.2% in 1983-84); fatality rates 5.7-6.3%; outcome-flag rates. The full file
(97.8 MB) is NOT downloaded here - discovery samples only; construction fetches
it on the worker.
"""
import csv
import io
import json
import urllib.request

from probe_access import BASE, BROWSER_HEADERS  # noqa: F401  (same header set)
OCC = "https://www.tsb.gc.ca/sites/default/files/stats/RODSdb_MDOTW_VW_OCCURRENCE_PUBLIC.csv"
TOTAL = 97_765_258


def fetch(rng):
    req = urllib.request.Request(OCC, headers={**BROWSER_HEADERS, "Range": rng})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


hdr = next(csv.reader(io.StringIO(
    fetch("bytes=0-8191").decode("cp1252", "replace").lstrip("\ufeff\ufeff").splitlines()[0])))
print(f"occurrence table: {len(hdr)} columns")


def sample(start, length):
    txt = fetch(f"bytes={start}-{start + length - 1}").decode("cp1252", "replace")
    rows = []
    for ln in txt.splitlines()[1:]:  # first line may be partial
        try:
            vals = next(csv.reader(io.StringIO(ln)))
            if len(vals) == len(hdr):
                rows.append(dict(zip(hdr, vals)))
        except StopIteration:
            pass
    return rows


for start, note in ((0, "newest"), (30_000_000, "2008-10"), (50_000_000, "2001-02"),
                    (70_000_000, "1995"), (TOTAL - 1_572_864, "1983-84 tail")):
    rows = sample(start, 2_097_152)
    inj = sum(1 for r in rows if (r.get("InjuriesIND") or "").strip().lower() in ("1", "y", "yes"))
    fatal = 0
    for r in rows:
        try:
            fatal += int((r.get("TotalFatalInjuries") or "0") or 0) > 0
        except ValueError:
            pass
    yrs = {}
    for r in rows:
        yrs[r.get("OccYear", "?")] = yrs.get(r.get("OccYear", "?"), 0) + 1
    print(f"offset {start:>11,} ({note}): n={len(rows)}, injuries={inj} ({100 * inj / max(1, len(rows)):.1f}%), "
          f"fatalities>0={fatal} ({100 * fatal / max(1, len(rows)):.1f}%), years={json.dumps(yrs)}")
