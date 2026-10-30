# Probe: ipo-tm pipe-row reconciliation (2026-10-30, advancement pass).
#
# Decides WITH MEASUREMENTS which pipeline is correct for the 94 embedded-pipe
# rows of the pinned IPO snapshot:
#   pass A = probe_aggregate.py verbatim (left-anchored reads at fields[7]/[12]/
#            [14], int-key dedup AFTER the filed check, header counted as a
#            row) - the source of the frozen EXPECTED table;
#   pass C = source/build.py's pipeline (right-anchored recovery, string-key
#            dedup BEFORE the filed check, header skipped) - what ipo-tm-002
#            ran on the worker (its measured numbers are pinned below).
# Also records pass B1 (build's dedup order + shifted reads) and B2 (old
# order, string key) for provenance of EXPECTED's "52 blank/bad-filed".
#
# Bounded reconciliation: aggregate counts only. No feature panel is aligned,
# no labelled example rows are emitted, no model, no AUC - the only row-level
# records are the 94 pipe rows and the rows whose classification changed.
# The zip is fetched once to scratch, sha256-verified against the pin.

import hashlib
import json
import struct
import sys
import time
import urllib.request
import zlib
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

URL = ("https://assets.publishing.service.gov.uk/media/"
       "5a82e5f4e5274a2e87dc387d/opendatadomestic.zip")
PINNED_SHA256 = ("3b6063bed36a78e8a04f10a5383f2881f4072a1be13e706a81ab"
                 "097fb56ee571")
PINNED_BYTES = 63_238_846
HERE = Path(__file__).resolve().parent
SCRATCH = Path("/opt/data/cache/scratch/ipo-reconc")
ZIP_PATH = SCRATCH / "opendatadomestic.zip"
OUT = HERE / "ipo_tm_reconciliation.json"

NEG_STATUSES = {"Refused", "Withdrawn"}
POS_LAPSED = {"Registered", "Merged", "Dead", "Removed", "Expired", "Cancelled",
              "Surrendered"}
CENSORED_VOCAB = {"Application Received", "Examination", "Pre-Publication",
                  "Application Published", "Opposed", "Appealed", "Appealable",
                  "Registration Pending", "Deleted", "Deemed Not Filed", ""}
KNOWN_STATUS_VOCAB = POS_LAPSED | NEG_STATUSES | CENSORED_VOCAB
YEARS = ("2010", "2011", "2012", "2013", "2014", "2015", "2016")

# frozen discovery aggregates (pass A output, 2026-10-27)
FROZEN = json.loads((HERE / "ipo_tm_aggregates.json").read_text())

# ipo-tm-002 container.log: what build.py's pipeline measured on the worker
BUILD_MEASURED = {
    "data_rows": 1_189_004, "distinct_marks": 1_172_095,
    "dup_rows": 16_909, "pipe_recovered": 94,
    "blank_or_bad_filed": 34, "unparseable_filed": 0,
    "letter_suffix_rows": 22_812, "letter_suffix_dups": 17,
    "neg_with_regdate_eligible": 8, "neg_with_regdate_post2010": 10,
    # unparseable_filed: the ipo-tm-002 worker build never printed or asserted
    # this count. The 3 in notes.md ("'3'/'5' filed rows") was a shifted-read
    # artifact of the 2026-10-30 probe: those rows are pipe rows
    # UK00003033672 / UK00003112662 / UK00003154878 whose SHIFTED filed read
    # was the series count; their recovered filed dates parse normally.
    "per_year": {
        "2010": {"n": 30_372, "pos": 27_181, "neg": 3_187, "cens": 4},
        "2011": {"n": 36_364, "pos": 31_015, "neg": 5_338, "cens": 11},
        "2012": {"n": 40_275, "pos": 34_472, "neg": 5_797, "cens": 6},
        "2013": {"n": 46_362, "pos": 38_928, "neg": 7_365, "cens": 69},
        "2014": {"n": 51_084, "pos": 42_771, "neg": 8_210, "cens": 103},
        "2015": {"n": 54_300, "pos": 46_169, "neg": 7_953, "cens": 178},
        "2016": {"n": 61_681, "pos": 53_216, "neg": 7_834, "cens": 631},
    },
}
# deltas C minus frozen EXPECTED that the attribution must close exactly
TARGET_DELTAS = {
    "per_year": {"2010": {"n": 0, "pos": 0, "neg": 0, "cens": 0},
                 "2011": {"n": 0, "pos": 0, "neg": 0, "cens": 0},
                 "2012": {"n": 0, "pos": 0, "neg": 0, "cens": 0},
                 "2013": {"n": 7, "pos": 5, "neg": 2, "cens": 0},
                 "2014": {"n": 9, "pos": 5, "neg": 4, "cens": 0},
                 "2015": {"n": 9, "pos": 9, "neg": 0, "cens": 0},
                 "2016": {"n": 33, "pos": 31, "neg": 2, "cens": 0}},
    "blank_data_rows": 34 - 52,
}

