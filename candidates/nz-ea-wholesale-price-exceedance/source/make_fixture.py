#!/usr/bin/env python3
"""Generate a synthetic fixture for locally exercising the nz-ea build.

Everything here is FABRICATED: no source bytes are read and no number from the
output may be quoted as a finding. The only purpose is to run build.py's full
code path (aggregation, channel ownership, panel construction, writers) and
then the qualification gate, so declaration errors surface before a paid
worker is launched.

Layout mirrors the real channel split: monthly files YYYYMM (owning dates
<= 2025-10-31) and daily files YYYYMMDD (owning dates > 2025-10-31), plus a
mini NetworkSupplyPointsTable.
"""
import argparse
import csv
import math
from datetime import date, timedelta
from pathlib import Path

DEFAULT_OUT = "/opt/data/cache/scratch/nz-ea-fixture"
FIRST = date(2024, 1, 1)
LAST = date(2026, 9, 30)
POCS = [("NIA0111", "NI", 1.0), ("NIB0111", "NI", 0.9), ("SIA0111", "SI", 1.05), ("SIB0111", "SI", 0.95)]

# high-price windows (start, length) per year, deterministic
BLOCKS = {
    2024: [(date(2024, 6, 3), 14), (date(2024, 7, 15), 12)],
    2025: [(date(2025, 1, 2) + timedelta(days=15 * i), 8) for i in range(24)],
    2026: [(date(2026, 1, 2) + timedelta(days=9 * i), 6) for i in range(31)],
}


def level(day: date) -> float:
    high = False
    for start, length in BLOCKS.get(day.year, []):
        if start <= day < start + timedelta(days=length):
            high = True
            break
    ordinal = day.toordinal()
    base = 40 + 25 * math.sin(2 * math.pi * ordinal / 37.0) \
        + 12 * math.sin(2 * math.pi * ordinal / 13.7) \
        + 5 * math.sin(2 * math.pi * ordinal / 3.1)
    return 150.0 + base if high else base


def main(out: str = DEFAULT_OUT) -> None:
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    for path in out_path.glob("*.csv"):
        path.unlink()
    with (out_path / "nsp.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["POC code", "Network reporting region", "Island", "Start date", "End date"])
        for code, island, _factor in POCS:
            writer.writerow([code, f"Region {island}", island, "2020-01-01", ""])

    # monthly files through 202510 (their dates are all <= 2025-10-31)
    day = FIRST
    monthly: dict[str, list] = {}
    while day <= LAST:
        if day <= date(2025, 10, 31):
            monthly.setdefault(day.strftime("%Y%m"), []).append(day)
        day += timedelta(days=1)
    for ym, days in sorted(monthly.items()):
        with (out_path / f"{ym}_FinalEnergyPrices.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["TradingDate", "TradingPeriod", "PointOfConnection",
                             "DollarsPerMegawattHour"])
            for one in days:
                for period in range(1, 49):
                    for code, _island, factor in POCS:
                        writer.writerow([one.isoformat(), period, code,
                                         round(level(one) * factor + 0.7 * math.sin(period), 4)])
    # daily files for dates owned by the daily channel (> 2025-10-31)
    day = date(2025, 11, 1)
    while day <= LAST:
        with (out_path / f"{day.strftime('%Y%m%d')}_FinalEnergyPrices.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["TradingDate", "TradingPeriod", "PointOfConnection",
                             "DollarsPerMegawattHour"])
            for period in range(1, 49):
                for code, _island, factor in POCS:
                    writer.writerow([day.isoformat(), period, code,
                                     round(level(day) * factor + 0.7 * math.sin(period), 4)])
        day += timedelta(days=1)
    print(f"fixture written to {out_path}: {len(monthly)} monthly files, "
          f"{(LAST - date(2025, 11, 1)).days + 1} daily files")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT)
