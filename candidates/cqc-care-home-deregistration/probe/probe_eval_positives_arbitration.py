"""Arbitrate the 757-vs-758 eval-positives discrepancy (cqc-chd-002 failure).

The build (read_vintage + build_panel join) counted 757 positives among the
14,765 care homes active at T=2024-01-05; the 2026-11-03 discovery
measurement (probe/cqc_example.py) recorded 758. Both source files are pinned
and byte-identical to the discovery bytes (2024-01 vintage digest
ac40b6f8/26,147,266 B asserted in-build; deactivated 49dc3062/27,644,723 B
pin re-verified pre-launch and the deactivated index matched the anchor
exactly: 65,830/17,177/0). So the difference is a join/rule difference
between the probe and the build, not source drift.

This diagnostic is a THIRD independent implementation over the same pinned
bytes. It measures, without scoring anything:
  1. the care-home population of the 2024-01 vintage (expect 14,765);
  2. positives under the recorded contract (T, T+365d]  (build says 757);
  3. positives under [T, T+365d] (end == T included) - boundary rule A;
  4. positives under (T, T+365d) (end == T+365d excluded) - boundary rule B;
  5. positives counted WITHOUT intersecting the vintage population (all
     deactivated care homes ending in the window) - population rule C;
  6. the exact location id(s) responsible for any difference, with end
     date and status (bounded dated evidence).

Bounded: two pinned files fetched one at a time into scratch (~54 MB),
only counts + the differing ids retained.
"""
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[2] / "candidates" / "cqc-care-home-deregistration" / "source" / "build.py"
WORK = Path("/opt/data/cache/scratch/cqc_vintage_probe")

spec = importlib.util.spec_from_file_location("cqc_build_diag", str(BUILD))
b = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise SystemExit("no loader")
spec.loader.exec_module(b)

WORK.mkdir(parents=True, exist_ok=True)

# --- fetch the two pinned inputs -------------------------------------------
stats: dict = {}
print("== fetching 2024-01 vintage (digest-pinned) ==", flush=True)
vint_path, T = b.download_vintage(2024, WORK, stats)
print(f"vintage: {vint_path.name} T={T} pinned={stats['vintages']['2024'].get('pinned')}", flush=True)
print("== fetching deactivated (pin re-check) ==", flush=True)
deact_path = b.download_deactivated(WORK, stats)
print(f"deactivated: {deact_path.name} (pin holds, else download_deactivated raised)", flush=True)

# --- deactivated index (independent) ----------------------------------------
deact: dict[str, dict] = {}
for kind, cells in b.ods_rows(deact_path):
    if kind == "header":
        hdr = {h.strip().lower(): i for i, h in enumerate(cells)}
        c_id = hdr["location id"]
        c_ch = hdr["care home?"]
        c_end = hdr["location hsca end date"]
        c_status = hdr["location status"]
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
print(f"deactivated care homes indexed: {len(deact)}", flush=True)

# --- vintage population (independent) ---------------------------------------
pop: dict[str, dict] = {}
for kind, cells in b.sheet_rows(vint_path):
    if kind == "header":
        res = b.resolve_header(cells)
        idx = res["idx"]
        continue
    if kind != "row":
        continue
    if (cells[idx["care_home"]] or "").strip() != "Y":
        continue
    pop[(cells[idx["location_id"]] or "").strip()] = {
        "end": None,
    }
print(f"vintage care homes at T: {len(pop)}", flush=True)

W = timedelta(days=365)

def positives(rule) -> list[str]:
    out = []
    for lid in pop:
        d = deact.get(lid)
        if d is None or d["end"] is None:
            continue
        if rule(d["end"]):
            out.append(lid)
    return out

strict = positives(lambda e: T < e <= T + W)          # the recorded contract
incl_T = positives(lambda e: T <= e <= T + W)          # boundary rule A
excl_end = positives(lambda e: T < e < T + W)          # boundary rule B

# population rule C: no intersection with the vintage population
window_all = [lid for lid, d in deact.items()
              if d["end"] is not None and T < d["end"] <= T + W]

print(f"positives (T, T+365]  = {len(strict)}   <- the build's rule")
print(f"positives [T, T+365]  = {len(incl_T)}   (end == T included)")
print(f"positives (T, T+365)  = {len(excl_end)}   (end == T+365 excluded)")
print(f"deactivated care homes ending in (T, T+365] WITHOUT population "
      f"intersection = {len(window_all)}")

diff_a = sorted(set(incl_T) - set(strict))
diff_b = sorted(set(strict) - set(excl_end))
print(f"rule-A difference ids (end == T): {diff_a}")
for lid in diff_a:
    print(f"  {lid}: end={deact[lid]['end']} status={deact[lid]['status']!r} "
          f"name={deact[lid]['name']!r}")
print(f"rule-B difference ids (end == T+365d = {T + W}): {diff_b}")
for lid in diff_b:
    print(f"  {lid}: end={deact[lid]['end']} status={deact[lid]['status']!r} "
          f"name={deact[lid]['name']!r}")
not_in_pop = sorted(set(window_all) - set(strict))
print(f"window-enders NOT in the vintage population: {len(not_in_pop)}")
for lid in not_in_pop[:12]:
    print(f"  {lid}: end={deact[lid]['end']} status={deact[lid]['status']!r} "
          f"name={deact[lid]['name']!r}")

# status mix of the strict positives
mix = Counter(deact[lid]["status"] for lid in strict)
print(f"strict-positive status mix: {dict(mix)}")
