#!/usr/bin/env python3
"""End-to-end synthetic test for the za-cct-substation-evening-peak-exceedance build.

Drives the real build.py over synthetic FeatureServer pages (3 stations x 3
years, deterministic, no network), then the real qualification gate over the
written extract, then --accept, then score.py against the accepted report.

What this test pins, and why each part exists:

1. The full worker order on fake bytes: construct -> gate -> exact-byte accept
   -> references. A failure here is caught before any worker launch (the acnc
   precedent: four real defects were caught by exactly this loop).

2. The P0 design rationale, on synthetic data only: the day-over-day delta of
   a sliding EVENING p95 reconstructs the entering evening's exceedance label
   with high agreement (the fts-appeal-003 lesson), while the same attack on
   the shipped MORNING mean agrees far less. That asymmetry is WHY the shipped
   frame carries no evening-derived column. Synthetic-only by construction:
   no real data, no real labels, no task measurement.

3. The gate bites on operand shipping: a mutated extract that ships the
   evening peak as a column while declaring it a label source must FAIL the
   gate's leakage check (red/green, reverted after the demonstration).

4. Determinism: two builds at the same --built-at produce byte-identical CSVs.

Run from the repository root:
    python3 tests/test_za_cct_build.py
"""
import csv
import datetime
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "candidates/za-cct-substation-evening-peak-exceedance/source")
BUILD = os.path.join(SOURCE, "build.py")
SCORE = os.path.join(SOURCE, "score.py")
GATE = os.path.join(ROOT, "skills/dataset-qualification/scripts/qualify_dataset.py")

STATIONS = ["Alpha_66kV", "Bravo_33kV", "Charlie_132kV"]
YEARS = [2021, 2022, 2023]          # train / eval / holdout by year
SAST = datetime.timezone(datetime.timedelta(hours=2))
BUILT_AT = "2026-11-03T00:00:00Z"


def day_factor(seed_key: str) -> float:
    """Deterministic day regime: ~8% of days are 1.30x spike days."""
    digest = int(hashlib.sha256(seed_key.encode()).hexdigest()[:8], 16)
    return 1.30 if (digest % 1000) / 1000 < 0.08 else 1.0


def noise(seed_key: str) -> float:
    digest = int(hashlib.sha256(seed_key.encode()).hexdigest()[:12], 16)
    return 0.90 + 0.20 * (digest % 1000) / 1000.0


def synthetic_value(station: str, day: str, hour: int, minute: int) -> float:
    base = 40.0 + 7.0 * STATIONS.index(station)
    date = datetime.date.fromisoformat(day)
    doy = date.timetuple().tm_yday
    season = 1.0 + 0.25 * math.sin(2 * math.pi * (doy - 105) / 365.25)
    regime = day_factor(f"day:{day}")
    # night load responds only partially to a day regime spike (imperfect
    # morning/evening coupling, as in a real grid)
    slot_shape = 1.0
    if hour < 6:
        slot_shape = 0.55 + 0.10 * (hour + minute / 60.0) / 6.0
        regime_response = 1.0 + 0.5 * (regime - 1.0)
    elif 16 <= hour < 22:
        slot_shape = 1.35
        regime_response = regime
    else:
        slot_shape = 0.8
        regime_response = 1.0 + 0.2 * (regime - 1.0)
    jitter = noise(f"slot:{station}:{day}:{hour}:{minute}")
    return round(base * season * regime_response * slot_shape * jitter, 4)


