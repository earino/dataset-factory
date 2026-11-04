"""Verify the three dated fixtures' FULL field set against the real pinned
bytes (2024-01 vintage + deactivated, both in scratch), so the corrected
assert_fixtures field mapping is evidence-backed before any relaunch.
Checks: label, beds, local_authority, latest_overall_rating, rating
publication date, HSCA start date - exactly what FIXTURES wants to assert."""
from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2] / "candidates" / "cqc-care-home-deregistration" / "source" / "build.py"
WORK = Path("/opt/data/cache/scratch/cqc_vintage_probe")

spec = importlib.util.spec_from_file_location("cqc_build_fx", str(BUILD))
b = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise SystemExit("no loader")
spec.loader.exec_module(b)

vint_path = WORK / "active_2024_01.ods"
deact_path = WORK / "deactivated.ods"

deact = {}
for kind, cells in b.ods_rows(deact_path):
    if kind == "header":
        hdr = {h.strip().lower(): i for i, h in enumerate(cells)}
        c_id, c_ch = hdr["location id"], hdr["care home?"]
        c_end = hdr["location hsca end date"]
        continue
    if kind != "row":
        continue
    if (cells[c_ch] or "").strip() != "Y":
        continue
    deact[(cells[c_id] or "").strip()] = b.dparse(cells[c_end])

rows = {}
for kind, cells in b.sheet_rows(vint_path):
    if kind == "header":
        idx = b.resolve_header(cells)["idx"]
        continue
    if kind != "row":
        continue
    if (cells[idx["care_home"]] or "").strip() != "Y":
        continue
    lid = (cells[idx["location_id"]] or "").strip()
    rows[lid] = {
        "beds": (cells[idx["beds"]] or "").strip(),
        "la": (cells[idx["la"]] or "").strip(),
        "rating": (cells[idx["rating"]] or "").strip(),
        "pub_raw": (cells[idx["pub"]] or "").strip(),
        "pub": b.dparse(cells[idx["pub"]]),
        "start_raw": (cells[idx["start"]] or "").strip(),
        "start": b.dparse(cells[idx["start"]]),
    }

T = date(2024, 1, 5)
W = T + timedelta(days=365)

# the row values build_panel will derive
for lid, want in b.FIXTURES.items():
    r = rows.get(lid)
    print(f"== fixture {lid} ==")
    if r is None:
        print("  NOT IN POPULATION")
        continue
    end = deact.get(lid)
    label = 1 if (end and T < end <= W) else 0
    print(f"  label: {label} (want {want['label']})")
    print(f"  care_home_beds: {r['beds']!r} (want {want.get('beds')})")
    print(f"  local_authority: {r['la']!r} (want {want.get('la')})")
    print(f"  latest_overall_rating: {r['rating']!r} (want {want.get('rating')})")
    print(f"  pub: raw {r['pub_raw']!r} parsed {r['pub']} "
          f"(want {want.get('pub')})")
    print(f"  start: raw {r['start_raw']!r} parsed {r['start']} "
          f"(want {want.get('start')})")

# fixture-assert mapping the fix will use, checked here on real bytes
FIELD_MAP = {
    "label": None,                      # -> row[TARGET]
    "beds": "care_home_beds",
    "la": "local_authority",
    "rating": "latest_overall_rating",
    "pub": "_pub",
    "start": "_start",
}
ok = True
for lid, want in b.FIXTURES.items():
    r = rows.get(lid)
    if r is None:
        ok = False
        continue
    end = deact.get(lid)
    label = 1 if (end and T < end <= W) else 0
    row = {"care_home_beds": int(r["beds"]) if r["beds"].isdigit() else -1,
           "local_authority": r["la"],
           "latest_overall_rating": r["rating"] or "Not rated",
           "_pub": r["pub"].strftime("%d/%m/%Y") if r["pub"] else "",
           "_start": r["start"].strftime("%Y") if r["start"] else "",
           b.TARGET: label}
    for field, value in want.items():
        key = FIELD_MAP[field]
        got = row[b.TARGET] if field == "label" else row[key]
        if field == "start":
            match = str(got) == str(value)[-4:]      # want "01/02/2011" -> start year
        elif field == "pub":
            match = str(got) == str(value)
        else:
            match = str(got) == str(value)
        print(f"  fixture {lid} field {field}: got {got!r} want {value!r} "
              f"-> {'OK' if match else 'MISMATCH'}")
        ok = ok and match
print(f"\nALL FIXTURE FIELDS VERIFY ON REAL PINNED BYTES: {ok}")
