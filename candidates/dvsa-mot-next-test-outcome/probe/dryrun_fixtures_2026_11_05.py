#!/usr/bin/env python3
"""Dry-run fixtures for dvsa-mot-build-001 (coordinator, no network).

Generates synthetic per-year source files in the three file eras the build must
handle, so the whole build -> gate -> accept -> score machinery runs once before
any worker cycle is spent:

  * 2005-2008  test_result_YYYY.txt.gz  pipe-delimited, HEADERLESS, 14 columns
              (no completed_date) - exercises the positional mapping path;
  * 2009-2016  test_result_YYYY.txt.gz  pipe-delimited WITH header - the
              name-mapping path;
  * 2017-2023  dft_test_result_YYYY.zip  single CSV member, 15-column header
              WITH completed_date;
  * 2024       12 monthly members test_result_202401..202412.csv with the exact
              pinned header - exercises the vintage-pin asserts.

Vehicles are drawn from the real hash bucket (md5(vehicle_id) % 1000 == 0), carry
annual NT tests plus short-gap RT retests after failures, ABR rows, and one
byte-identical duplicate row - so dedup, abandoned-code exclusion and the
right-censoring cutoff all execute. Output lands in a scratch directory only.
"""
import gzip
import hashlib
import json
import random
import zipfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path("/opt/data/cache/scratch/dvsa-dryrun")
SOURCES = ROOT / "sources"
HEADER14 = ("test_id|vehicle_id|test_date|test_class_id|test_type|test_result|"
            "test_mileage|postcode_area|make|model|colour|fuel_type|"
            "cylinder_capacity|first_use_date")
HEADER15 = ("test_id,vehicle_id,test_date,test_class_id,test_type,test_result,"
            "test_mileage,postcode_area,make,model,colour,fuel_type,"
            "cylinder_capacity,first_use_date,completed_date")
MAKES = ["FORD", "VAUXHALL", "VOLKSWAGEN", "TOYOTA", "NISSAN", "BMW"]
MODELS = ["FIESTA", "CORSA", "GOLF", "YARIS", "MICRA", "3 SERIES"]
COLOURS = ["SILVER", "BLUE", "BLACK", "RED", "WHITE"]
FUELS = ["PE", "DI", "HY"]
AREAS = ["HG", "M", "B", "LS", "EH"]


def bucket_ids(count: int) -> list[str]:
    found = []
    candidate = 1
    while len(found) < count:
        text = str(candidate)
        if int(hashlib.md5(text.encode()).hexdigest(), 16) % 1000 == 0:
            found.append(text)
        candidate += 1
    return found


def vehicle_history(rng: random.Random, vehicle_id: str, index: int) -> list[dict]:
    first_use = date(2001 + (index % 5), 1 + (index % 12), 1 + (index % 27))
    start_year = 2005 + (index % 4)
    month = 1 + (index % 12)
    day = 1 + (index % 27)
    chronic = index % 3 == 0
    fail_probability = 0.55 if chronic else 0.18
    mileage = 8000.0 + rng.randint(0, 40000)
    tests = []
    test_counter = [100000 + index]
    year = start_year
    while year <= 2024:
        test_day = date(year, month, day)
        if test_day >= date(2025, 1, 1):
            break
        result = "F" if rng.random() < fail_probability else "P"
        if rng.random() < 0.03:
            result = "PRS" if rng.random() < 0.3 else result
        mileage += rng.randint(4000, 16000)
        test_counter[0] += 1
        tests.append({"test_id": str(test_counter[0]), "vehicle_id": vehicle_id,
                      "test_date": test_day.isoformat(), "test_class_id": "4",
                      "test_type": "NT", "test_result": result,
                      "test_mileage": f"{mileage}.0",
                      "postcode_area": AREAS[index % len(AREAS)],
                      "make": MAKES[index % len(MAKES)],
                      "model": MODELS[index % len(MODELS)],
                      "colour": COLOURS[index % len(COLOURS)],
                      "fuel_type": FUELS[index % len(FUELS)],
                      "cylinder_capacity": str(1200 + 100 * (index % 12)),
                      "first_use_date": first_use.isoformat()})
        if result in ("F", "PRS") and rng.random() < 0.8:
            retest_day = test_day + timedelta(days=rng.randint(5, 25))
            if retest_day < date(2025, 1, 1):
                mileage += rng.randint(0, 300)
                test_counter[0] += 1
                tests.append({"test_id": str(test_counter[0]),
                              "vehicle_id": vehicle_id,
                              "test_date": retest_day.isoformat(),
                              "test_class_id": "4", "test_type": "RT",
                              "test_result": "P" if rng.random() < 0.85 else "F",
                              "test_mileage": f"{mileage}.0",
                              "postcode_area": AREAS[index % len(AREAS)],
                              "make": MAKES[index % len(MAKES)],
                              "model": MODELS[index % len(MODELS)],
                              "colour": COLOURS[index % len(COLOURS)],
                              "fuel_type": FUELS[index % len(FUELS)],
                              "cylinder_capacity": str(1200 + 100 * (index % 12)),
                              "first_use_date": first_use.isoformat()})
        if rng.random() < 0.006:
            test_counter[0] += 1
            abandoned_day = test_day + timedelta(days=rng.randint(1, 40))
            if abandoned_day < date(2025, 1, 1):
                tests.append({"test_id": str(test_counter[0]),
                              "vehicle_id": vehicle_id,
                              "test_date": abandoned_day.isoformat(),
                              "test_class_id": "4", "test_type": "NT",
                              "test_result": "ABR", "test_mileage": "",
                              "postcode_area": AREAS[index % len(AREAS)],
                              "make": MAKES[index % len(MAKES)],
                              "model": MODELS[index % len(MODELS)],
                              "colour": COLOURS[index % len(COLOURS)],
                              "fuel_type": FUELS[index % len(FUELS)],
                              "cylinder_capacity": str(1200 + 100 * (index % 12)),
                              "first_use_date": first_use.isoformat()})
        year += 1
    return tests