sys.path.insert(0, str(HERE / "source"))
import build as ipo_build  # noqa: E402  (module import is side-effect free)

EXPECTED_PER_YEAR = ipo_build.EXPECTED["per_year"]


def fetch() -> None:
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size == PINNED_BYTES:
        if hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest() == PINNED_SHA256:
            print("zip already in scratch, sha256 pinned OK")
            return
    SCRATCH.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    req = urllib.request.Request(URL, headers={"User-Agent": "scout-probe"})
    total = 0
    with urllib.request.urlopen(req, timeout=300) as resp, \
            ZIP_PATH.open("wb") as handle:
        while True:
            block = resp.read(1 << 20)
            if not block:
                break
            handle.write(block)
            digest.update(block)
            total += len(block)
    sha = digest.hexdigest()
    if total != PINNED_BYTES or sha != PINNED_SHA256:
        raise SystemExit(f"fetch mismatch: {total} B, sha256 {sha}")
    print(f"fetched {total} bytes, sha256 pinned OK")


def raw_lines():
    """Stream (is_header, fields) for every non-blank line, raw left split."""
    with ZIP_PATH.open("rb") as handle:
        pre = handle.read(30)
        if pre[:4] != b"PK\x03\x04":
            raise SystemExit("not a zip local-file record")
        nlen, elen = struct.unpack("<HH", pre[26:30])
        handle.read(nlen + elen)
        dec = zlib.decompressobj(-15)
        bytebuf, tail = b"", ""
        header_done = False
        while True:
            raw = handle.read(1 << 18)
            text = dec.decompress(raw, 0) if raw else dec.flush()
            if text:
                bytebuf += text
                usable = len(bytebuf) - (len(bytebuf) % 2)
                tail += bytebuf[:usable].decode("utf-16-le", "replace")
                bytebuf = bytebuf[usable:]
                lines = tail.split("\r")
                tail = lines[-1]
                for line in lines[:-1]:
                    line = line.strip("\n")
                    if not line.strip():
                        continue
                    is_header = not header_done
                    header_done = True
                    yield is_header, line.lstrip("\ufeff").split("|")
            if not raw:
                break


def recover(fields):
    """Verbatim copy of build.py iter_records' right-anchored recovery
    (source/build.py lines 252-267). Returns recovered fields or None."""
    if len(fields) < 17:
        return None
    if len(fields) != 62:
        extra = len(fields) - 62
        classes = fields[-45:]
        head = fields[:-45]
        if len(head) != 17 + extra:
            return None
        mark_text = "|".join(head[2:3 + extra])
        fields = [head[0], head[1], mark_text] + head[3 + extra:] + classes
    return fields


def parse_date(value):
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def new_year():
    return {"n": 0, "pos": 0, "neg": 0, "cens": 0,
            "status": Counter(), "shift": 0}


