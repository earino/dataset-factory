#!/usr/bin/env python3
"""Discovery probe: cross-check the Alberta per-fire CSV against the publisher's
own season statistics (the publisher's summary product) and measure
label-revision sensitivity near candidate thresholds.

Published figures quoted from Alberta Wildfire's seasonal statistics PDFs
(open.alberta.ca/publications/alberta-wildfire-season-statistics, e.g.
fp-alberta-wildfire-seasonal-statistics-2024.pdf, read 2026-11-06):
  2019: 883,411 ha | 2020: 3,269 ha | 2021: 54,047 ha | 2022: 130,858 ha
  2023: 2,211,900 ha | 2024: 708,528 ha
The CSV is year-round (winter wildfires included) and carries the current
revised area burned; the season PDFs are as-of their publication dates.

Usage: python3 probe_publisher_crosscheck.py <csv-path> <out-json>
"""
import csv
import json
import sys
from collections import defaultdict

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else \
    "/opt/data/cache/scratch/ab-wildfire/fp-historical-wildfire-data-2006-2025.csv"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "probe_publisher_crosscheck_result.json"

PUBLISHED_SEASON_HA = {2019: 883411, 2020: 3269, 2021: 54047, 2022: 130858,
                       2023: 2211900, 2024: 708528}


def main():
    rows = list(csv.DictReader(open(CSV_PATH, newline="", encoding="utf-8-sig")))
    ha = defaultdict(float)
    n = defaultdict(int)
    for r in rows:
        y = int(r["YEAR"])
        n[y] += 1
        try:
            ha[y] += float(r["CURRENT_SIZE"])
        except (TypeError, ValueError):
            pass
    comp = {}
    for y, pub in sorted(PUBLISHED_SEASON_HA.items()):
        comp[str(y)] = {"csv_fires": n[y], "csv_hectares": round(ha[y]),
                        "published_season_hectares": pub,
                        "ratio_current_over_published": round(ha[y] / pub, 4)}
    # label-revision sensitivity: fires within +-20% of a threshold
    sens = {}
    for th in (4, 10, 40, 100, 200):
        band = sum(1 for r in rows
                   if th * 0.8 <= float(r["CURRENT_SIZE"] or 0) <= th * 1.2)
        sens[f"within_20pct_of_{th}ha"] = {"fires": band,
                                           "share": round(band / len(rows), 5)}
    out = {"n_rows": len(rows), "hectares_crosscheck": comp,
           "label_revision_sensitivity": sens}
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
