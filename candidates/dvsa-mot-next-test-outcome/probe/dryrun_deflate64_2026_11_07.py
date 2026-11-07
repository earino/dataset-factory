#!/usr/bin/env python3
"""Red/green dry run for the dvsa-mot-build-003 Deflate64 repair (coordinator).

Proves, on synthetic fixtures and REAL Deflate64 bytes (never shipped, never
quoted as findings):

  RED-A      - the build-001 source (git be68bfd, pre-ABRVE-repair) still
               fails loudly on the measured 2015 'ABRVE' source value - the
               build-002 value repair is still in place and this dry run
               still bites;
  RED-D      - the build-002 source (git 5dc4b61, pre-Deflate64-repair)
               still raises stdlib zipfile's NotImplementedError on
               compress_type 9 members - the defect that killed
               dvsa-mot-build-002 at the 2017 DfT zip;
  GREEN-D    - the patched open_text_lines decodes REAL Deflate64 members
               through the local-header + inflate64 route on (a) a
               known-plaintext zip built here with inflate64's own Deflater
               in the measured 2017 member shape (pipe-delimited header,
               \r\n line ends, two members) and (b) the inflate64 project's
               own tests/data/test-file.zip (a container written by another
               producer): every member's blob read matches the central
               directory's compress_size and its one-shot inflate matches the
               central directory's file_size exactly;
  GREEN-S    - the patched build in test mode on the stdlib fixtures
               (coordinator shape: no inflate64 import needed for the
               stdlib members) still constructs, inventories ABRVE/ABR as
               non-completed, and the ABRVE checks all hold;
  GREEN-FULL - the patched build in test mode over a source tree whose
               2017-2023 fixtures are re-encoded as real Deflate64 zips
               with byte-identical member content reproduces the
               stdlib-route extract byte-for-byte (public/*.csv,
               private/holdout.csv, meta.json, quality.json) with equal
               per-year population counters and pair counters;
  GATE       - qualify_dataset.py (gate 1.5.0) passes on both synthetic
               extracts and exact-byte --accept accepts them, in the run.sh
               stage order, with the post-acceptance triad machinery after
               acceptance only.

The Deflate64 legs need python3.13 + inflate64==1.0.4 (the pinned worker
dependency). The script bootstraps a scratch venv itself and re-execs into
it, so plain `python3 probe/dryrun_deflate64_2026_11_07.py` works from any
stdlib python with /usr/bin/python3 present. If the bootstrap is impossible
the Deflate64 legs FAIL loudly - they are never silently skipped, because a
silent skip would relaunch build-003 with the route untested on this host.

The optional leg on the inflate64 project's own test-file.zip (downloaded
from its PyPI sdist at dry-run time, ~180 KB, never committed) tests the
local-header math against a container this script did not build; on network
failure it is reported as skipped and the verdict does not depend on it.

Usage: python3 probe/dryrun_deflate64_2026_11_07.py   (absolute paths
       internally; any cwd works)
"""
import gzip
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import types
import urllib.request
import zipfile
import zlib
from pathlib import Path

CAND = Path(__file__).resolve().parent
REPO = CAND.parents[2]
SCRATCH = Path("/opt/data/cache/scratch/dvsa-dryrun-deflate64")
SOURCES = SCRATCH / "sources"
TYPE9_SOURCES = SCRATCH / "sources-type9"
VENV = Path("/opt/data/cache/scratch/dvsa-venv313")
VENV_PY = VENV / "bin" / "python3"
GATE = REPO / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"
BUILD = CAND.parent / "source" / "build.py"
SCORE = CAND.parent / "source" / "score.py"
COMMIT_BUILD001 = "be68bfd"   # pre-ABRVE-repair: fails loudly on 'ABRVE'
COMMIT_BUILD002 = "5dc4b61"  # ABRVE-repaired, pre-Deflate64: type-9 refuses
COMMIT_BUILD003 = "2efdf50"  # Deflate64-repaired, pre-MACOSX: junk members hit RowParser
INFLATE64_PIN = "1.0.4"

