#!/usr/bin/env python3
"""Reproduce the TED CSV-subset measurements recorded in
candidates/ted-procurement-single-bid/record.json (2026-10-27): zip sizes,
CSV headers, FUTURE_CAN_ID population and the CAN base-rate prefix samples.

Bulk data never leaves the wire: only the first 256 KiB of each zip is read
(HTTP Range), the deflate stream is partially inflated (~1.5-3 MB of CSV), and
the rows recovered are the year file's leading notices (ordered by notice ID =
early-January). The samples are therefore NOT year-representative; they are
bounded discovery evidence. Run from anywhere: python3 probe_csv_prefix.py
"""
import csv
import io
import struct
import time
import urllib.request
import zlib

UA = {
    "User-Agent": "scout-dataset-factory/1.0 (dataset discovery)",
    "From": "scout@nousresearch.com",
}
STORE = "https://data.europa.eu/api/hub/store/data"
FETCH = 262144
MAXOUT = 3_000_000


def zip_head(url, fetch=FETCH, maxout=MAXOUT):
    """Ranged read of the zip prefix; return (decoded text, total size, seconds)."""
    t0 = time.time()
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes=0-{fetch - 1}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        total = r.headers.get("Content-Range", "?").split("/")[-1]
        blob = r.read()
    el = time.time() - t0
    assert blob[:4] == b"PK\x03\x04", "not a zip stream"
    method, = struct.unpack("<H", blob[8:10])
    nlen, elen = struct.unpack("<HH", blob[26:30])
    name = blob[30:30 + nlen].decode("utf-8", "replace")
    if method == 8:
        d = zlib.decompressobj(-15)
        out = d.decompress(blob[30 + nlen + elen:], maxout) + d.flush()
        return name, out.decode("utf-8", "replace"), total, el
    return name, blob[30 + nlen + elen:30 + nlen + elen + 4000].decode("utf-8", "replace"), total, el


def drop_truncated(text):
    return "\n".join(text.split("\n")[:-1])


def main():
    # CN schema + FUTURE_CAN_ID population (2019 pre-eForms, 2023 eForms era)
    for year in (2019, 2023):
        name, text, total, el = zip_head(f"{STORE}/ted-contract-notices-{year}.zip")
        lines = text.split("\n")
        print(f"CN {year}: entry={name} zip_total={total} bytes fetch={el:.2f}s")
        print("  header:", lines[0].replace("\r", "")[:1800])
        rows = csv.DictReader(io.StringIO(drop_truncated(text)))
        n = with_id = est = 0
        for row in rows:
            n += 1
            if (row.get("FUTURE_CAN_ID") or "").strip():
                with_id += 1
                if (row.get("FUTURE_CAN_ID_ESTIMATED") or "").strip() == "1":
                    est += 1
            else:
                break
        print(f"  complete rows={n} FUTURE_CAN_ID populated={with_id} estimated=1 in {est}")
        time.sleep(1.0)

    # CAN base-rate prefix samples
    for year in (2019, 2021, 2023):
        name, text, total, el = zip_head(f"{STORE}/ted-contract-award-notices-{year}.zip")
        if year == 2019:
            print(f"\nCAN 2019: entry={name} zip_total={total} bytes")
            print("  header:", text.split("\n")[0].replace("\r", "")[:1800])
        rows = csv.DictReader(io.StringIO(drop_truncated(text)))
        n = offers_pop = single = multi = zero = nonaward = dt_award = 0
        notices = set()
        for row in rows:
            n += 1
            notices.add((row["ID_NOTICE_CAN"] or "").strip())
            v = (row.get("NUMBER_OFFERS") or "").strip()
            if v != "":
                offers_pop += 1
                try:
                    iv = int(float(v))
                    if iv == 1:
                        single += 1
                    elif iv == 0:
                        zero += 1
                    else:
                        multi += 1
                except ValueError:
                    pass
            if (row.get("INFO_ON_NON_AWARD") or "").strip() != "":
                nonaward += 1
            if (row.get("DT_AWARD") or "").strip() != "":
                dt_award += 1
        print(f"CAN {year}: rows={n} notices={len(notices)} "
              f"NUMBER_OFFERS populated={offers_pop} ({offers_pop / n:.1%}) "
              f"single-bid={single} ({single / offers_pop:.1%} of populated) "
              f"multi={multi} zero={zero} "
              f"INFO_ON_NON_AWARD set={nonaward} ({nonaward / n:.1%}) "
              f"DT_AWARD set={dt_award} ({dt_award / n:.1%}) [fetch {el:.2f}s]")
        time.sleep(1.0)


if __name__ == "__main__":
    main()
