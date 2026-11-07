#!/usr/bin/env python3
"""Red/green dry run for the dvsa-mot-build-002 value-rule repair (coordinator).

Proves, on synthetic fixtures only (never shipped, never quoted as findings):

  RED   - the build as launched for dvsa-mot-build-001 (git HEAD, pre-repair)
          still fails loudly on the measured 2015 'ABRVE' source value;
  GREEN - the repaired build (source/build.py, dvsa-mot-build-002) treats any
          test_result outside {P, F, PRS} as a non-completed test: counted per
          year, inventoried in summary.json, excluded from both sides of every
          pair, with the parse-time counters the deterministic 2005-2014
          cross-check reads unchanged;
  GATE  - qualify_dataset.py (gate 1.5.0) passes on the synthetic extract and
          exact-byte --accept accepts it, so the stage order in run.sh is
          unchanged by the repair.

Usage: python3 probe/dryrun_abrve_2026_11_07.py   (from the candidate root;
       expects git HEAD to carry the pre-repair source/build.py)
"""
import gzip
import json
import subprocess
import sys
from pathlib import Path

CAND = Path(__file__).resolve().parent
REPO = CAND.parents[2]
SCRATCH = Path("/opt/data/cache/scratch/dvsa-dryrun-abrve")
SOURCES = SCRATCH / "sources"

# The measured anomaly, verbatim from record measurements.build_failure_2015_
# abrve_2026_11_05 (container.log row), 14-column pipe era (no completed_date):
ABRVE_ROW = ("1574076421|192184530|2015-07-03|4|NT|ABRVE||SK|VOLKSWAGEN|"
             "GOLF PLUS|RED|DI|1896|2006-07-07")


