#!/usr/bin/env python3
"""Standing capture: pin small source files whose reopen conditions need
repeated observation over time, before the publisher replaces them.

Two parked East Asia candidates name this mechanism as their recorded reopen
path (see their next_action):

- tw-taipower-major-outage-register: the register is a single-year replacement
  file; skipping a yearly vintage loses it permanently. Reopen review when
  >= 4 distinct yearly vintages exist (bytes committed under vintages/).
- hk-red-tide-sighting: the publication lag is undocumented and must be
  measured from >= 12 consecutive captures (ledger below; bytes stay on the
  host under /opt/data/standing-captures/).

Run from the repo root (intended: once per East Asia discovery tick, and any
other session that passes by):

    python3 scripts/standing-capture.py --all

Each run appends one ledger entry per source to
candidates/<id>/standing-captures.json (capture time, sha256, size, row count,
max/min date in the configured date column, rows added/removed vs the previous
entry, publication lag in days). Bytes are always copied to the host-persistent
store; when a source's configured commit_bytes is true and the digest changed,
the bytes are ALSO written into candidates/<id>/vintages/ so the distinct
vintage is durable in git. Failing to fetch one source does not stop the others;
a source that fails on every run is reported, not silently skipped.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory.admission import require
from factory.common import FactoryError
HOST_STORE = Path("/opt/data/standing-captures")
CONFIG_PATH = ROOT / "scripts" / "standing-capture-sources.json"
UA = "dataset-factory-standing-capture/1.0 (research evidence pinning)"

DATE_FORMATS = ("%Y-%m-%d", "%Y%m%dT%H%M%S")


def parse_date(tok):
    tok = (tok or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(tok, fmt).date()
        except ValueError:
            continue
    return None


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def csv_rows(data):
    text = data.decode("utf-8-sig", "replace")
    return list(csv.DictReader(io.StringIO(text, newline="")))


def stats(rows, date_col):
    dates = [parse_date(r.get(date_col, "")) for r in rows]
    dates = [d for d in dates if d]
    return {
        "rows": len(rows),
        "max_date": max(dates).isoformat() if dates else None,
        "min_date": min(dates).isoformat() if dates else None,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="capture every configured source")
    ap.add_argument("--source", action="append", default=[], help="capture only this source id")
    args = ap.parse_args(argv)
    if not args.all and not args.source:
        ap.print_help()
        return 2
    try:
        require(ROOT, "discovery collection")
    except FactoryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    config = json.loads(CONFIG_PATH.read_text())
    now = dt.datetime.now(dt.timezone.utc)
    failures = []
    for src in config["sources"]:
        sid = src["id"]
        if args.source and sid not in args.source:
            continue
        cand_dir = ROOT / "candidates" / src["candidate"]
        ledger_path = cand_dir / "standing-captures.json"
        ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else []
        try:
            data = fetch(src["url"])
        except Exception as exc:  # keep the ledger honest about failures
            ledger.append({"captured_at": now.isoformat(timespec="seconds"),
                           "source": sid, "error": f"{type(exc).__name__}: {exc}"})
            ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
            failures.append(f"{sid}: {type(exc).__name__}")
            continue
        digest = hashlib.sha256(data).hexdigest()
        entry = {"captured_at": now.isoformat(timespec="seconds"), "source": sid,
                 "sha256": digest, "bytes": len(data)}
        rows = csv_rows(data)
        entry.update(stats(rows, src["date_col"]))
        prev = next((e for e in reversed(ledger) if "sha256" in e), None)
        if prev:
            delta = entry.get("rows", 0) - prev.get("rows", 0)
            entry["rows_delta_vs_previous"] = delta
            if delta < 0:
                entry["rows_removed"] = True  # revision evidence: rows left the file
        if entry.get("max_date"):
            lag = (now.date() - dt.date.fromisoformat(entry["max_date"])).days
            entry["publication_lag_days"] = lag
        if prev and prev.get("sha256") == digest:
            entry["unchanged_since_previous"] = True
        # host-persistent byte store (always)
        host_dir = HOST_STORE / src["candidate"]
        host_dir.mkdir(parents=True, exist_ok=True)
        (host_dir / f"{now:%Y-%m-%dT%H%M%SZ}__{digest[:16]}.{src['ext']}").write_bytes(data)
        # durable-in-git byte store (only configured sources, only on change)
        if src.get("commit_bytes") and not entry.get("unchanged_since_previous"):
            vin_dir = cand_dir / "vintages"
            vin_dir.mkdir(parents=True, exist_ok=True)
            (vin_dir / f"{now:%Y-%m-%d}__{digest[:16]}.{src['ext']}").write_bytes(data)
            entry["bytes_committed"] = True
        ledger.append(entry)
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
        print(f"{sid}: sha256 {digest[:16]} bytes {entry['bytes']} rows {entry.get('rows')} "
              f"max_date {entry.get('max_date')} lag {entry.get('publication_lag_days')}d"
              + (" UNCHANGED" if entry.get("unchanged_since_previous") else ""))
    if failures:
        print("FAILURES:", "; ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
