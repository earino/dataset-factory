"""Complete the cqc-chd-002 arbitration: verify the leap-year hypothesis
(the discovery probe hardcoded win_end=2025-01-05 = T+366d through the 2024
leap year, while the recorded contract and the build use T+365d = 2025-01-04)
and check every never-reached eval assertion under the build's rule.

Reuses the pinned files already in scratch. Counts only; no scoring."""
from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2] / "candidates" / "cqc-care-home-deregistration" / "source" / "build.py"
WORK = Path("/opt/data/cache/scratch/cqc_vintage_probe")

spec = importlib.util.spec_from_file_location("cqc_build_diag2", str(BUILD))
b = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise SystemExit("no loader")
spec.loader.exec_module(b)

vint_path = WORK / "active_2024_01.ods"
deact_path = WORK / "deactivated.ods"
assert vint_path.exists() and deact_path.exists(), "pinned files not in scratch"

deact: dict[str, dict] = {}
for kind, cells in b.ods_rows(deact_path):
    if kind == "header":
        hdr = {h.strip().lower(): i for i, h in enumerate(cells)}
        c_id, c_ch = hdr["location id"], hdr["care home?"]
        c_end, c_status = hdr["location hsca end date"], hdr["location status"]
        c_name = hdr["location name"]
        continue
    if kind != "row":
        continue
    if (cells[c_ch] or "").strip() != "Y":
        continue
    deact[(cells[c_id] or "").strip()] = {
        "end": b.dparse(cells[c_end]),
        "status": (cells[c_status] or "").strip(),
        "name": (cells[c_name] or "").strip(),
    }

pop: dict[str, dict] = {}
for kind, cells in b.sheet_rows(vint_path):
    if kind == "header":
        idx = b.resolve_header(cells)["idx"]
        continue
    if kind != "row":
        continue
    if (cells[idx["care_home"]] or "").strip() != "Y":
        continue
    lid = (cells[idx["location_id"]] or "").strip()
    pop[lid] = {
        "beds": (cells[idx["beds"]] or "").strip(),
        "rating": (cells[idx["rating"]] or "").strip(),
        "pub": b.dparse(cells[idx["pub"]]),
        "start": b.dparse(cells[idx["start"]]),
        "la": (cells[idx["la"]] or "").strip(),
    }

T = date(2024, 1, 5)
W365 = T + timedelta(days=365)     # 2025-01-04 (the recorded contract)
W366 = date(2025, 1, 5)            # the discovery probe's hardcoded win_end

print(f"pop care homes: {len(pop)} (anchor 14,765)")
print(f"T+365d = {W365}  |  probe win_end = {W366}")

ends_on_0104 = sorted(lid for lid in pop if deact.get(lid) and deact[lid]["end"] == W365)
ends_on_0105 = sorted(lid for lid in pop if deact.get(lid) and deact[lid]["end"] == W366)
print(f"pop members with HSCA end date == 2025-01-04 (T+365d): {len(ends_on_0104)}")
print(f"pop members with HSCA end date == 2025-01-05 (probe's win_end): {len(ends_on_0105)}")
for lid in ends_on_0105:
    d = deact[lid]
    print(f"  THE ONE: {lid} end={d['end']} status={d['status']!r} name={d['name']!r}")

pos365 = [lid for lid in pop if deact.get(lid) and deact[lid]["end"]
          and T < deact[lid]["end"] <= W365]
pos366 = [lid for lid in pop if deact.get(lid) and deact[lid]["end"]
          and T < deact[lid]["end"] <= W366]
print(f"positives under (T, T+365d] = {len(pos365)}  <- the recorded contract (build)")
print(f"positives under (T, 2025-01-05] = {len(pos366)}  <- the discovery probe's window")
print(f"difference ids: {sorted(set(pos366) - set(pos365))}")

later = [lid for lid in pop if lid in deact]
print(f"later_deactivated (any end): {len(later)} (anchor 2,076)")
pub_after_T = [lid for lid, r in pop.items() if r["pub"] and r["pub"] > T]
print(f"pop rows with rating Publication Date after T: {len(pub_after_T)} (anchor 0)")

for lid, want in b.FIXTURES.items():
    r = pop.get(lid)
    d = deact.get(lid)
    end = d["end"] if d else None
    label = 1 if (end and T < end <= W365) else 0
    print(f"fixture {lid}: in_pop={r is not None} end={end} "
          f"label_under_contract={label} (want {want['label']})")