def sh(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)

    # 1. Regenerate the committed 2026-11-05 fixture set into our scratch dir.
    generator = CAND / "dryrun_fixtures_2026_11_05.py"
    text = generator.read_text()
    text = text.replace('Path("/opt/data/cache/scratch/dvsa-dryrun")',
                        f'Path("{SCRATCH}")')
    patched_gen = SCRATCH / "fixtures_gen.py"
    patched_gen.write_text(text)
    result = sh([sys.executable, str(patched_gen)])
    if result.returncode != 0:
        print(result.stdout, result.stderr)
        return 1
    print("fixtures generated:", json.loads((SCRATCH / "fixtures_summary.json")
                                            .read_text())["tests"], "tests")

    # 2. Inject ABRVE rows into the 2015 headered pipe file: the measured
    #    historical row verbatim, plus one for a real bucket vehicle so the
    #    sampled path also exercises the exclusion (pair sequence must skip it).
    ids = []
    candidate = 1
    while len(ids) < 1:
        if int(__import__("hashlib").md5(str(candidate).encode()).hexdigest(),
               16) % 1000 == 0:
            ids.append(str(candidate))
        candidate += 1
    bucket_abrve = (f"990001|{ids[0]}|2015-12-15|4|NT|ABRVE||HG|FORD|FIESTA|"
                    f"BLUE|PE|1400|2003-03-03")
    bucket_abr = (f"990002|{ids[0]}|2015-06-20|4|NT|ABR||HG|FORD|FIESTA|"
                  f"BLUE|PE|1400|2003-03-03")
    path = SOURCES / "source_2015.txt.gz"
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    header, data = lines[0], lines[1:]
    data.extend([ABRVE_ROW, bucket_abrve, bucket_abr])
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(header + "\n")
        for line in sorted(data):
            handle.write(line + "\n")
    print("ABRVE rows injected into source_2015.txt.gz (measured row + bucket row)")

    # 3. RED: the pre-repair build (git HEAD) must fail on the ABRVE value.
    old_build = SCRATCH / "build_prerepair.py"
    old = sh(["git", "-C", str(REPO), "show",
              "HEAD:candidates/dvsa-mot-next-test-outcome/source/build.py"])
    if old.returncode != 0:
        print("git show failed", old.stderr)
        return 1
    old_build.write_text(old.stdout)
    red = sh([sys.executable, "-u", str(old_build), "--out",
              str(SCRATCH / "extract-red"), "--work-dir", str(SCRATCH / "w-red"),
              "--source-dir", str(SOURCES)])
    (SCRATCH / "red.log").write_text(red.stdout + "\n--stderr--\n" + red.stderr)
    red_failed = red.returncode != 0 and "unexpected test_result 'ABRVE'" in red.stderr
    print("RED (pre-repair build on ABRVE): exit", red.returncode,
          "-> FAILED AS DESIGNED" if red_failed else "UNEXPECTED",
          flush=True)

    # 4. GREEN: the repaired build must construct and inventory the values.
    new_build = CAND.parent / "source" / "build.py"
    green = sh([sys.executable, "-u", str(new_build), "--out",
                str(SCRATCH / "extract"), "--work-dir", str(SCRATCH / "w"),
                "--source-dir", str(SOURCES)])
    (SCRATCH / "green.log").write_text(green.stdout + "\n--stderr--\n"
                                      + green.stderr)
    print("GREEN (repaired build): exit", green.returncode, flush=True)
    if green.returncode != 0:
        print(green.stdout[-3000:], green.stderr[-3000:])
        return 1
    summary = json.loads((SCRATCH / "extract" / "summary.json").read_text())
    per_year = summary["population"]["per_year"]
    y2015 = per_year["2015"]
    checks = {
        "2015 non_completed_rows >= 2": y2015.get("non_completed_rows", 0) >= 2,
        "2015 inventory carries ABRVE": "ABRVE" in y2015.get("non_completed_values", []),
        "2015 inventory carries ABR": "ABR" in y2015.get("non_completed_values", []),
        "2015 histogram counts ABRVE": y2015.get("result_histogram", {}
                                                  ).get("ABRVE", 0) >= 1,
        "abandoned (pair-excluded) rows >= 2": summary["pairs"].get(
            "abandoned_rows", 0) >= 2,
    }
    print("GREEN checks:", json.dumps(checks, indent=1))

    # 5. GATE + exact-byte accept on the synthetic extract (order as run.sh).
    gate = REPO / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"
    qual = sh([sys.executable, str(gate), str(SCRATCH / "extract"), "--json",
               "--report", str(SCRATCH / "qualification.json")])
    (SCRATCH / "qualification.txt").write_text(qual.stdout + "\n"
                                              + qual.stderr)
    print("GATE exit", qual.returncode)
    accept = None
    if qual.returncode == 0:
        accept = sh([sys.executable, str(gate), "--accept",
                     str(SCRATCH / "qualification.json"),
                     str(SCRATCH / "extract")])
        (SCRATCH / "acceptance.txt").write_text(accept.stdout + "\n"
                                                + accept.stderr)
        print("ACCEPT exit", accept.returncode)

    # 6. Post-acceptance triad machinery (score.py, eval only).
    score = None
    if accept is not None and accept.returncode == 0:
        score = sh([sys.executable, str(CAND.parent / "source" / "score.py"),
                    "--data", str(SCRATCH / "extract"),
                    "--accepted-report", str(SCRATCH / "qualification.json"),
                    "--report", str(SCRATCH / "references.json")])
        (SCRATCH / "score.log").write_text(score.stdout + "\n"
                                          + score.stderr)
        print("TRIAD exit", score.returncode)

    verdict = {
        "red_failed_as_designed": red_failed,
        "green_exit": green.returncode,
        "green_checks": checks,
        "gate_exit": qual.returncode,
        "accept_exit": accept.returncode if accept else None,
        "triad_exit": score.returncode if score else None,
        "note": "synthetic fixtures only; numbers are not findings",
    }
    (SCRATCH / "verdict.json").write_text(json.dumps(verdict, indent=1) + "\n")
    print(json.dumps(verdict, indent=1))
    ok = (red_failed and green.returncode == 0 and all(checks.values())
          and qual.returncode == 0 and accept is not None
          and accept.returncode == 0 and score is not None
          and score.returncode == 0)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
