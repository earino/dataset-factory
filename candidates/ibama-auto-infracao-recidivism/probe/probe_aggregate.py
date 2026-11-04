#!/usr/bin/env python3
"""Discovery-owned aggregate probe over IBAMA's full current-vintage auto de infracao table.

One streaming pass, source aggregates only. Builds NO dataset: no train/eval/holdout
files, no shipped labels, no gate, no scoring (the record's next_action step 1).

Measured (record next_action wording):
  - per-lavratura-year row counts (raw vs deduped on SEQ_AUTO_INFRACAO)
  - share of rows with a valid non-empty CPF_CNPJ_INFRACAO (pessoa fisica vs CNPJ),
    cross-checked against the publisher's TP_PESSOA_INFRATOR
  - effective-lavratura source mix per year (DAT_HORA_AUTO_INFRACAO vs DT_LANCAMENTO)
  - 12-month re-autuacao base rate per year, first-time vs repeat entities,
    naive and right-censored at the extract's max lavratura
  - clustered positive counts by entity and by SEQ_ACAO_FISCALIZATORIA per window
    (record windows: train 2005-2015 / eval 2016-2019 / holdout 2022-2025,
    plus pre-2005, gap 2020-2021, 2026 context buckets)
  - SIT_CANCELADO / DES_STATUS_FORMULARIO mix per year, TP_ORIGEM_REGISTRO_AUTO
    (SICAFI vs AIe regime) per year, and current-vintage revision evidence
    (DT_ULT_ALTERACAO recency, TP_ULT_ALTERACAO mix, export stamps)

Structural failures exit nonzero and still write a partial report. A scientific
shortfall (few positives, weak entity coverage) is a finding, not a failure.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
import time
import traceback
import urllib.request
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

csv.field_size_limit(16 * 1024 * 1024)  # DS_WKT polygons can exceed the 128 KB default

URL = ("https://stibamadadosabertosprd.blob.core.windows.net/dados-abertos/"
       "dados/SIFISC/auto_infracao/auto_infracao/auto_infracao_csv.zip")

# Columns actually served (header verified 2026-11-04 via a bounded 256 KB Range +
# raw-inflate probe from the coordinator; see candidate notes).
COLS = {
    "seq": "SEQ_AUTO_INFRACAO",
    "des_status": "DES_STATUS_FORMULARIO",
    "sit": "SIT_CANCELADO",
    "tp_pessoa": "TP_PESSOA_INFRATOR",
    "entity": "CPF_CNPJ_INFRATOR",
    "dat_hora": "DAT_HORA_AUTO_INFRACAO",
    "dt_lanc": "DT_LANCAMENTO",
    "dt_ult_alt": "DT_ULT_ALTERACAO",
    "tp_ult_alt": "TP_ULT_ALTERACAO",
    "stamp": "ULTIMA_ATUALIZACAO_RELATORIO",
    "seq_acao": "SEQ_ACAO_FISCALIZATORIA",
    "uf": "UF",
    "cod_mun": "COD_MUNICIPIO",
    "tp_origem": "TP_ORIGEM_REGISTRO_AUTO",
}
REQUIRED = ("seq", "entity", "dat_hora", "dt_lanc")

WINDOWS = [
    ("pre_2005", None, 2004),
    ("train_2005_2015", 2005, 2015),
    ("eval_2016_2019", 2016, 2019),
    ("gap_2020_2021", 2020, 2021),
    ("holdout_2022_2025", 2022, 2025),
    ("post_2025", 2026, None),
]

GLOB_TS = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]"
GLOB_DATE = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"

ENT_KIND_MEMO: dict[str, str] = {}
_PUNCT = str.maketrans("", "", "./-,")


def ent_kind(raw: str) -> str:
    k = ENT_KIND_MEMO.get(raw)
    if k is None:
        if not raw:
            k = "missing"
        else:
            digits = raw.translate(_PUNCT)
            k = "cpf" if len(digits) == 11 and digits.isdigit() else (
                "cnpj" if len(digits) == 14 and digits.isdigit() else "nonstd")
            if raw != digits:
                k += "_punct"
        if len(ENT_KIND_MEMO) < 2_000_000:
            ENT_KIND_MEMO[raw] = k
    return k


def die(partial_path: Path, stage: str, exc: Exception) -> None:
    """Write a partial report with the traceback, then re-raise."""
    payload = {"stage": stage, "error": f"{type(exc).__name__}: {exc}",
               "traceback": traceback.format_exc()[-6000:]}
    try:
        partial_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    except OSError:
        pass
    raise


def download(out: Path, report: dict) -> Path:
    t0 = time.monotonic()
    h = hashlib.sha256()
    n = 0
    req = urllib.request.Request(URL, headers={"User-Agent": "scout-worker-probe/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r, out.open("wb") as f:
        report["zip_last_modified"] = r.headers.get("Last-Modified")
        report["zip_content_length"] = r.headers.get("Content-Length")
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            n += len(chunk)
            h.update(chunk)
            f.write(chunk)
    report["zip_bytes_downloaded"] = n
    report["zip_sha256"] = h.hexdigest()
    report["download_seconds"] = round(time.monotonic() - t0, 1)
    return out


def open_member_rows(path: Path):
    """Yield (header_map, row_iter) for one extracted CSV member."""
    f = path.open("r", encoding="utf-8-sig", newline="")
    reader = csv.reader(f, delimiter=";", quotechar='"')
    header = [h.strip() for h in next(reader, None) or []]
    if not header:
        f.close()
        return None
    colmap = {k: header.index(v) for k, v in COLS.items() if v in header}
    return f, reader, colmap, header


def load_members(work: Path, db: sqlite3.Connection, report: dict) -> None:
    cur = db.cursor()
    cur.executescript("""
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA cache_size=-200000;
        CREATE TABLE autos(
            seq INTEGER PRIMARY KEY,
            des_status TEXT, sit TEXT, tp_pessoa TEXT, entity TEXT,
            dat_hora TEXT, dt_lanc TEXT, dt_ult_alt TEXT, tp_ult_alt TEXT,
            stamp TEXT, seq_acao TEXT, uf TEXT, cod_mun TEXT, tp_origem TEXT,
            n_occ INTEGER NOT NULL DEFAULT 1,
            ent_mis INTEGER NOT NULL DEFAULT 0, eff_mis INTEGER NOT NULL DEFAULT 0,
            sit_mis INTEGER NOT NULL DEFAULT 0, des_mis INTEGER NOT NULL DEFAULT 0
        );
    """)
    upsert = """
        INSERT INTO autos (seq, des_status, sit, tp_pessoa, entity, dat_hora,
                           dt_lanc, dt_ult_alt, tp_ult_alt, stamp, seq_acao,
                           uf, cod_mun, tp_origem)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(seq) DO UPDATE SET
            n_occ = n_occ + 1,
            ent_mis = MAX(ent_mis, CASE WHEN excluded.entity IS autos.entity THEN 0 ELSE 1 END),
            eff_mis = MAX(eff_mis, CASE WHEN excluded.dat_hora IS autos.dat_hora
                                        AND excluded.dt_lanc IS autos.dt_lanc THEN 0 ELSE 1 END),
            sit_mis = MAX(sit_mis, CASE WHEN excluded.sit IS autos.sit THEN 0 ELSE 1 END),
            des_mis = MAX(des_mis, CASE WHEN excluded.des_status IS autos.des_status THEN 0 ELSE 1 END)
    """
    zpath = work / "auto_infracao_csv.zip"
    members: list = []
    with zipfile.ZipFile(zpath) as zf:
        names = sorted(zf.namelist())
        report["zip_members"] = len(names)
        for name in names:
            info = zf.getinfo(name)
            dest = work / "csv" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, dest.open("wb") as dst:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    dst.write(chunk)
            members.append((name, info.file_size))

    loaded_any = False
    member_rows: list = []
    t0 = time.monotonic()
    for name, usize in members:
        path = work / "csv" / name
        opened = open_member_rows(path)
        if opened is None:
            member_rows.append({"member": name, "uncompressed_bytes": usize, "status": "empty"})
            path.unlink(missing_ok=True)
            continue
        f, reader, colmap, header = opened
        missing = [COLS[k] for k in REQUIRED if k not in colmap]
        if missing:
            member_rows.append({"member": name, "uncompressed_bytes": usize,
                                "status": f"skipped_missing_columns {missing}",
                                "header": header[:90]})
            f.close()
            path.unlink(missing_ok=True)
            continue
        idx = {k: colmap.get(k, -1) for k in COLS}
        ncols = len(header)
        raw = 0
        bad_seq = 0
        ragged = 0
        batch: list = []
        for row in reader:
            raw += 1
            if len(row) != ncols:
                ragged += 1
            vals = []
            for key in COLS:
                i = idx[key]
                v = row[i].strip() if 0 <= i < len(row) else ""
                vals.append(v)
            try:
                seq = int(vals[0])
            except ValueError:
                bad_seq += 1
                continue
            batch.append((seq, *vals[1:]))
            if len(batch) >= 50000:
                cur.executemany(upsert, batch)
                batch.clear()
        if batch:
            cur.executemany(upsert, batch)
        db.commit()
        f.close()
        path.unlink(missing_ok=True)  # scratch CSV is fully loaded; keep disk bounded
        loaded_any = True
        member_rows.append({"member": name, "uncompressed_bytes": usize,
                            "status": "loaded", "raw_rows": raw,
                            "bad_seq": bad_seq, "ragged": ragged})
    zpath.unlink(missing_ok=True)  # zip sha256 is already recorded
    report["members"] = member_rows
    report["load_seconds"] = round(time.monotonic() - t0, 1)
    if not loaded_any:
        raise RuntimeError("no member carried the required columns; see report['members']")


def sql_scalar(db: sqlite3.Connection, sql: str) -> tuple | None:
    return db.execute(sql).fetchone()


def build_eff(db: sqlite3.Connection, report: dict) -> None:
    """Normalize the effective lavratura into a sortable ISO string, SQL fast path."""
    cur = db.cursor()
    fmt_probe = {}
    for col in ("dat_hora", "dt_lanc"):
        rows = cur.execute(f"""
            SELECT CASE
                WHEN {col} = '' THEN 'empty'
                WHEN length({col}) = 19 AND {col} GLOB '{GLOB_TS}' THEN 'ts19'
                WHEN length({col}) = 10 AND {col} GLOB '{GLOB_DATE}' THEN 'date10'
                ELSE 'other' END AS fmt, COUNT(*)
            FROM autos GROUP BY 1
        """).fetchall()
        fmt_probe[col] = dict(rows)
        others = cur.execute(f"""
            SELECT DISTINCT {col} FROM autos
            WHERE {col} <> '' AND NOT (length({col}) = 19 AND {col} GLOB '{GLOB_TS}')
              AND NOT (length({col}) = 10 AND {col} GLOB '{GLOB_DATE}')
            LIMIT 5
        """).fetchall()
        if others:
            fmt_probe[f"{col}_other_samples"] = [r[0] for r in others]
    report["datetime_format_probe"] = fmt_probe

    cur.execute("ALTER TABLE autos ADD COLUMN eff_ts TEXT")
    cur.execute(f"""
        UPDATE autos SET eff_ts = CASE
            WHEN length(dat_hora) = 19 AND dat_hora GLOB '{GLOB_TS}' THEN dat_hora
            WHEN length(dat_hora) = 10 AND dat_hora GLOB '{GLOB_DATE}' THEN dat_hora || ' 00:00:00'
            WHEN length(dt_lanc) = 19 AND dt_lanc GLOB '{GLOB_TS}' THEN substr(dt_lanc, 1, 19)
            WHEN length(dt_lanc) = 10 AND dt_lanc GLOB '{GLOB_DATE}' THEN dt_lanc || ' 00:00:00'
            ELSE NULL
        END
    """)
    db.commit()
    # Bounded python fallback for rows the SQL patterns did not classify.
    leftover = cur.execute(
        "SELECT COUNT(*) FROM autos WHERE (dat_hora <> '' OR dt_lanc <> '') AND eff_ts IS NULL"
    ).fetchone()[0]
    report["eff_null_despite_raw_dates"] = leftover
    if leftover:
        memo: dict[str, str] = {}
        rows = cur.execute(
            "SELECT seq, dat_hora, dt_lanc FROM autos "
            "WHERE (dat_hora <> '' OR dt_lanc <> '') AND eff_ts IS NULL"
        ).fetchall()
        fixed = 0
        samples = []
        for seq, dh, dl in rows:
            iso = None
            for raw in (dh, dl):
                if not raw:
                    continue
                if raw in memo:
                    iso = memo[raw]
                    break
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y/%m/%d %H:%M:%S",
                            "%Y/%m/%d"):
                    try:
                        iso = datetime.strptime(raw.strip()[:19].strip(), fmt).strftime(
                            "%Y-%m-%d %H:%M:%S" if fmt != "%Y-%m-%d" and fmt != "%d/%m/%Y" and fmt != "%Y/%m/%d"
                            else "%Y-%m-%d 00:00:00")
                        memo[raw] = iso
                        break
                    except ValueError:
                        continue
                if iso:
                    break
            if iso:
                cur.execute("UPDATE autos SET eff_ts = ? WHERE seq = ?", (iso, seq))
                fixed += 1
                if len(samples) < 8:
                    samples.append({"seq": seq, "dat_hora": dh, "dt_lanc": dl, "eff_ts": iso})
        db.commit()
        report["eff_python_fallback_fixed"] = fixed
        report["eff_python_fallback_samples"] = samples
        remaining = cur.execute(
            "SELECT COUNT(*) FROM autos WHERE (dat_hora <> '' OR dt_lanc <> '') AND eff_ts IS NULL"
        ).fetchone()[0]
        if remaining:
            report["eff_unparseable_remaining"] = remaining
    cur.execute("""
        CREATE INDEX idx_autos_label ON autos(entity, eff_ts, seq, seq_acao, uf, cod_mun)
        WHERE entity <> '' AND eff_ts IS NOT NULL
    """)
    db.commit()


def one(db: sqlite3.Connection, sql: str) -> dict:
    return dict(db.execute(sql).fetchall())


def per_year_sql(db: sqlite3.Connection) -> tuple[dict, dict]:
    scalar_years = {}
    for row in db.execute(f"""
        SELECT substr(eff_ts, 1, 4) AS yr, COUNT(*),
            SUM(CASE WHEN entity <> '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN entity GLOB '[0-9]*' AND length(replace(replace(replace(entity, '.', ''), '/', ''), '-', '')) = 11 THEN 1 ELSE 0 END),
            SUM(CASE WHEN entity GLOB '[0-9]*' AND length(replace(replace(replace(entity, '.', ''), '/', ''), '-', '')) = 14 THEN 1 ELSE 0 END),
            SUM(CASE WHEN entity <> '' AND NOT (entity GLOB '[0-9]*') THEN 1 ELSE 0 END),
            SUM(CASE WHEN dat_hora <> '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN dat_hora = '' AND dt_lanc <> '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN dat_hora <> '' AND dt_lanc <> '' AND substr(dat_hora, 1, 10) = substr(dt_lanc, 1, 10) THEN 1 ELSE 0 END),
            SUM(CASE WHEN dat_hora <> '' AND dt_lanc <> '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN dt_ult_alt <> '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN tp_ult_alt <> '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN eff_ts IS NULL THEN 1 ELSE 0 END)
        FROM autos GROUP BY 1
    """):
        y = row[0] or "none"
        scalar_years[y] = dict(zip(
            ("rows", "valid_entity", "cpf11", "cnpj14", "nonstd_alpha", "dat_hora_rows",
             "dt_lanc_only_rows", "dh_dl_same_day", "dh_dl_both", "altered_rows",
             "tp_alt_rows", "eff_null"), row[1:]))
    nested = {}
    for col in ("sit", "des_status", "tp_pessoa", "tp_origem", "tp_ult_alt"):
        d = {}
        for yr, val, cnt in db.execute(
                f"SELECT substr(eff_ts,1,4), {col}, COUNT(*) FROM autos GROUP BY 1, 2"):
            y = yr or "none"
            d.setdefault(y, {})[val if val != "" else "(empty)"] = cnt
        nested[col] = d
    return scalar_years, nested


def label_pass(db: sqlite3.Connection, censor_cutoff: str, report: dict) -> dict:
    """Stream (entity, eff_ts) in order; next-event two-pointer labels; accumulate."""
    def new_year() -> dict:
        return {"n": 0, "pos": 0, "first_n": 0, "first_pos": 0, "rep_n": 0, "rep_pos": 0,
                "naive_n": 0, "naive_pos": 0, "censored": 0}

    def new_window() -> dict:
        return {"n": 0, "pos": 0, "first_pos": 0, "rep_pos": 0, "censored": 0,
                "ent_pos": set(), "acao_pos": set(), "month_pos": set(),
                "uf_pos": set(), "mun_pos": set(), "ent_all": set()}

    def bucket(year: int) -> str | None:
        for name, lo, hi in WINDOWS:
            if (lo is None or year >= lo) and (hi is None or year <= hi):
                return name
        return None

    years: dict[int, dict] = {}
    windows: dict[str, dict] = {name: new_window() for name, _, _ in WINDOWS}

    cur = db.execute("""
        SELECT entity, eff_ts, seq, seq_acao, uf, cod_mun
        FROM autos
        WHERE entity <> '' AND eff_ts IS NOT NULL
        ORDER BY entity, eff_ts
    """)
    entity = None
    group: list = []
    t0 = time.monotonic()

    def flush(group: list) -> None:
        if not group:
            return
        j = 0
        n = len(group)
        for i in range(n):
            _, eff, seq, acao, uf, mun = group[i]
            year = int(eff[:4])
            y = years.setdefault(year, new_year())
            if j < i + 1:
                j = i + 1
            while j < n and group[j][1] <= eff:
                j += 1
            label = 0
            if j < n and (ts_diff_days(group[j][1], eff) <= 365):
                label = 1
            y["naive_n"] += 1
            y["naive_pos"] += label
            censored = eff > censor_cutoff
            if censored:
                y["censored"] += 1
                continue
            first = (i == 0)
            y["n"] += 1
            y["pos"] += label
            if first:
                y["first_n"] += 1
                y["first_pos"] += label
            else:
                y["rep_n"] += 1
                y["rep_pos"] += label
            wname = bucket(year)
            if wname is None:
                continue
            w = windows[wname]
            w["n"] += 1
            w["pos"] += label
            w["ent_all"].add(group[i][0])
            if first:
                w["first_pos"] += label
            else:
                w["rep_pos"] += label
            if label:
                w["ent_pos"].add(group[i][0])
                if acao:
                    w["acao_pos"].add(acao)
                w["month_pos"].add(eff[:7])
                if uf:
                    w["uf_pos"].add(uf)
                if mun:
                    w["mun_pos"].add(mun)

    while True:
        row = cur.fetchone()
        if row is None:
            break
        ent, eff = row[0], row[1]
        if entity is not None and ent != entity:
            flush(group)
            group = []
        entity = ent
        group.append(row)
    flush(group)
    report["label_pass_seconds"] = round(time.monotonic() - t0, 1)
    for w in windows.values():
        for k in ("ent_pos", "acao_pos", "month_pos", "uf_pos", "mun_pos", "ent_all"):
            w[k] = len(w[k])
    return {"years": years, "windows": windows}


_TS_CACHE: dict[tuple[str, str], int] = {}


def ts_diff_days(later: str, earlier: str) -> int:
    """Day difference between two normalized 'YYYY-MM-DD HH:MM:SS' strings."""
    key = (later[:10], earlier[:10])
    d = _TS_CACHE.get(key)
    if d is None:
        a = datetime.strptime(later[:10], "%Y-%m-%d")
        b = datetime.strptime(earlier[:10], "%Y-%m-%d")
        d = (a - b).days
        if len(_TS_CACHE) < 1_000_000:
            _TS_CACHE[key] = d
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--work-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    work = Path(args.work_dir)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    report: dict = {"probe": "ibama-auto-infracao-recidivism aggregate probe",
                    "url": URL, "started_utc": datetime.utcnow().isoformat() + "Z"}
    t_start = time.monotonic()
    partial = out / "probe_error.json"
    try:
        zpath = download(work / "auto_infracao_csv.zip", report)
        db = sqlite3.connect(work / "probe.sqlite3")
        load_members(work, db, report)

        head = sql_scalar(db, "SELECT COUNT(*), SUM(n_occ), "
                              "SUM(CASE WHEN n_occ > 1 THEN 1 ELSE 0 END), "
                              "SUM(n_occ - 1), SUM(ent_mis), SUM(eff_mis), "
                              "SUM(sit_mis), SUM(des_mis) FROM autos") or ()
        report.update(dict(zip(
            ("rows_dedup", "rows_raw", "dup_seqs", "dup_extra_rows",
             "dup_entity_mismatch", "dup_date_mismatch", "dup_sit_mismatch",
             "dup_des_status_mismatch"), head)))

        build_eff(db, report)

        eff_head = sql_scalar(db, "SELECT COUNT(*), MIN(eff_ts), MAX(eff_ts) FROM autos "
                                  "WHERE eff_ts IS NOT NULL") or (0, None, None)
        eff_rows, eff_min, eff_max = eff_head
        report["rows_with_eff"] = eff_rows
        report["min_eff"] = eff_min
        report["max_eff"] = eff_max
        censor_days = 365
        cutoff_dt = datetime.strptime(eff_max[:10], "%Y-%m-%d") - timedelta(days=censor_days)
        censor_cutoff = cutoff_dt.strftime("%Y-%m-%d") + " 23:59:59"
        report["censor_cutoff_eff"] = censor_cutoff

        ent = one(db, """
            SELECT ent_kind, COUNT(*) FROM (
              SELECT CASE
                WHEN entity = '' THEN 'missing'
                WHEN length(replace(replace(replace(entity,'.',''),'/',''),'-','')) = 11
                     AND replace(replace(replace(entity,'.',''),'/',''),'-','') GLOB '[0-9]*'
                     AND entity GLOB '[0-9]*' THEN 'cpf'
                WHEN length(replace(replace(replace(entity,'.',''),'/',''),'-','')) = 14
                     AND replace(replace(replace(entity,'.',''),'/',''),'-','') GLOB '[0-9]*'
                     AND entity GLOB '[0-9]*' THEN 'cnpj'
                ELSE 'other' END AS ent_kind
              FROM autos) GROUP BY 1
        """)
        report["entity_kind_overall"] = ent
        punct = sql_scalar(db, "SELECT COUNT(*) FROM autos WHERE entity <> '' "
                               "AND (entity LIKE '%.%' OR entity LIKE '%-%' OR entity LIKE '%/%')") or (0,)
        report["entity_rows_with_punctuation"] = punct[0]
        stamps = one(db, "SELECT stamp, COUNT(*) FROM autos GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
        report["export_stamps_top10"] = stamps
        bins = one(db, """
            SELECT bin, COUNT(*) FROM (
              SELECT CASE WHEN c = 1 THEN '1' WHEN c = 2 THEN '2' WHEN c <= 5 THEN '3-5'
                          WHEN c <= 20 THEN '6-20' ELSE '21+' END AS bin
              FROM (SELECT entity, COUNT(*) AS c FROM autos
                    WHERE entity <> '' AND eff_ts IS NOT NULL GROUP BY entity)
            ) GROUP BY 1
        """)
        report["entities_by_auto_count_bin"] = bins
        report["distinct_entities_with_autos"] = sum(bins.values())
        acao = sql_scalar(db, "SELECT COUNT(DISTINCT seq_acao), "
                              "SUM(CASE WHEN seq_acao = '' THEN 1 ELSE 0 END) FROM autos") or (0, 0)
        report["distinct_seq_acao"] = acao[0]
        report["rows_without_seq_acao"] = acao[1]

        scalar_years, nested = per_year_sql(db)
        recent_cutoff = None
        if report["export_stamps_top10"]:
            top_stamp = next(iter(report["export_stamps_top10"]))
            if top_stamp and len(top_stamp) >= 10:
                recent_cutoff = (datetime.strptime(top_stamp[:10], "%Y-%m-%d")
                                 - timedelta(days=365)).strftime("%Y-%m-%d")
                report["recent_alt_cutoff"] = recent_cutoff
        if recent_cutoff:
            rec = one(db, f"""
                SELECT substr(eff_ts,1,4), SUM(CASE WHEN dt_ult_alt >= '{recent_cutoff}' THEN 1 ELSE 0 END)
                FROM autos WHERE eff_ts IS NOT NULL GROUP BY 1
            """)
            for y, c in rec.items():
                scalar_years.setdefault(y, {})["recent_alt_rows"] = c

        lab = label_pass(db, censor_cutoff, report)
        years = lab["years"]
        windows = lab["windows"]

        # naive + censored per-year merge into scalar_years
        for y, d in sorted(years.items()):
            row = scalar_years.setdefault(str(y), {})
            row.update({"scored_n": d["n"], "scored_pos": d["pos"],
                        "base_rate": round(d["pos"] / d["n"], 4) if d["n"] else None,
                        "first_n": d["first_n"], "first_pos": d["first_pos"],
                        "rep_n": d["rep_n"], "rep_pos": d["rep_pos"],
                        "naive_n": d["naive_n"], "naive_pos": d["naive_pos"],
                        "naive_base_rate": (round(d["naive_pos"] / d["naive_n"], 4)
                                            if d["naive_n"] else None),
                        "censored_n": d["censored"]})

        report["per_year"] = scalar_years
        report["per_year_nested_mixes"] = nested
        report["windows"] = windows

        summary = {
            "probe": "ibama-probe-001 aggregate probe (discovery-owned)",
            "zip_sha256": report.get("zip_sha256"),
            "zip_bytes": report.get("zip_bytes_downloaded"),
            "zip_last_modified": report.get("zip_last_modified"),
            "zip_members": report.get("zip_members"),
            "rows_raw": report.get("rows_raw"),
            "rows_dedup": report.get("rows_dedup"),
            "dup_extra_rows": report.get("dup_extra_rows"),
            "dup_mismatches": {k: report.get(k) for k in
                               ("dup_entity_mismatch", "dup_date_mismatch",
                                "dup_sit_mismatch", "dup_des_status_mismatch")},
            "min_eff": report.get("min_eff"), "max_eff": report.get("max_eff"),
            "censor_cutoff_eff": censor_cutoff,
            "entity_kind_overall": ent,
            "distinct_seq_acao": report.get("distinct_seq_acao"),
            "entities_by_auto_count_bin": bins,
            "windows": windows,
            "per_year_scored": {y: {"n": d.get("scored_n"), "pos": d.get("scored_pos"),
                                     "base_rate": d.get("base_rate")}
                                for y, d in sorted(scalar_years.items())},
            "export_stamps_top10": report.get("export_stamps_top10"),
            "elapsed_seconds": round(time.monotonic() - t_start, 1),
        }
        (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        (out / "probe_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

        with (out / "per_year.csv").open("w", encoding="utf-8", newline="") as f:
            wtr = csv.writer(f)
            wtr.writerow(["year", "rows", "valid_entity", "cpf11", "cnpj14", "nonstd_alpha",
                          "dat_hora_rows", "dt_lanc_only_rows", "dh_dl_both", "dh_dl_same_day",
                          "eff_null", "altered_rows", "recent_alt_rows", "tp_alt_rows",
                          "scored_n", "censored_n", "scored_pos", "base_rate",
                          "first_n", "first_pos", "rep_n", "rep_pos",
                          "naive_n", "naive_pos", "naive_base_rate"])
            for y in sorted(scalar_years, key=lambda s: (s == "none", s)):
                d = scalar_years[y]
                wtr.writerow([y] + [d.get(k) for k in (
                    "rows", "valid_entity", "cpf11", "cnpj14", "nonstd_alpha",
                    "dat_hora_rows", "dt_lanc_only_rows", "dh_dl_both", "dh_dl_same_day",
                    "eff_null", "altered_rows", "recent_alt_rows", "tp_alt_rows",
                    "scored_n", "censored_n", "scored_pos", "base_rate",
                    "first_n", "first_pos", "rep_n", "rep_pos",
                    "naive_n", "naive_pos", "naive_base_rate")])
        with (out / "windows.csv").open("w", encoding="utf-8", newline="") as f:
            wtr = csv.writer(f)
            wtr.writerow(["window", "scored_n", "scored_pos", "base_rate",
                          "first_pos", "repeat_pos", "censored_excluded",
                          "distinct_entities_pos", "distinct_seq_acao_pos",
                          "distinct_yearmonth_pos", "distinct_uf_pos",
                          "distinct_municipio_pos", "distinct_entities_all"])
            for name, _, _ in WINDOWS:
                d = windows[name]
                wtr.writerow([name, d["n"], d["pos"],
                              round(d["pos"] / d["n"], 4) if d["n"] else None,
                              d["first_pos"], d["rep_pos"], d["censored"],
                              d["ent_pos"], d["acao_pos"], d["month_pos"],
                              d["uf_pos"], d["mun_pos"], d["ent_all"]])
        with (out / "members.csv").open("w", encoding="utf-8", newline="") as f:
            wtr = csv.writer(f)
            wtr.writerow(["member", "uncompressed_bytes", "status", "raw_rows",
                          "bad_seq", "ragged"])
            for m in report.get("members", []):
                wtr.writerow([m.get("member"), m.get("uncompressed_bytes"), m.get("status"),
                              m.get("raw_rows"), m.get("bad_seq"), m.get("ragged")])
        print("probe complete; report keys:", sorted(report)[:12], "...")
        print("rows_dedup", report.get("rows_dedup"), "max_eff", report.get("max_eff"))
        db.close()
    except Exception as exc:  # structural failure: leave evidence, exit nonzero
        die(partial, "probe", exc)


if __name__ == "__main__":
    main()