def row_line(test: dict, delimiter: str, with_completed: bool) -> str:
    base = [test["test_id"], test["vehicle_id"], test["test_date"],
            test["test_class_id"], test["test_type"], test["test_result"],
            test["test_mileage"], test["postcode_area"], test["make"],
            test["model"], test["colour"], test["fuel_type"],
            test["cylinder_capacity"], test["first_use_date"]]
    if with_completed:
        completed = (test["test_date"] + "T14:10:35.000Z"
                     if test["test_date"] >= "2017-01-01" else "")
        base.append(completed)
    return delimiter.join(base)


def main() -> None:
    rng = random.Random(20261105)
    SOURCES.mkdir(parents=True, exist_ok=True)
    ids = bucket_ids(150)
    all_tests = []
    for index, vehicle_id in enumerate(ids):
        all_tests.extend(vehicle_history(rng, vehicle_id, index))

    # One byte-identical duplicate row (measured in the real 2024 files).
    duplicate = dict(sorted(all_tests, key=lambda t: t["test_date"])[7])
    all_tests.append(duplicate)
    # A handful of other-class rows (motorcycles) that must be skipped.
    for offset in range(3):
        other = dict(all_tests[offset * 50])
        other["test_class_id"] = "2"
        all_tests.append(other)

    by_year = {}
    for test in all_tests:
        by_year.setdefault(test["test_date"][:4], []).append(test)

    for year in range(2005, 2017):
        rows = sorted(by_year.get(str(year), []), key=lambda t: t["test_date"])
        path = SOURCES / f"source_{year}.txt.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            if year >= 2009:
                handle.write(HEADER14 + "\n")
            for test in rows:
                handle.write(row_line(test, "|", False) + "\n")

    for year in range(2017, 2024):
        rows = sorted(by_year.get(str(year), []), key=lambda t: t["test_date"])
        path = SOURCES / f"source_{year}.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            with archive.open(f"dft_test_result_{year}.csv", "w") as member:
                text = HEADER15 + "\n"
                for test in rows:
                    text += row_line(test, ",", True) + "\n"
                member.write(text.encode())

    path = SOURCES / "source_2024.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for month in range(1, 13):
            prefix = f"2024-{month:02d}"
            rows = sorted((t for t in by_year.get("2024", [])
                           if t["test_date"].startswith(prefix)),
                          key=lambda t: t["test_date"])
            text = HEADER15 + "\n"
            for test in rows:
                text += row_line(test, ",", True) + "\n"
            archive.writestr(f"test_result_2024{month:02d}.csv", text)

    summary = {"vehicles": len(ids), "tests": len(all_tests),
               "years": sorted(by_year),
               "per_year_rows": {year: len(rows) for year, rows in
                                 sorted(by_year.items())},
               "note": "synthetic fixtures for the dvsa-mot-build-001 dry run "
                       "only; never shipped, never scored as a finding"}
    (ROOT / "fixtures_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