def bucket_of(regd, status):
    if regd:
        return "pos"
    if status in NEG_STATUSES:
        return "neg"
    return "cens"


def main() -> int:
    t0 = time.time()
    fetch()

    # pass A: probe_aggregate.py verbatim (header row included)
    a = {"rows": 0, "field_counts": Counter(), "bad_short": 0,
         "shift_rows": 0, "blank": 0, "dup": 0, "nwr": 0, "sortedness": 0,
         "seen": set(), "years_all": Counter(),
         "per_year": defaultdict(new_year)}
    # pass C: build.py's pipeline
    c = {"rows": 0, "field_counts": Counter(), "short": 0, "blank": 0,
         "unparseable": 0, "dup": 0, "letter_rows": 0, "letter_dups": 0,
         "seen": set(), "outwin": Counter(), "years_all": Counter(),
         "per_year": defaultdict(new_year), "nwr_elig": 0, "nwr_post2010": 0,
         "censored_status": Counter()}
    # B1: C's dedup decisions + shifted reads; B2: filed check first, string key
    b1 = {"blank": 0, "dup": 0, "per_year": defaultdict(new_year)}
    b2 = {"blank": 0, "dup": 0, "seen": set(), "per_year": defaultdict(new_year)}

    pipe_census = []
    diffs = []
    last_mark_int = -1

    for is_header, fields in raw_lines():
        raw_len = len(fields)

        # ---------------- pass A (verbatim order from probe_aggregate) ----
        cls_a = ("short",)
        a["rows"] += 1
        a["field_counts"][raw_len] += 1
        if raw_len < 15:
            a["bad_short"] += 1
        else:
            tm_a, status_a = fields[0].strip(), fields[7].strip()
            filed_a, regd_a = fields[12].strip(), fields[14].strip()
            if raw_len != 62:
                a["shift_rows"] += 1
            try:
                tm_int = int(tm_a.replace("UK", "").replace(" ", "")
                             .lstrip("0") or "0")
            except ValueError:
                tm_int = -1
            if tm_int >= 0:
                if tm_int <= last_mark_int - 5 and last_mark_int >= 0:
                    a["sortedness"] += 1
                last_mark_int = tm_int
            if not filed_a or not filed_a[:4].isdigit():
                a["blank"] += 1
                cls_a = ("blank",)
            else:
                key = filed_a[:4]
                a["years_all"][key] += 1
                if tm_int >= 0 and tm_int in a["seen"]:
                    a["dup"] += 1
                    cls_a = ("dup",)
                else:
                    if tm_int >= 0:
                        a["seen"].add(tm_int)
                    if key >= "2010":
                        d = a["per_year"][key]
                        d["n"] += 1
                        d["status"][status_a] += 1
                        if regd_a:
                            d["pos"] += 1
                            if status_a not in POS_LAPSED:
                                d["shift"] += 1
                        elif status_a in NEG_STATUSES:
                            d["neg"] += 1
                        else:
                            d["cens"] += 1
                        if regd_a and status_a in NEG_STATUSES:
                            a["nwr"] += 1
                        if key <= "2016":
                            cls_a = ("inwin", key,
                                     bucket_of(regd_a, status_a))
                        else:
                            cls_a = ("outwin", key)
                    else:
                        cls_a = ("outwin", key)

        if is_header:
            continue

        # ---------------- pass C (build pipeline, header skipped) ----------
        rec = recover(list(fields))
        c["field_counts"][raw_len] += 1
        if rec is None:
            c["short"] += 1
            cls_c = ("short",)
        else:
            c["rows"] += 1
            tm_c = rec[0].strip().replace(" ", "")
            filed_raw = rec[12].strip()
            status_c = rec[7].strip()
            regd_c = rec[14].strip()
            try:
                int(tm_c.replace("UK", "").lstrip("0") or "0")
                letter_row = False
            except ValueError:
                letter_row = True
            if letter_row:
                c["letter_rows"] += 1
            if tm_c in c["seen"]:
                c["dup"] += 1
                if letter_row:
                    c["letter_dups"] += 1
                cls_c = ("dup",)
            else:
                c["seen"].add(tm_c)
                if not filed_raw or not filed_raw[:4].isdigit():
                    c["blank"] += 1
                    cls_c = ("blank",)
                else:
                    c["years_all"][filed_raw[:4]] += 1
                    filed = parse_date(filed_raw)
                    if filed is None:
                        c["unparseable"] += 1
                        cls_c = ("unparseable",)
                    else:
                        if filed_raw[:4] >= "2010" and regd_c \
                                and status_c in NEG_STATUSES:
                            c["nwr_post2010"] += 1
                        if 2010 <= filed.year <= 2016:
                            year = str(filed.year)
                            d = c["per_year"][year]
                            d["n"] += 1
                            if regd_c:
                                d["pos"] += 1
                                if status_c in NEG_STATUSES:
                                    c["nwr_elig"] += 1
                                cls_c = ("inwin", year, "pos")
                            elif status_c in NEG_STATUSES:
                                d["neg"] += 1
                                cls_c = ("inwin", year, "neg")
                            else:
                                d["cens"] += 1
                                c["censored_status"][status_c or "(blank)"] += 1
                                cls_c = ("inwin", year, "cens")
                        else:
                            c["outwin"][str(filed.year)] += 1
                            cls_c = ("outwin", str(filed.year))

            # ---- B1: same dedup decisions as C, shifted reads ----
            if cls_c[0] == "dup":
                b1["dup"] += 1
            else:
                filed_b = fields[12].strip()
                status_b = fields[7].strip()
                regd_b = fields[14].strip()
                if not filed_b or not filed_b[:4].isdigit():
                    b1["blank"] += 1
                else:
                    key = filed_b[:4]
                    if key >= "2010":
                        d = b1["per_year"][key]
                        d["n"] += 1
                        if regd_b:
                            d["pos"] += 1
                        elif status_b in NEG_STATUSES:
                            d["neg"] += 1
                        else:
                            d["cens"] += 1

            # ---- B2: filed check first, then string-key dedup ----
            filed_b2 = fields[12].strip()
            status_b2 = fields[7].strip()
            regd_b2 = fields[14].strip()
            if not filed_b2 or not filed_b2[:4].isdigit():
                b2["blank"] += 1
            elif tm_c in b2["seen"]:
                b2["dup"] += 1
            else:
                b2["seen"].add(tm_c)
                key = filed_b2[:4]
                if key >= "2010":
                    d = b2["per_year"][key]
                    d["n"] += 1
                    if regd_b2:
                        d["pos"] += 1
                    elif status_b2 in NEG_STATUSES:
                        d["neg"] += 1
                    else:
                        d["cens"] += 1

        # ---------------- pipe-row census ----------------
        is_pipe = raw_len != 62
        if is_pipe and rec is not None:
            classes_ok = all(rec[17 + i].strip() in ("0", "1", "")
                             for i in range(45))
            filed_dt = parse_date(rec[12].strip())
            pipe_census.append({
                "mark": rec[0].strip(),
                "raw_fields": raw_len,
                "recovered_filed": rec[12].strip(),
                "filed_parses": filed_dt.isoformat() if filed_dt else None,
                "recovered_status": rec[7].strip(),
                "status_in_vocab": rec[7].strip() in KNOWN_STATUS_VOCAB,
                "shifted_status_read": fields[7].strip(),
                "shifted_status_in_vocab": fields[7].strip()
                                           in KNOWN_STATUS_VOCAB,
                "recovered_regd": rec[14].strip(),
                "shifted_filed_read": fields[12].strip(),
                "classes_binary": classes_ok,
                "cls_old": list(cls_a),
                "cls_new": list(cls_c),
            })

        # ---------------- per-row diff A vs C ----------------
        if cls_a != cls_c:
            diffs.append({
                "mark": (rec[0].strip() if rec is not None
                         else fields[0].strip()),
                "pipe": is_pipe,
                "raw_fields": raw_len,
                "old": list(cls_a),
                "new": list(cls_c),
            })

    # ---------------- pass 2: imported build.iter_records cross-check ----
    x = {"rows": 0, "blank": 0, "unparseable": 0, "dup": 0, "letter_rows": 0,
         "letter_dups": 0, "seen": set(), "outwin": Counter(),
         "per_year": defaultdict(new_year), "nwr_elig": 0, "nwr_post2010": 0}
    hazards = ipo_build.new_hazards()
    for rec in ipo_build.iter_records(ZIP_PATH, hazards):
        x["rows"] += 1
        tm = rec[0].strip().replace(" ", "")
        filed_raw = rec[12].strip()
        status = rec[7].strip()
        regd = rec[14].strip()
        try:
            int(tm.replace("UK", "").lstrip("0") or "0")
            letter_row = False
        except ValueError:
            letter_row = True
        if letter_row:
            x["letter_rows"] += 1
        if tm in x["seen"]:
            x["dup"] += 1
            if letter_row:
                x["letter_dups"] += 1
            continue
        x["seen"].add(tm)
        if not filed_raw or not filed_raw[:4].isdigit():
            x["blank"] += 1
            continue
        filed = parse_date(filed_raw)
        if filed is None:
            x["unparseable"] += 1
            continue
        if filed_raw[:4] >= "2010" and regd and status in NEG_STATUSES:
            x["nwr_post2010"] += 1
        if not (2010 <= filed.year <= 2016):
            x["outwin"][str(filed.year)] += 1
            continue
        d = x["per_year"][str(filed.year)]
        d["n"] += 1
        if regd:
            d["pos"] += 1
            if status in NEG_STATUSES:
                x["nwr_elig"] += 1
        elif status in NEG_STATUSES:
            d["neg"] += 1
        else:
            d["cens"] += 1

    def inwin(store):
        return {y: {b: store[y][b] for b in ("n", "pos", "neg", "cens")}
                for y in YEARS}

    problems = []

    def check(name, got, want):
        if got != want:
            problems.append(f"{name}: got {got} != want {want}")

    # pass A vs the frozen discovery aggregates (verbatim reproduction)
    check("A.rows_seen", a["rows"], FROZEN["rows_seen"])
    check("A.field_counts", dict(a["field_counts"]),
          {int(k): v for k, v in FROZEN["field_count_distribution"].items()})
    check("A.distinct", len(a["seen"]), FROZEN["distinct_marks_total"])
    check("A.shift_rows", a["shift_rows"],
          FROZEN["rows_with_field_count_ne_62"])
    check("A.bad_short", a["bad_short"], FROZEN["bad_short_rows"])
    check("A.dup", a["dup"], FROZEN["owner_dup_rows"])
    check("A.blank", a["blank"], FROZEN["blank_or_bad_filed"])
    check("A.sortedness", a["sortedness"], FROZEN["sortedness_violations"])
    check("A.nwr", a["nwr"], FROZEN["neg_with_regdate"])
    check("A.years_all", dict(a["years_all"]),
          {k: int(v) for k, v in FROZEN["years_all"].items()})
    check("A.per_year", inwin(a["per_year"]),
          {y: {"n": v["n"], "pos": v["pos"], "neg": v["neg"], "cens": v["cens"]}
           for y, v in FROZEN["per_year_2010plus"].items() if y in YEARS})
    check("A.inwin == EXPECTED.per_year", inwin(a["per_year"]),
          EXPECTED_PER_YEAR)
    a_postwin = {y: {"n": a["per_year"][y]["n"], "pos": a["per_year"][y]["pos"],
                     "neg": a["per_year"][y]["neg"],
                     "cens": a["per_year"][y]["cens"]}
                 for y in a["per_year"] if y not in YEARS}
    check("A.postwin years", sorted(a_postwin),
          sorted(y for y in FROZEN["per_year_2010plus"] if y not in YEARS))

    # pass C vs the ipo-tm-002 worker build's measured numbers
    check("C.data_rows", c["rows"], BUILD_MEASURED["data_rows"])
    check("C.field_counts", dict(c["field_counts"]),
          {62: 1_188_910, 63: 76, 64: 15, 65: 3})
    check("C.distinct", len(c["seen"]), BUILD_MEASURED["distinct_marks"])
    check("C.dup", c["dup"], BUILD_MEASURED["dup_rows"])
    check("C.letter_rows", c["letter_rows"],
          BUILD_MEASURED["letter_suffix_rows"])
    check("C.letter_dups", c["letter_dups"], BUILD_MEASURED["letter_suffix_dups"])
    check("C.blank", c["blank"], BUILD_MEASURED["blank_or_bad_filed"])
    check("C.unparseable", c["unparseable"], BUILD_MEASURED["unparseable_filed"])
    check("C.nwr", (c["nwr_elig"], c["nwr_post2010"]),
          (BUILD_MEASURED["neg_with_regdate_eligible"],
           BUILD_MEASURED["neg_with_regdate_post2010"]))
    check("C.per_year", inwin(c["per_year"]), BUILD_MEASURED["per_year"])

    # pass 2 (imported build.iter_records) == pass C: zero drift
    check("X.rows", x["rows"], c["rows"])
    check("X.field_counts", dict(hazards["field_counts"]),
          dict(c["field_counts"]))
    check("X.pipe_recovered", hazards["pipe_recovered"], 94)
    check("X.short_rows", hazards["short_rows"], c["short"])
    check("X.trailing", hazards["trailing_partial_line"], 0)
    check("X.distinct", len(x["seen"]), len(c["seen"]))
    check("X.dup", x["dup"], c["dup"])
    check("X.blank", x["blank"], c["blank"])
    check("X.unparseable", x["unparseable"], c["unparseable"])
    check("X.letter", (x["letter_rows"], x["letter_dups"]),
          (c["letter_rows"], c["letter_dups"]))
    check("X.per_year", inwin(x["per_year"]), inwin(c["per_year"]))
    check("X.nwr", (x["nwr_elig"], x["nwr_post2010"]),
          (c["nwr_elig"], c["nwr_post2010"]))

    # attribution closure: per-row diffs must equal the measured deltas
    delta = defaultdict(lambda: Counter())
    blank_delta = 0
    for d in diffs:
        old, new = d["old"], d["new"]
        if old[0] == "inwin":
            delta[old[1]][old[2]] -= 1
        elif old[0] == "blank":
            blank_delta -= 1
        if new[0] == "inwin":
            delta[new[1]][new[2]] += 1
        elif new[0] == "blank":
            blank_delta += 1
    closure = {y: {b: delta[y].get(b, 0) for b in ("n", "pos", "neg", "cens")}
               for y in YEARS}
    for y in closure:
        closure[y]["n"] = (closure[y]["pos"] + closure[y]["neg"]
                           + closure[y]["cens"])
    check("closure.per_year", closure, TARGET_DELTAS["per_year"])
    check("closure.blank", blank_delta, TARGET_DELTAS["blank_data_rows"])

    # aggregate deltas, independent of the diff list
    agg = {y: {b: inwin(c["per_year"])[y][b] - inwin(a["per_year"])[y][b]
               for b in ("n", "pos", "neg", "cens")} for y in YEARS}
    check("aggregate.per_year", agg, TARGET_DELTAS["per_year"])
    check("aggregate.blank", c["blank"] - (a["blank"] - 1),
          TARGET_DELTAS["blank_data_rows"])

    # pipe-only closure: every pipe row that C scores in-window must appear as
    # a diff add; pipe rows never score in A (shifted reads never yield an
    # in-window year), so the pipe diff adds must equal the census counts.
    pipe_adds = Counter()
    for d in diffs:
        if d["pipe"] and d["new"][0] == "inwin":
            pipe_adds[(d["new"][1], d["new"][2])] += 1
    census_inwin = Counter()
    for p in pipe_census:
        if p["cls_new"] and p["cls_new"][0] == "inwin":
            census_inwin[(p["cls_new"][1], p["cls_new"][2])] += 1
    check("pipe closure", dict(pipe_adds), dict(census_inwin))

    non_pipe = [d for d in diffs if not d["pipe"]]
    census_ok = {
        "census_rows": len(pipe_census),
        "status_in_vocab": sum(1 for p in pipe_census if p["status_in_vocab"]),
        "shifted_status_in_vocab": sum(1 for p in pipe_census
                                       if p["shifted_status_in_vocab"]),
        "filed_parses": sum(1 for p in pipe_census if p["filed_parses"]),
        "classes_binary": sum(1 for p in pipe_census if p["classes_binary"]),
        "in_window_scored": sum(census_inwin.values()),
        "old_blank_artifact_rows": sum(1 for p in pipe_census
                                        if p["cls_old"] == ["blank"]),
        "inwin_by_year_bucket": {f"{y}/{b}": n
                                 for (y, b), n in sorted(census_inwin.items())},
    }

    result = {
        "run": {"date": "2026-10-30", "zip_sha256": PINNED_SHA256,
                "wall_s": round(time.time() - t0, 1)},
        "pass_a_reproduces_frozen": not [p for p in problems
                                         if p.startswith("A.")],
        "pass_c_matches_worker_build": not [p for p in problems
                                            if p.startswith(("C.", "X."))],
        "closure_ok": not [p for p in problems
                           if p.startswith(("closure.", "aggregate.",
                                            "pipe "))],
        "b_provenance": {
            "b1_blank": b1["blank"], "b1_dup": b1["dup"],
            "b1_per_year": inwin(b1["per_year"]),
            "b2_blank": b2["blank"], "b2_dup": b2["dup"],
            "b2_per_year": inwin(b2["per_year"]),
            "note": ("EXPECTED.blank_or_bad_filed_head=52 provenance: pass A "
                     "counts 53 incl. the header row (52 data rows)."),
        },
        "c_postwin_out_of_window": dict(sorted(c["outwin"].items())),
        "a_out_of_window": {k: v for k, v in sorted(a["years_all"].items())
                            if k < "2010"},
        "diff_rows": diffs,
        "non_pipe_diffs": non_pipe,
        "pipe_census_summary": census_ok,
        "pipe_census": pipe_census,
        "problems": problems,
    }
    OUT.write_text(json.dumps(result, indent=1) + "\n")

    print(f"wall {result['run']['wall_s']}s")
    print(f"pass A reproduces frozen discovery aggregates: "
          f"{result['pass_a_reproduces_frozen']}")
    print(f"pass C matches ipo-tm-002 worker build:       "
          f"{result['pass_c_matches_worker_build']}")
    print(f"closure (+58 scored, -18 blank) exact:         "
          f"{result['closure_ok']}")
    print(f"pipe census: {json.dumps(census_ok)}")
    print(f"non-pipe classification diffs: {len(non_pipe)} "
          f"(dedup-key effects)")
    print(f"B1 blank {b1['blank']} dup {b1['dup']} | "
          f"B2 blank {b2['blank']} dup {b2['dup']}")
    for p in problems:
        print("PROBLEM:", p)
    print(f"{'RECONCILIATION CLOSED' if not problems else 'MISMATCH'} -> {OUT}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