# The measured anomaly, verbatim from record measurements.build_failure_2015_
# abrve_2026_11_05 (container.log row), 14-column pipe era (no completed_date):
ABRVE_ROW = ("1574076421|192184530|2015-07-03|4|NT|ABRVE||SK|VOLKSWAGEN|"
             "GOLF PLUS|RED|DI|1896|2006-07-07")

VERDICT = {}


def sh(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def load_build(path: Path) -> types.ModuleType:
    """Load a build.py as a module without writing __pycache__ (skill rule)."""
    module = types.ModuleType("build_under_test")
    module.__file__ = str(path)
    exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
    return module


def git_build(commit: str) -> Path:
    target = SCRATCH / f"build_{commit}.py"
    result = sh(["git", "-C", str(REPO), "show",
                 f"{commit}:candidates/dvsa-mot-next-test-outcome/source/build.py"])
    if result.returncode != 0:
        raise RuntimeError(f"git show {commit} failed: {result.stderr[-200:]}")
    target.write_text(result.stdout)
    return target


def ensure_inflate64() -> bool:
    """Re-exec into a python3.13 venv with the pinned inflate64, if needed."""
    try:
        import inflate64  # noqa: F401
        return True
    except ImportError:
        pass
    base = Path("/usr/bin/python3")
    if not base.exists():
        print("no /usr/bin/python3 for the Deflate64 venv bootstrap")
        return False
    if not VENV_PY.is_file():
        created = sh([str(base), "-m", "venv", str(VENV)])
        if created.returncode != 0:
            print("venv bootstrap failed:", created.stderr[-300:])
            return False
    installed = sh([str(VENV_PY), "-m", "pip", "install", "--no-cache-dir",
                    f"inflate64=={INFLATE64_PIN}"])
    if installed.returncode != 0:
        print("pip install inflate64 failed:", installed.stderr[-300:])
        return False
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve())])
    return False


def write_deflate64_zip(path: Path, members: list) -> None:
    """Write a zip container whose members claim compress_type 9 with REAL
    Deflate64 payloads produced by inflate64's own Deflater. The local
    header, central directory and EOCD are written explicitly because stdlib
    zipfile cannot write method 9. CRC32 is the CRC of the UNcompressed
    member, per the zip spec.
    """
    import inflate64
    prepared = []
    for name, text in members:
        compressor = inflate64.Deflater()
        blob = compressor.deflate(text) + compressor.flush()
        name_bytes = name.encode("utf-8")
        prepared.append((name_bytes, blob, zlib.crc32(text) & 0xFFFFFFFF,
                         len(text)))
    with open(path, "wb") as handle:
        central = b""
        for name_bytes, blob, crc, usize in prepared:
            offset = handle.tell()
            # local file header (30 bytes) + name + payload
            handle.write(struct.pack(
                "<4sHHHHHIIIHH", b"PK\x03\x04", 20, 0, 9, 0, 0,
                crc, len(blob), usize, len(name_bytes), 0))
            handle.write(name_bytes)
            handle.write(blob)
            # central directory entry (46 bytes) + name
            central += struct.pack(
                "<4sHHHHHHIIIHHHHHII", b"PK\x01\x02", 20, 20, 0, 9, 0, 0,
                crc, len(blob), usize, len(name_bytes), 0, 0, 0, 0, 0,
                offset)
            central += name_bytes
        cd_offset = handle.tell()
        handle.write(central)
        handle.write(struct.pack(
            "<4sHHHHIIH", b"PK\x05\x06", 0, 0, len(prepared), len(prepared),
            len(central), cd_offset, 0))