def write_pages(directory: str) -> None:
    features, page = [], 0

    def flush():
        nonlocal page
        path = os.path.join(directory, f"page-{page:03d}.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"features": [{"attributes": a} for a in features]}, handle)
        page += 1

    batch = []
    for year in YEARS:
        day = datetime.date(year, 1, 1)
        while day.year == year:
            for half_hour in range(48):
                dt = datetime.datetime(day.year, day.month, day.day,
                                       half_hour // 2, 30 * (half_hour % 2),
                                       tzinfo=SAST)
                epoch_ms = int(dt.timestamp() * 1000)
                row = {"Timestamp": epoch_ms}
                for station in STATIONS:
                    row[station] = synthetic_value(station, day.isoformat(),
                                                   dt.hour, dt.minute)
                batch.append(row)
                if len(batch) == 1000:
                    features = batch[:1000]
                    flush()
                    batch = batch[1000:]
            day += datetime.timedelta(days=1)
    if batch:
        features = batch
        flush()


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return result


def digest(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main() -> int:
    work = tempfile.mkdtemp(prefix="za-cct-test-")
    try:
        pages = os.path.join(work, "pages")
        os.makedirs(pages)
        write_pages(pages)
        extract = os.path.join(work, "extract")

        # ---- 1. construct on synthetic pages --------------------------------
        run([sys.executable, BUILD, "--out", extract, "--work-dir",
             os.path.join(work, "scratch"), "--pages-dir", pages,
             "--built-at", BUILT_AT, "--summary-out",
             os.path.join(work, "summary.json")])
        summary = json.load(open(os.path.join(work, "summary.json")))
        splits = summary["split_stats"]
        assert splits["train"]["rows"] == 3 * (365 - 30), splits
        assert splits["eval"]["rows"] == 3 * 365, splits
        assert splits["holdout"]["rows"] == 3 * 365, splits
        for name in ("eval", "holdout"):
            assert 0 < splits[name]["positives"] < splits[name]["rows"], splits
            assert splits[name]["distinct_positive_days"] >= 20, splits
        assert summary["exclusions"]["burn_in_under_30_prior_evenings"] == 3 * 30

        # evening-derived columns must not ship in any split
        for relative in ("public/train.csv", "public/eval.csv", "private/holdout.csv"):
            with open(os.path.join(extract, relative)) as handle:
                header = next(csv.reader(handle))
            assert "evening_peak_mva" not in header, header
            assert "trailing_evening_p95_mva" not in header, header
            assert "exceeds" in header

        # ---- 2. the real gate over the synthetic extract ----------------------
        report_path = os.path.join(work, "qualification.json")
        run([sys.executable, GATE, extract, "--json", "--report", report_path])
        report = json.load(open(report_path))
        failed = report["failed_checks"]
        assert not failed, f"gate failed on the synthetic artifact: {failed}"
        assert report["ok"] is True

        # the declared cross-row probe must have run with coverage (exposure
        # demonstrated) and be accepted only because access is isolated_rows
        probe = next(r for r in report["results"]
                     if r["check"] == "contract.cross_row_probe_0")
        assert probe["ok"] is True
        covered = {split: v["covered"] for split, v in probe["evidence"].items()}
        mismatches = {split: v["mismatches"] for split, v in probe["evidence"].items()}
        assert sum(covered.values()) > 0, covered

        # ---- 3. exact-byte acceptance -----------------------------------------
        accept = run([sys.executable, GATE, "--accept", report_path, extract])
        assert "ACCEPTED" in accept.stdout, accept.stdout

        # ---- 4. references only after acceptance ------------------------------
        references_path = os.path.join(work, "references.json")
        run([sys.executable, SCORE, "--data", extract,
             "--accepted-report", report_path, "--report", references_path])
        references = json.load(open(references_path))
        assert references["references"]["persistence_prev_evening"]["eval_auc"] is not None

        # score.py must refuse to run against a non-matching report
        mutated_report = dict(report)
        mutated_report["artifact"] = dict(report["artifact"])
        mutated_report["artifact"]["train"] = dict(report["artifact"]["train"])
        mutated_report["artifact"]["train"]["sha256"] = "0" * 64
        bad_report = os.path.join(work, "bad-report.json")
        open(bad_report, "w").write(json.dumps(mutated_report))
        refused = subprocess.run([sys.executable, SCORE, "--data", extract,
                                  "--accepted-report", bad_report,
                                  "--report", os.path.join(work, "x.json")],
                                 capture_output=True, text=True)
        assert refused.returncode != 0, "score.py must refuse a stale report"

        # ---- 5. the P0 design rationale, synthetic only ----------------------
        # The sliding EVENING p95 delta attack vs the shipped MORNING mean
        # delta attack, both computed on the synthetic evening matrix. The
        # evening column must not ship precisely because the first agrees with
        # the label far more than the second.
        import math
        evening = {s: {} for s in STATIONS}
        for year in YEARS:
            day = datetime.date(year, 1, 1)
            while day.year == year:
                for station in STATIONS:
                    evening[station][day.isoformat()] = max(
                        synthetic_value(station, day.isoformat(), h, m)
                        for h in range(16, 22) for m in (0, 30))
                day += datetime.timedelta(days=1)
        agree = {"evening_p95_delta": [0, 0], "morning_mean_delta": [0, 0]}
        # agree[attack] = [matches, total]: does the delta attack reproduce
        # the label exactly? (the P0 question, on synthetic bytes only)
        for station in STATIONS:
            days = sorted(evening[station])
            morning_peak = {}
            for day in days:
                morning_peak[day] = max(
                    synthetic_value(station, day, h, m)
                    for h in range(0, 6) for m in (0, 30))
            for i in range(30, len(days) - 1):
                hist = [evening[station][d] for d in days[max(0, i - 90):i]]
                p95 = sorted(hist)[int(0.95 * (len(hist) - 1))]
                label = 1 if evening[station][days[i]] > p95 else 0
                nxt = [evening[station][d] for d in days[max(0, i - 89):i + 1]]
                pred_eve = 1 if sorted(nxt)[int(0.95 * (len(nxt) - 1))] > p95 else 0
                mh = [morning_peak[d] for d in days[max(0, i - 90):i]]
                nxtm = [morning_peak[d] for d in days[max(0, i - 89):i + 1]]
                pred_mor = 1 if sum(nxtm) / len(nxtm) > sum(mh) / len(mh) else 0
                agree["evening_p95_delta"][0] += int(pred_eve == label)
                agree["evening_p95_delta"][1] += 1
                agree["morning_mean_delta"][0] += int(pred_mor == label)
                agree["morning_mean_delta"][1] += 1
        evening_agree = agree["evening_p95_delta"][0] / agree["evening_p95_delta"][1]
        morning_agree = agree["morning_mean_delta"][0] / agree["morning_mean_delta"][1]
        print(f"synthetic delta-attack agreement: evening p95 {evening_agree:.3f} "
              f"vs shipped morning mean {morning_agree:.3f} "
              f"(probe mismatches on the artifact: {mismatches})")
        assert evening_agree > morning_agree + 0.10, (
            "the synthetic demonstration no longer supports the design: "
            f"evening {evening_agree:.3f} vs morning {morning_agree:.3f}")

        # ---- 6. red/green: shipping the operand must fail the gate -----------
        mutant = os.path.join(work, "mutant")
        shutil.copytree(extract, mutant)
        aux = os.path.join(mutant, "auxiliary", "evening_peaks.csv")
        with open(aux) as handle:
            peaks = {(row["station"], row["date"]): row["evening_peak_mva"]
                     for row in csv.DictReader(handle)}
        for relative in ("public/train.csv", "public/eval.csv", "private/holdout.csv"):
            path = os.path.join(mutant, relative)
            with open(path) as handle:
                rows = list(csv.reader(handle))
            header, body = rows[0], rows[1:]
            station_i, date_i = header.index("station"), header.index("date")
            header = header[:-1] + ["evening_peak_mva", header[-1]]
            with open(path, "w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                for row in body:
                    value = peaks[(row[station_i], row[date_i])]
                    writer.writerow(row[:-1] + [value, row[-1]])
        quality_path = os.path.join(mutant, "quality.json")
        quality = json.load(open(quality_path))
        quality["label_source_columns"] = list(quality["label_source_columns"]) + [
            "evening_peak_mva"]
        quality["features"] = list(quality["features"]) + ["evening_peak_mva"]
        quality["shipped_columns"] = list(quality["shipped_columns"]) + [
            "evening_peak_mva"]
        json.dump(quality, open(quality_path, "w"), indent=1, sort_keys=True)
        mutant_report = os.path.join(work, "mutant-qualification.json")
        red = subprocess.run([sys.executable, GATE, mutant, "--json",
                              "--report", mutant_report],
                             capture_output=True, text=True)
        mutant_result = json.load(open(mutant_report))
        assert "leakage.answer_source_absent" in mutant_result["failed_checks"], (
            f"the gate must refuse a shipped label source; it said: "
            f"{mutant_result['failed_checks']}")

        # ---- 7. determinism ---------------------------------------------------
        extract2 = os.path.join(work, "extract2")
        run([sys.executable, BUILD, "--out", extract2, "--work-dir",
             os.path.join(work, "scratch2"), "--pages-dir", pages,
             "--built-at", BUILT_AT, "--summary-out",
             os.path.join(work, "summary2.json")])
        for relative in ("public/train.csv", "public/eval.csv",
                         "private/holdout.csv", "meta.json", "quality.json"):
            assert digest(os.path.join(extract, relative)) == \
                digest(os.path.join(extract2, relative)), relative

        print("test_za_cct_build: ALL OK")
        print(f"  synthetic splits: {splits}")
        print(f"  probe coverage/mismatches: covered={covered} mismatches={mismatches}")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
