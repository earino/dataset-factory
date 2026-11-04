"""Bounded vintage-schema probe for the cqc-chd-001 failure (jobs[0].next_check).

Diff the care-home-identifying column's value domain between the January
vintages that build (2018 xlsx, 2022 ods) and the three that built 0 care-home
rows (2019/2020/2021 xlsx), naming the exact drift for the build.py filter
fix. Uses build.py's own download recipe, header resolution and sheet readers
so the probe measures what the build measures. Bounded: files fetched one at
a time into scratch, only header lists + value domains + counts retained.

Output: probe/vintage_schema_out.json (committed evidence; no row data).
Run on the coordinator (stdlib only, ~130 MB transient in scratch).
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BUILD = REPO / "candidates" / "cqc-care-home-deregistration" / "source" / "build.py"
WORK = Path("/opt/data/cache/scratch/cqc_vintage_probe")

spec = importlib.util.spec_from_file_location("cqc_build_probe", BUILD)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

WORK.mkdir(parents=True, exist_ok=True)

# 2018 (xlsx) and 2022 (ods) build care-home rows; 2019/2020/2021 (xlsx) built 0.
YEARS = [2018, 2019, 2020, 2021, 2022]

CARE_HEADER_RE = re.compile(r"care\s*home", re.I)


def domain_summary(counter: Counter, top: int = 25) -> dict:
    return {
        "distinct_values": len(counter),
        "top": [{"value": v if v != "" else "<EMPTY>", "count": n}
                for v, n in counter.most_common(top)],
        "total_observed": sum(counter.values()),
    }


def probe_vintage(year: int, stats: dict) -> dict:
    path, T = b.download_vintage(year, WORK, stats)
    header: list[str] = []
    resolution = None
    care_cols: dict[int, tuple[str, Counter]] = {}
    rows = 0
    pass_current_filter = 0
    pass_startswith_y = 0
    pass_yes = 0
    for kind, cells in b.sheet_rows(path):
        if kind == "header":
            header = [(h or "").strip() for h in cells]
            resolution = b.resolve_header(cells)
            care_cols = {}
            for i, h in enumerate(header):
                if CARE_HEADER_RE.search(h):
                    care_cols[i] = (header[i], Counter())
            continue
        if kind != "row" or not header:
            continue
        rows += 1
        idx = resolution["idx"]
        matched = idx.get("care_home")
        if matched is not None and matched < len(cells):
            v = (cells[matched] or "").strip()
            if v == "Y":
                pass_current_filter += 1
            if v.upper().startswith("Y"):
                pass_startswith_y += 1
            if v.upper() == "YES":
                pass_yes += 1
        for i, (_, counter) in care_cols.items():
            counter[(cells[i] if i < len(cells) else "") or ""] += 1

    vint = stats["vintages"][str(year)]
    matched = resolution["idx"].get("care_home") if resolution else None
    return {
        "year": year,
        "instant_T": T.isoformat(),
        "file": vint["file"], "drive_id": vint["drive_id"],
        "bytes": vint["bytes"], "sha256": vint["sha256"],
        "data_rows": rows,
        "header_columns": [[i, h] for i, h in enumerate(header)],
        "resolved_required": {k: v for k, v in (resolution["idx"] if resolution else {}).items()},
        "missing_required": [f for f, pat in b.REQUIRED_FIELDS.items()
                              if resolution is None or f not in resolution["idx"]],
        "care_home_matched": None if matched is None else {
            "index": matched, "header_text": header[matched] if matched < len(header) else None},
        "care_home_header_columns": {
            f"col[{i}] {text!r}": domain_summary(counter)
            for i, (text, counter) in sorted(care_cols.items())},
        "service_type_labels": [lbl for _, lbl in (resolution["svc_types"] if resolution else [])],
        "user_band_labels": [lbl for _, lbl in (resolution["user_bands"] if resolution else [])],
        "rows_passing_current_filter_eqY": pass_current_filter,
        "rows_passing_startswithY": pass_startswith_y,
        "rows_passing_eqYES": pass_yes,
    }


def main() -> int:
    stats: dict = {}
    out: dict = {
        "probe": "vintage_schema",
        "purpose": ("cqc-chd-001 jobs[0].next_check: care-home-identifying "
                    "column value domains, active_2018_01 vs "
                    "active_2019/2020/2021_01 (+2022 ods control)"),
        "generated_by": "probe/probe_vintage_schema.py",
        "vintages": {},
    }
    for year in YEARS:
        print(f"== probing January {year} vintage ==", flush=True)
        info = probe_vintage(year, stats)
        out["vintages"][str(year)] = info
        print(json.dumps({k: info[k] for k in
                          ("year", "data_rows", "rows_passing_current_filter_eqY",
                           "rows_passing_startswithY", "rows_passing_eqYES",
                           "missing_required")}), flush=True)
    dest = HERE / "vintage_schema_out.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"written: {dest}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