def expected_lines(text: bytes) -> list:
    """Lines exactly as open_text_lines must yield them for this member text
    (TextIOWrapper with newline=None translates \r\n and lone \r to \n, then
    splits keeping line ends)."""
    normalized = text.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return normalized.decode("utf-8", "replace").splitlines(keepends=True)


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    if not ensure_inflate64():
        print("FATAL: no runtime with inflate64; the Deflate64 legs cannot run")
        return 1

    # 1. Regenerate the committed fixture set into this scratch dir.
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
    print("fixtures generated:", json.loads(
        (SCRATCH / "fixtures_summary.json").read_text())["tests"], "tests")

    # 2. Inject the measured ABRVE rows into the 2015 headered pipe file
    #    (verbatim measured row + one for a real bucket vehicle).
    ids = []
    candidate = 1
    while len(ids) < 1:
        if int(hashlib.md5(str(candidate).encode()).hexdigest(), 16) % 1000 == 0:
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
    print("ABRVE rows injected into source_2015.txt.gz (measured + bucket row)")

    # 3. RED-A: the build-001 source must still fail on the ABRVE value.
    old_build = git_build(COMMIT_BUILD001)
    red_a = sh([sys.executable, "-u", str(old_build), "--out",
                str(SCRATCH / "extract-red-a"), "--work-dir",
                str(SCRATCH / "w-red-a"), "--source-dir", str(SOURCES)])
    (SCRATCH / "red-a.log").write_text(red_a.stdout + "\n--stderr--\n" + red_a.stderr)
    red_a_ok = red_a.returncode != 0 and "unexpected test_result 'ABRVE'" in red_a.stderr
    VERDICT["red_a_abrve_fails_as_designed"] = red_a_ok
    print("RED-A (build-001 on ABRVE): exit", red_a.returncode,
          "-> FAILED AS DESIGNED" if red_a_ok else "UNEXPECTED", flush=True)

    # 4. GREEN-S: the patched build on the stdlib fixtures.
    green_s = sh([sys.executable, "-u", str(BUILD), "--out",
                  str(SCRATCH / "extract-stdlib"), "--work-dir",
                  str(SCRATCH / "w-stdlib"), "--source-dir", str(SOURCES)])
    (SCRATCH / "green-stdlib.log").write_text(green_s.stdout + "\n--stderr--\n"
                                              + green_s.stderr)
    print("GREEN-S (patched build, stdlib fixtures): exit", green_s.returncode,
          flush=True)
    if green_s.returncode != 0:
        print(green_s.stdout[-3000:], green_s.stderr[-3000:])
        return 1
    summary_s = json.loads((SCRATCH / "extract-stdlib" / "summary.json").read_text())
    y2015 = summary_s["population"]["per_year"]["2015"]
    checks = {
        "2015 non_completed_rows >= 2": y2015.get("non_completed_rows", 0) >= 2,
        "2015 inventory carries ABRVE": "ABRVE" in y2015.get("non_completed_values", []),
        "2015 inventory carries ABR": "ABR" in y2015.get("non_completed_values", []),
        "2015 histogram counts ABRVE": y2015.get("result_histogram", {}).get("ABRVE", 0) >= 1,
        "abandoned (pair-excluded) rows >= 2": summary_s["pairs"].get("abandoned_rows", 0) >= 2,
    }
    VERDICT["green_s_checks"] = checks
    print("GREEN-S checks:", json.dumps(checks, indent=1))

    # 5. Known-plaintext Deflate64 mini zip in the real 2017 member shape
    #    (pipe-delimited 14-col header, \r\n ends, two members).
    HEADER14 = ("test_id|vehicle_id|test_date|test_class_id|test_type|test_result|"
                "test_mileage|postcode_area|make|model|colour|fuel_type|"
                "cylinder_capacity|first_use_date")
    row = "1574076421|192184530|2017-07-03|4|NT|ABRVE||SK|VOLKSWAGEN|GOLF PLUS|RED|DI|1896|2006-07-07"
    member1 = (HEADER14 + "\r\n" + row + "\r\n"
               + row.replace("ABRVE", "P") + "\r\n").encode()
    member2 = (HEADER14 + "\r\n" + row.replace("ABRVE", "F") + "\r\n").encode()
    mini_zip = SCRATCH / "mini_deflate64.zip"
    write_deflate64_zip(mini_zip, [("test_result_31870.csv", member1),
                                   ("test_result_31871.csv", member2)])
    with zipfile.ZipFile(mini_zip) as archive:
        types_ok = all(info.compress_type == 9 for info in archive.infolist())
    VERDICT["mini_zip_members_are_type9"] = types_ok
    print("mini Deflate64 zip written; stdlib reads central dir, all type 9:",
          types_ok)

    # 6. RED-D: the build-002 source must raise NotImplementedError on the
    #    type-9 member (the exact failure class that killed build-002).
    build002 = load_build(git_build(COMMIT_BUILD002))
    try:
        for _name, _line in build002.open_text_lines(mini_zip, 2017):
            pass
        red_d_ok = False
        red_d_error = "no exception"
    except NotImplementedError as error:
        red_d_ok = True
        red_d_error = str(error)[:160]
    VERDICT["red_d_build002_refuses_type9"] = red_d_ok
    print("RED-D (build-002 open_text_lines on type 9):",
          "NotImplementedError AS DESIGNED" if red_d_ok
          else f"UNEXPECTED ({red_d_error})")

    # 7. GREEN-D: the patched open_text_lines decodes the mini zip exactly.
    patched = load_build(BUILD)
    got = [(name, line) for name, line in patched.open_text_lines(mini_zip, 2017)]
    want = ([("test_result_31870.csv", line) for line in expected_lines(member1)]
            + [("test_result_31871.csv", line) for line in expected_lines(member2)])
    green_d_ok = got == want
    VERDICT["green_d_known_plaintext_roundtrip"] = green_d_ok
    print("GREEN-D (patched route vs known plaintext):",
          "EXACT" if green_d_ok else "MISMATCH")
    if not green_d_ok:
        print(" first got:", got[:3], "\n first want:", want[:3])

    # 8. GREEN-D-extra (optional, other producer's container): the inflate64
    #    project's own test-file.zip from its PyPI sdist. Per member: the
    #    blob read at MY computed local-header offset must be exactly the
    #    central directory's compress_size, and its one-shot inflate exactly
    #    the central directory's file_size.
    sdist_leg = "skipped"
    sdist = SCRATCH / "inflate64-1.0.4.tar.gz"
    if not sdist.is_file():
        try:
            info = json.load(urllib.request.urlopen(
                "https://pypi.org/pypi/inflate64/1.0.4/json", timeout=30))
            url = next(f["url"] for f in info["urls"]
                       if f["packagetype"] == "sdist")
            urllib.request.urlretrieve(url, sdist)
            sdist_leg = "downloaded"
        except Exception as error:  # bounded optional leg, reported not fatal
            sdist_leg = f"download-failed ({str(error)[:100]})"
    if sdist.is_file():
        with tarfile.open(sdist) as tar:
            member = tar.getmember("inflate64-1.0.4/tests/data/test-file.zip")
            sample = SCRATCH / "inflate64_test-file.zip"
            sample.write_bytes(tar.extractfile(member).read())
        ok = True
        with zipfile.ZipFile(sample) as archive:
            for info in archive.infolist():
                blob = patched._member_blob(sample, info)
                import inflate64
                text = inflate64.Inflater().inflate(blob)
                ok = ok and len(blob) == info.compress_size
                ok = ok and len(text) == info.file_size
        sdist_leg = "ok" if ok else "MISMATCH"
    VERDICT["green_d_other_container"] = sdist_leg
    print("GREEN-D-extra (inflate64 project test-file.zip):", sdist_leg)

    # 9. GREEN-FULL: re-encode fixture years 2017-2023 as real Deflate64
    #    zips with byte-identical member content, then run the patched build.
    if TYPE9_SOURCES.exists():
        shutil.rmtree(TYPE9_SOURCES)
    shutil.copytree(SOURCES, TYPE9_SOURCES)
    for year in range(2017, 2024):
        original = SOURCES / f"source_{year}.zip"
        with zipfile.ZipFile(original) as archive:
            info = archive.infolist()[0]
            content = archive.read(info)
        target = TYPE9_SOURCES / f"source_{year}.zip"
        write_deflate64_zip(target, [(info.filename, content)])
        with zipfile.ZipFile(target) as archive:
            assert archive.infolist()[0].compress_type == 9, target
    print("fixture years 2017-2023 re-encoded as real Deflate64 zips")

    green_f = sh([sys.executable, "-u", str(BUILD), "--out",
                  str(SCRATCH / "extract-type9"), "--work-dir",
                  str(SCRATCH / "w-type9"), "--source-dir", str(TYPE9_SOURCES)])
    (SCRATCH / "green-type9.log").write_text(green_f.stdout + "\n--stderr--\n"
                                             + green_f.stderr)
    print("GREEN-FULL (patched build, type-9 fixtures): exit", green_f.returncode,
          flush=True)
    if green_f.returncode != 0:
        print(green_f.stdout[-3000:], green_f.stderr[-3000:])
        return 1

    identical = {}
    for relative in ("public/train.csv", "public/eval.csv",
                     "private/holdout.csv", "meta.json", "quality.json"):
        left = (SCRATCH / "extract-stdlib" / relative).read_bytes()
        right = (SCRATCH / "extract-type9" / relative).read_bytes()
        identical[relative] = left == right
    summary_f = json.loads((SCRATCH / "extract-type9" / "summary.json").read_text())
    counters_equal = True
    for year in map(str, range(2005, 2025)):
        left = summary_s["population"]["per_year"][year]
        right = summary_f["population"]["per_year"][year]
        for key in ("rows_seen", "class4_rows", "sampled_rows",
                    "non_completed_rows", "result_histogram", "members"):
            counters_equal = counters_equal and left.get(key) == right.get(key)
    counters_equal = counters_equal and summary_s["pairs"] == summary_f["pairs"]
    VERDICT["green_full_files_identical"] = identical
    VERDICT["green_full_counters_equal"] = counters_equal
    print("GREEN-FULL files identical:", json.dumps(identical))
    print("GREEN-FULL per-year counters + pairs equal:", counters_equal)

    # 9b. RED-M / GREEN-M: the 2018 macOS junk-member defect (measured on
    #     the real 2018 DfT zip by dvsa-mot-build-003: its FIRST member is
    #     __MACOSX/._dft_test_result-from-2018-...-csv, AppleDouble bytes).
    #     RED-M - the build-003 source fails on a fixture zip carrying a
    #     __MACOSX member exactly like the real one; GREEN-M - the patched
    #     build skips the junk and reproduces the stdlib extract
    #     byte-for-byte from a source tree whose 2018 zip carries the junk.
    JUNK_SOURCES = SCRATCH / "sources-junk"
    if JUNK_SOURCES.exists():
        shutil.rmtree(JUNK_SOURCES)
    shutil.copytree(TYPE9_SOURCES, JUNK_SOURCES)
    junk_payload = (b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X"
                    b"\x00\x02\x00\x00\x00\t\x00\x00\x002\x00\x00\x07")
    # the real member's content comes from the ORIGINAL stdlib fixture
    # (stdlib cannot read the type-9 re-encoded copy - that is the defect)
    with zipfile.ZipFile(SOURCES / "source_2018.zip") as archive:
        info = archive.infolist()[0]
        content = archive.read(info)
    write_deflate64_zip(JUNK_SOURCES / "source_2018.zip",
                        [(f"__MACOSX/._{info.filename}", junk_payload),
                         (info.filename, content)])
    with zipfile.ZipFile(JUNK_SOURCES / "source_2018.zip") as archive:
        names = [i.filename for i in archive.infolist()]
    assert len(names) == 2 and names[0].startswith("__MACOSX/"), names
    build003 = git_build(COMMIT_BUILD003)
    red_m = sh([sys.executable, "-u", str(build003), "--out",
                str(SCRATCH / "extract-red-m"), "--work-dir",
                str(SCRATCH / "w-red-m"), "--source-dir", str(JUNK_SOURCES)])
    (SCRATCH / "red-m.log").write_text(red_m.stdout + "\n--stderr--\n" + red_m.stderr)
    red_m_ok = red_m.returncode != 0 and "cannot map columns" in red_m.stderr
    VERDICT["red_m_build003_fails_on_macosx_junk"] = red_m_ok
    print("RED-M (build-003 on __MACOSX member): exit", red_m.returncode,
          "-> FAILED AS DESIGNED" if red_m_ok else "UNEXPECTED", flush=True)

    green_m = sh([sys.executable, "-u", str(BUILD), "--out",
                  str(SCRATCH / "extract-junk"), "--work-dir",
                  str(SCRATCH / "w-junk"), "--source-dir", str(JUNK_SOURCES)])
    (SCRATCH / "green-junk.log").write_text(green_m.stdout + "\n--stderr--\n"
                                            + green_m.stderr)
    print("GREEN-M (patched build, junk-carrying tree): exit", green_m.returncode,
          flush=True)
    junk_identical = {}
    if green_m.returncode == 0:
        for relative in ("public/train.csv", "public/eval.csv",
                         "private/holdout.csv", "meta.json", "quality.json"):
            left = (SCRATCH / "extract-stdlib" / relative).read_bytes()
            right = (SCRATCH / "extract-junk" / relative).read_bytes()
            junk_identical[relative] = left == right
    VERDICT["green_m_files_identical"] = junk_identical
    print("GREEN-M files identical vs stdlib extract:",
          json.dumps(junk_identical))

    # 10. GATE + exact-byte accept + triad on both extracts (run.sh order).
    overall = {}
    for label, extract in (("stdlib", SCRATCH / "extract-stdlib"),
                           ("type9", SCRATCH / "extract-type9")):
        qual = sh([sys.executable, str(GATE), str(extract), "--json",
                   "--report", str(SCRATCH / f"qualification-{label}.json")])
        (SCRATCH / f"qualification-{label}.txt").write_text(qual.stdout + "\n"
                                                            + qual.stderr)
        accept = None
        score = None
        if qual.returncode == 0:
            accept = sh([sys.executable, str(GATE), "--accept",
                         str(SCRATCH / f"qualification-{label}.json"), str(extract)])
            (SCRATCH / f"acceptance-{label}.txt").write_text(accept.stdout + "\n"
                                                             + accept.stderr)
        if accept is not None and accept.returncode == 0:
            score = sh([sys.executable, str(SCORE), "--data", str(extract),
                        "--accepted-report",
                        str(SCRATCH / f"qualification-{label}.json"),
                        "--report", str(SCRATCH / f"references-{label}.json")])
            (SCRATCH / f"score-{label}.log").write_text(score.stdout + "\n"
                                                        + score.stderr)
        overall[label] = {"gate": qual.returncode,
                          "accept": accept.returncode if accept else None,
                          "triad": score.returncode if score else None}
        print(f"GATE/{label}: exit", qual.returncode,
              "accept", accept.returncode if accept else None,
              "triad", score.returncode if score else None, flush=True)
    VERDICT["gate_accept_triad"] = overall

    VERDICT["note"] = ("synthetic fixtures and self-built Deflate64 bytes "
                       "only; numbers are not findings")
    (SCRATCH / "verdict.json").write_text(json.dumps(VERDICT, indent=1) + "\n")
    mandatory = [red_a_ok, all(checks.values()), red_d_ok, green_d_ok,
                 all(identical.values()), counters_equal, red_m_ok,
                 green_m.returncode == 0 and all(junk_identical.values())]
    for label in ("stdlib", "type9"):
        leg = overall[label]
        mandatory.append(leg["gate"] == 0 and leg["accept"] == 0
                         and leg["triad"] == 0)
    ok = all(mandatory)
    print(json.dumps(VERDICT, indent=1))
    print("DRY RUN", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
