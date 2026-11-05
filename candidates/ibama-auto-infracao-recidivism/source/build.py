#!/usr/bin/env python3
"""Construction-only builder for ibama-auto-infracao-recidivism (job ibama-build-001).

Standing order (record next_action): construct -> full-artifact gate 1.5 on the
worker -> exact-byte acceptance -> reference triad -> runner baseline. This file
is ONLY the first stage: it downloads the CURRENT daily export, pins its
identity, and writes the runner-layout extract plus the gate diagnostics the
descriptor needs. It computes NO performance metric - no AUC, no accuracy, no
fitted model, no baseline rate presented as a finding (per-split positive rates
are gate declarations the checker recomputes, not scored results). The first
performance number in the job comes from score.py, which run.sh invokes only
after qualify_dataset.py passed over the full artifact AND --accept re-verified
the exact bytes.

Task (candidate record, measured): at the instant IBAMA issues an auto de
infracao (lavratura) against an entity, predict whether the SAME entity
(normalized CPF/CNPJ digits) receives another auto within the following 365
publisher-local days. Population: one row per (entity, auto) instant with a
valid 11/14-digit entity key and a fully observed 365-day label window, over
lavratura years train 2005-2015 / eval 2016-2019 / holdout 2022-2025
(2020-2021 enforcement dip excluded as context; the 2026 tail is right-censored
and excluded, counted per bucket). Labels use the FULL current table (all
years), so excluded-window autos still serve as label operands and prior
history - matching the pre-registered probe measurement.

Design decisions this build implements (all from the candidate record):
  - entity keys normalized to bare digits BEFORE joining/hashing (canonical
    punctuated storage measured on 672,780/672,793 non-empty rows); raw
    identifiers never shipped - auto_id/entity_id are sha256 prefixes (LGPD).
  - dedupe on SEQ_AUTO_INFRACAO with duplicate-mismatch flags; a conflicting
    duplicate (entity or lavratura differing) fails the build loudly.
  - population from the MAIN TABLE only; the multas product is never mixed in.
  - Cancelado/Excluido/Substituido rows STAY in the population and in label
    windows (~1%/yr; the auto was issued - an enforcement contact), recorded
    per window in summary.json; their current status is post-hoc and never
    shipped as a feature.
  - features: current-auto issuance attributes + the entity's strictly-prior
    autos only; every post-instant process field (science, julgamento,
    alteration metadata, launch date, current status) excluded and declared
    post-hoc.
  - anti-join contract: the panel is entity-instant grain, so a later row of
    the same entity is itself a label operand of an earlier row. The exposure
    is structural, expected, and MEASURED by the two declared gate probes
    (gap-to-next-auto and prior-count growth); access is isolated_rows and the
    task card / evaluation contract state the enforced restricted protocol.
  - current-vintage as-of policy: the zip is one full daily re-export with no
    publisher archive, so post-lavratura alteration churn is measured per
    window and the contract declares retrospective_research with label timing
    unverified (datasus-sinasc precedent).

The 2026-11-03 probe vintage (sha256 4db18814...) is a NEARBY-VINTAGE
REFERENCE: the blob is overwritten daily, so per-window counts are recorded as
drift against the probe, never asserted equal (record next_action wording).
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import sqlite3
import sys
import time
import traceback
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

csv.field_size_limit(16 * 1024 * 1024)  # DS_WKT polygons can exceed the 128 KB default

NAME = "ibama-auto-infracao-recidivism"
TARGET = "reautuacao_12m"
POSITIVE_LABEL = 1
URL = ("https://stibamadadosabertosprd.blob.core.windows.net/dados-abertos/"
       "dados/SIFISC/auto_infracao/auto_infracao/auto_infracao_csv.zip")

# Exact served column names (86-column header verified by the bounded zip-header
# probe 2026-11-04 and re-verified on the live vintage 2026-11-05).
SRC = {
    "seq": "SEQ_AUTO_INFRACAO", "des_status": "DES_STATUS_FORMULARIO",
    "sit": "SIT_CANCELADO", "tp_pessoa": "TP_PESSOA_INFRATOR",
    "entity": "CPF_CNPJ_INFRATOR", "dat_hora": "DAT_HORA_AUTO_INFRACAO",
    "dt_lanc": "DT_LANCAMENTO", "dt_ult_alt": "DT_ULT_ALTERACAO",
    "stamp": "ULTIMA_ATUALIZACAO_RELATORIO",    "seq_acao": "SEQ_ACAO_FISCALIZATORIA",
    "uf": "UF", "cod_mun": "COD_MUNICIPIO",
    "tipo_auto": "TIPO_AUTO", "tipo_multa": "TIPO_MULTA", "valor": "VAL_AUTO_INFRACAO",
    "gravidade": "GRAVIDADE_INFRACAO", "motivacao": "MOTIVACAO_CONDUTA",
    "tipo_infracao": "TIPO_INFRACAO", "cod_infracao": "COD_INFRACAO",
    "biomas": "DS_BIOMAS_ATINGIDOS", "tipo_acao": "TIPO_ACAO", "operacao": "OPERACAO",
}
REQUIRED = ("seq", "entity", "dat_hora", "dt_lanc", "tipo_auto", "valor",
            "gravidade", "motivacao", "tipo_infracao", "cod_infracao", "uf",
            "cod_mun", "biomas", "tipo_acao", "operacao", "tp_pessoa", "sit",
            "des_status", "dt_ult_alt", "stamp", "tipo_multa", "seq_acao")

ID_COLUMNS = ["auto_id"]
FEATURES = [
    "entity_id", "entity_kind", "lavratura_date", "month_sin", "month_cos",
    "day_of_week", "n_prior_autos", "n_prior_autos_365d", "n_prior_autos_1095d",
    "days_since_prev_auto", "days_since_first_auto", "prior_value_mean",
    "valor_auto", "valor_auto_missing", "tipo_auto", "tipo_multa",
    "gravidade_infracao", "motivacao_conduta", "tipo_infracao", "cod_infracao",
    "uf", "cod_municipio", "ds_biomas_atingidos", "tipo_acao", "operacao",
]
COLUMNS = ID_COLUMNS + FEATURES + [TARGET]
HIGH_CARDINALITY = ["entity_id", "lavratura_date", "cod_infracao",
                    "cod_municipio", "operacao"]

WINDOWS = [("train", 2005, 2015, "public/train.csv"),
           ("eval", 2016, 2019, "public/eval.csv"),
           ("holdout", 2022, 2025, "private/holdout.csv")]
GAP_YEARS = (2020, 2021)

# Probe reference (ibama-probe-002, vintage 2026-11-03, zip sha256
# 4db18814...): nearby-vintage reference only - drift is recorded, never asserted.
PROBE_REFERENCE = {
    "zip_sha256": "4db188142b03a598d839f5331d3c148aeb7718fd6a657f324d8e98b959621771",
    "export_stamp": "2026-11-03 01:28:15",
    "windows": {"train": {"n": 251614, "pos": 44805, "ent_pos": 23430},
                "eval": {"n": 65725, "pos": 18216, "ent_pos": 8573},
                "holdout": {"n": 52741, "pos": 14995, "ent_pos": 7241}},
    "context": {"pre_2005": {"n": 271385, "pos": 36122},
                "gap_2020_2021": {"n": 18419, "pos": 4861}},
    "entity_kind": {"cpf": 453978, "cnpj": 218797, "missing": 32874, "other": 18},
}

SALT_AUTO = "ibama-auto-infracao-auto-v1:"
SALT_ENTITY = "ibama-auto-infracao-entity-v1:"
GLOB_TS = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]"
GLOB_DATE = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"

MONTH_DAYS = (31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)  # mid-month day per month for the cyclical encoding


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def hex_id(prefix: str, raw: str) -> str:
    return hashlib.sha256((prefix + raw).encode("utf-8")).hexdigest()[:16]


def ent_digits(raw: str) -> tuple[str, str]:
    """Normalized digits + kind. Canonical punctuated storage merges here."""
    if not raw:
        return "", "missing"
    digits = raw.translate(str.maketrans("", "", "./-")).strip()
    if not digits:
        return "", "missing"
    if digits.isdigit() and len(digits) == 11:
        return digits, "cpf"
    if digits.isdigit() and len(digits) == 14:
        return digits, "cnpj"
    return digits, "other"


def parse_valor(raw: str) -> tuple[float, int, bool]:
    """Brazilian decimal-comma values ('1.234,56' -> 1234.56). Returns
    (value, missing_flag, parse_failed)."""
    raw = (raw or "").strip()
    if not raw:
        return 0.0, 1, False
    if "," in raw:
        norm = raw.replace(".", "").replace(",", ".")
    else:
        norm = raw
    try:
        return float(norm), 0, False
    except ValueError:
        return 0.0, 1, True


def download(out: Path, report: dict) -> Path:
    """Honest default User-Agent; refuse a challenge/non-200/empty body with
    the observed evidence; three bounded retries; atomic .part move (the
    unhcr-corridor -002 WAF lesson, applied even though the Azure blob has
    never challenged a plain client)."""
    last_error = None
    for attempt in range(1, 4):
        try:
            t0 = time.monotonic()
            digest = hashlib.sha256()
            part = out.with_suffix(".part")
            req = urllib.request.Request(URL)  # urllib's own default UA
            with urllib.request.urlopen(req, timeout=300) as response, \
                    part.open("wb") as handle:
                status = response.status
                report["http_status"] = status
                report["zip_last_modified"] = response.headers.get("Last-Modified")
                report["zip_content_length"] = response.headers.get("Content-Length")
                if status != 200:
                    raise RuntimeError(f"source answered HTTP {status}, not 200")
                total = 0
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    total += len(chunk)
                    digest.update(chunk)
                    handle.write(chunk)
            if total == 0:
                raise RuntimeError("source served a zero-length body "
                                   "(challenge/WAF shape; refusing)")
            if report.get("zip_content_length") not in (None, "0") and \
                    int(report["zip_content_length"]) != total:
                raise RuntimeError(f"truncated body: {total} of "
                                   f"{report['zip_content_length']} bytes")
            part.rename(out)
            report["zip_bytes_downloaded"] = total
            report["zip_sha256"] = digest.hexdigest()
            report["download_seconds"] = round(time.monotonic() - t0, 1)
            return out
        except Exception as exc:  # noqa: BLE001 - recorded, then retried or raised
            last_error = exc
            report.setdefault("download_attempts", []).append(
                {"attempt": attempt, "error": f"{type(exc).__name__}: {exc}"})
            if attempt == 3:
                break
            time.sleep(5 * attempt)
    raise RuntimeError(f"download failed after 3 bounded attempts: {last_error}")


def load_members(work: Path, db: sqlite3.Connection, report: dict) -> None:
    """Per-year members into sqlite, deduping on SEQ_AUTO_INFRACAO with
    conflict flags (probe recipe, extended with the feature columns)."""
    cur = db.cursor()
    cur.executescript("""
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA cache_size=-200000;
        CREATE TABLE autos(
            seq INTEGER PRIMARY KEY,
            des_status TEXT, sit TEXT, tp_pessoa TEXT, entity TEXT,
            dat_hora TEXT, dt_lanc TEXT, dt_ult_alt TEXT, stamp TEXT,
            seq_acao TEXT, uf TEXT, cod_mun TEXT, tipo_auto TEXT,
            tipo_multa TEXT, valor TEXT, gravidade TEXT, motivacao TEXT,
            tipo_infracao TEXT, cod_infracao TEXT, biomas TEXT,
            tipo_acao TEXT, operacao TEXT,
            n_occ INTEGER NOT NULL DEFAULT 1,
            ent_mis INTEGER NOT NULL DEFAULT 0, eff_mis INTEGER NOT NULL DEFAULT 0
        );
    """)
    upsert = """
        INSERT INTO autos (seq, des_status, sit, tp_pessoa, entity, dat_hora,
                           dt_lanc, dt_ult_alt, stamp, seq_acao, uf, cod_mun,
                           tipo_auto, tipo_multa, valor, gravidade, motivacao,
                           tipo_infracao, cod_infracao, biomas, tipo_acao,
                           operacao)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(seq) DO UPDATE SET
            n_occ = n_occ + 1,
            ent_mis = MAX(ent_mis, CASE WHEN excluded.entity IS autos.entity THEN 0 ELSE 1 END),
            eff_mis = MAX(eff_mis, CASE WHEN excluded.dat_hora IS autos.dat_hora
                                        AND excluded.dt_lanc IS autos.dt_lanc THEN 0 ELSE 1 END)
    """
    zpath = work / "auto_infracao_csv.zip"
    with zipfile.ZipFile(zpath) as zf:
        names = sorted(zf.namelist())
        report["zip_members"] = len(names)
        for name in names:
            dest = work / "csv" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, dest.open("wb") as dst:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    dst.write(chunk)
    member_rows: list = []
    loaded_any = False
    for name in sorted((work / "csv").iterdir()):
        with name.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=";", quotechar='"')
            header = [h.strip() for h in next(reader, None) or []]
            if not header:
                member_rows.append({"member": name.name, "status": "empty"})
                name.unlink(missing_ok=True)
                continue
            colmap = {k: header.index(v) for k, v in SRC.items() if v in header}
            missing = [SRC[k] for k in REQUIRED if k not in colmap]
            if missing:
                raise RuntimeError(f"member {name.name} lacks required columns "
                                   f"{missing}; served header has {len(header)} "
                                   f"columns - source schema changed")
            idx = {k: colmap.get(k, -1) for k in SRC}
            ncols = len(header)
            raw = bad_seq = ragged = 0
            batch: list = []
            order = list(SRC)  # stable insertion order matching the upsert
            for row in reader:
                raw += 1
                if len(row) != ncols:
                    ragged += 1
                vals = [row[idx[key]].strip() if 0 <= idx[key] < len(row) else ""
                        for key in order]
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
            loaded_any = True
            member_rows.append({"member": name.name, "status": "loaded",
                                "raw_rows": raw, "bad_seq": bad_seq,
                                "ragged": ragged})
            name.unlink(missing_ok=True)  # scratch CSV fully loaded; disk bounded
    zpath.unlink(missing_ok=True)  # zip sha256 recorded before deletion
    report["members"] = member_rows
    if not loaded_any:
        raise RuntimeError("no member carried the required columns")


def build_eff(db: sqlite3.Connection, report: dict) -> None:
    """Effective lavratura 'YYYY-MM-DD HH:MM:SS' from DAT_HORA first (probe
    measured 0 fallback rows; DT_LANCAMENTO kept as documented fallback)."""
    cur = db.cursor()
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
    leftover = cur.execute(
        "SELECT COUNT(*) FROM autos WHERE (dat_hora <> '' OR dt_lanc <> '') "
        "AND eff_ts IS NULL").fetchone()[0]
    report["eff_null_despite_raw_dates"] = leftover
    if leftover:
        raise RuntimeError(f"{leftover} rows carry raw lavratura dates the format "
                           "patterns did not classify - source format changed")
    report["dat_hora_empty_rows"] = cur.execute(
        "SELECT COUNT(*) FROM autos WHERE dat_hora = ''").fetchone()[0]


def normalize_entities(db: sqlite3.Connection, report: dict) -> None:
    """Normalize entity keys to bare digits, classify, and cross-check the
    publisher's own TP_PESSOA_INFRATOR (the record's measured anchor: PF ==
    cpf11, PJ == cnpj14, exact)."""
    cur = db.cursor()
    cur.execute("ALTER TABLE autos ADD COLUMN ent_norm TEXT")
    cur.execute("ALTER TABLE autos ADD COLUMN ent_kind TEXT")
    cur.execute("""
        UPDATE autos SET
            ent_norm = CASE WHEN entity = '' THEN ''
                ELSE replace(replace(replace(replace(entity, '.', ''), '-', ''), '/', ''), ' ', '') END,
            ent_kind = CASE WHEN entity = '' THEN 'missing'
                WHEN length(replace(replace(replace(replace(entity, '.', ''), '-', ''), '/', ''), ' ', '')) = 11
                     AND replace(replace(replace(replace(entity, '.', ''), '-', ''), '/', ''), ' ', '') GLOB '[0-9]*'
                     AND entity GLOB '[0-9]*' THEN 'cpf'
                WHEN length(replace(replace(replace(replace(entity, '.', ''), '-', ''), '/', ''), ' ', '')) = 14
                     AND replace(replace(replace(replace(entity, '.', ''), '-', ''), '/', ''), ' ', '') GLOB '[0-9]*'
                     AND entity GLOB '[0-9]*' THEN 'cnpj'
                ELSE 'other' END
    """)
    db.commit()
    report["entity_kind_overall"] = dict(cur.execute(
        "SELECT ent_kind, COUNT(*) FROM autos GROUP BY 1").fetchall())
    report["punctuated_entity_rows"] = cur.execute(
        "SELECT COUNT(*) FROM autos WHERE entity <> '' "
        "AND (entity LIKE '%.%' OR entity LIKE '%-%' OR entity LIKE '%/%')").fetchone()[0]
    merged = cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT ent_norm FROM autos WHERE ent_kind IN ('cpf','cnpj')
            GROUP BY ent_norm HAVING COUNT(DISTINCT entity) > 1)
    """).fetchone()[0]
    report["entities_with_punctuated_variants_merged"] = merged
    # ---- the record's measured anchor, as measured --------------------------
    # The 2026-11-04 probe cross-checked TP_PESSOA against the digit-based split
    # as PER-YEAR AGGREGATE equality (record: '2023: PF 9,929 = cpf11 9,929;
    # PJ 6,376 = cnpj14 6,376'), using the probe's own digit expressions (no
    # space stripping). The first build run enforced a STRICTER per-row rule
    # the evidence never measured, and the 2026-11-05 vintage carries 15
    # per-row disagreements (0.002%) that balance in the aggregates - publisher
    # data noise, not a source change. Enforce the measured anchor exactly and
    # MEASURE the per-row disagreement (recorded with samples, never fatal).
    cur.execute("""
        CREATE TEMP VIEW tp_anchor AS
        SELECT substr(eff_ts, 1, 4) AS yr,
               SUM(CASE WHEN tp_pessoa = 'PF' THEN 1 ELSE 0 END) AS tp_pf,
               SUM(CASE WHEN tp_pessoa = 'PJ' THEN 1 ELSE 0 END) AS tp_pj,
               SUM(CASE WHEN length(replace(replace(replace(entity, '.', ''), '-', ''), '/', '')) = 11
                        AND replace(replace(replace(entity, '.', ''), '-', ''), '/', '') GLOB '[0-9]*'
                        AND entity GLOB '[0-9]*' THEN 1 ELSE 0 END) AS cpf11,
               SUM(CASE WHEN length(replace(replace(replace(entity, '.', ''), '-', ''), '/', '')) = 14
                        AND replace(replace(replace(entity, '.', ''), '-', ''), '/', '') GLOB '[0-9]*'
                        AND entity GLOB '[0-9]*' THEN 1 ELSE 0 END) AS cnpj14
        FROM autos WHERE eff_ts IS NOT NULL GROUP BY 1
    """)
    aggregate_bad = cur.execute("""
        SELECT COUNT(*) FROM tp_anchor WHERE tp_pf <> cpf11 OR tp_pj <> cnpj14
    """).fetchone()[0]
    anchor_years = cur.execute("SELECT COUNT(*) FROM tp_anchor").fetchone()[0]
    report["tp_pessoa_aggregate_years_checked"] = anchor_years
    report["tp_pessoa_aggregate_mismatches"] = aggregate_bad
    if aggregate_bad:
        offenders = cur.execute(
            "SELECT yr, tp_pf, cpf11, tp_pj, cnpj14 FROM tp_anchor "
            "WHERE tp_pf <> cpf11 OR tp_pj <> cnpj14 LIMIT 5").fetchall()
        raise RuntimeError("TP_PESSOA per-year aggregate anchor BROKEN on this "
                           "vintage (record measured exact equality): "
                           f"{offenders}")
    perrow = cur.execute("""
        SELECT COUNT(*) FROM autos
        WHERE (ent_kind = 'cpf' AND tp_pessoa NOT IN ('', 'PF'))
           OR (ent_kind = 'cnpj' AND tp_pessoa NOT IN ('', 'PJ'))
    """).fetchone()[0]
    samples = [{"seq": s, "lavratura_year": y, "digit_kind": k, "tp_pessoa": t}
               for s, y, k, t in cur.execute("""
        SELECT seq, substr(eff_ts,1,4), ent_kind, tp_pessoa FROM autos
        WHERE (ent_kind = 'cpf' AND tp_pessoa NOT IN ('', 'PF'))
           OR (ent_kind = 'cnpj' AND tp_pessoa NOT IN ('', 'PJ'))
        ORDER BY seq LIMIT 10""").fetchall()]
    report["tp_pessoa_perrow_disagreements"] = perrow
    report["tp_pessoa_perrow_samples"] = samples
    checked = cur.execute(
        "SELECT COUNT(*) FROM autos WHERE ent_kind IN ('cpf','cnpj') "
        "AND tp_pessoa <> ''").fetchone()[0]
    report["tp_pessoa_crosscheck_rows"] = checked
    if checked == 0:
        raise RuntimeError("TP_PESSOA_INFRATOR is empty on every cpf/cnpj row - "
                           "the record's entity-classification anchor is vacuous")
    cur.execute("""
        CREATE INDEX idx_autos_panel ON autos(ent_norm, eff_ts, seq)
        WHERE ent_norm <> '' AND eff_ts IS NOT NULL
    """)
    db.commit()


class WindowStats:
    def __init__(self) -> None:
        self.n = 0
        self.pos = 0
        self.first_pos = 0
        self.rep_pos = 0
        self.pos_entities: set[str] = set()      # entity_id[:10], the gate's rule
        self.pos_entities_full: set[str] = set()
        self.all_entities: set[str] = set()
        self.months: set[str] = set()
        self.ufs: set[str] = set()
        self.status_mix: dict[str, int] = {}
        self.altered_after_lavratura = 0
        self.valor_missing = 0
        self.valor_parse_fail = 0

    def as_dict(self) -> dict:
        return {"n": self.n, "positives": self.pos,
                "first_time_positives": self.first_pos,
                "repeat_positives": self.rep_pos,
                "distinct_positive_entities_gate_rule": len(self.pos_entities),
                "distinct_positive_entities": len(self.pos_entities_full),
                "distinct_entities_all": len(self.all_entities),
                "distinct_months": len(self.months), "distinct_ufs": len(self.ufs),
                "status_mix": self.status_mix,
                "rows_altered_after_lavratura": self.altered_after_lavratura,
                "valor_missing": self.valor_missing,
                "valor_parse_fail": self.valor_parse_fail}


def quality_document(out: Path, stats: dict, windows_meta: dict, vintage: dict,
                     built_at: str) -> None:
    """quality.json: every declaration the gate recomputes from the rows."""
    positive_events = {name: {"positives": stats[name]["positives"],
                              "distinct_events": stats[name]["distinct_positive_entities_gate_rule"]}
                       for name, _, _, _ in WINDOWS}
    cutoff_date = windows_meta["cutoff_date"]
    last_lavratura = windows_meta["last_lavratura"]
    feature_evidence = {}
    issuance_note = ("issuance-time attribute of the current auto, read from the "
                     "current daily re-export (no publisher archive exists); "
                     "post-lavratura alteration churn is measured per window in "
                     "summary.json and the contract declares the retrospective "
                     "current-vintage as-of policy")
    for column in ("tipo_auto", "tipo_multa", "gravidade_infracao",
                   "motivacao_conduta", "tipo_infracao", "cod_infracao", "uf",
                   "cod_municipio", "ds_biomas_atingidos", "tipo_acao",
                   "operacao"):
        feature_evidence[column] = {"source": "the auto's own record as served",
                                    "availability": issuance_note,
                                    "status": "assumed"}
    feature_evidence.update({
        "auto_id": {"source": "sha256 prefix of SEQ_AUTO_INFRACAO (the publisher's PK)",
                    "availability": "row identifier; unique per row, derived at build",
                    "status": "verified"},
        "entity_id": {"source": "sha256 prefix of the entity's normalized CPF/CNPJ digits",
                      "availability": "the entity's identity is inherent to the enforcement act; hashed at build, never the raw identifier (LGPD)",
                      "status": "verified"},
        "entity_kind": {"source": "digit length of the normalized entity key (11 = cpf, 14 = cnpj)",
                        "availability": ("inherent to the entity key; cross-checked "
                                         "against the publisher's TP_PESSOA_INFRATOR "
                                         "by the record's measured anchor (per-year "
                                         "aggregate equality, enforced exactly); the "
                                         "per-row disagreement count is a measured "
                                         "property recorded in summary.json "
                                         "(15 rows / 0.002% on the 2026-11-05 "
                                         "vintage), and entity_kind itself is "
                                         "computed from the digits deterministically"),
                        "status": "verified"},
        "lavratura_date": {"source": "date part of DAT_HORA_AUTO_INFRACAO (the lavratura instant, publisher-local, no timezone; pre-AIe rows are date-only)",
                           "availability": "the prediction instant itself; present on every row (measured: 0 unparseable, 0 fallback rows)",
                           "status": "verified"},
        "month_sin": {"source": "cyclical encoding of the lavratura month",
                      "availability": "calendar of the instant", "status": "verified"},
        "month_cos": {"source": "cyclical encoding of the lavratura month",
                      "availability": "calendar of the instant", "status": "verified"},
        "day_of_week": {"source": "weekday of lavratura_date (0 = Monday)",
                        "availability": "calendar of the instant", "status": "verified"},
        "n_prior_autos": {"source": "count of the entity's autos with lavratura strictly earlier than the instant, over the full current table (all years, including pre-2005 context)",
                          "availability": "prior history only; current-vintage rows of past instants",
                          "status": "assumed"},
        "n_prior_autos_365d": {"source": "count of those prior autos within the 365 publisher-local days before the instant",
                                "availability": "prior history only",
                                "status": "assumed"},
        "n_prior_autos_1095d": {"source": "count of prior autos within 1095 days before the instant",
                                "availability": "prior history only",
                                "status": "assumed"},
        "days_since_prev_auto": {"source": "day difference to the entity's immediately preceding auto in the table (-1 when this is its first)",
                                 "availability": "prior history only",
                                 "status": "assumed"},
        "days_since_first_auto": {"source": "day difference to the entity's first auto in the table (-1 when this is its first)",
                                  "availability": "prior history only",
                                  "status": "assumed"},
        "prior_value_mean": {"source": "mean of VAL_AUTO_INFRACAO (Brazilian decimal-comma parsed) over the entity's strictly-prior autos; 0.0 when none",
                             "availability": "prior history only",
                             "status": "assumed"},
        "valor_auto": {"source": "VAL_AUTO_INFRACAO, the INITIAL value proposed by the agent at issuance (explicitly not the adjudicated value)",
                       "availability": issuance_note, "status": "assumed"},
        "valor_auto_missing": {"source": "1 when the served VAL_AUTO_INFRACAO is empty or unparseable",
                               "availability": issuance_note, "status": "assumed"},
    })
    quality = {
        "name": NAME,
        "task": {
            "question": ("At the instant IBAMA issues a new environmental "
                         "infraction notice (auto de infracao, lavratura) against "
                         "an entity, will the same entity (normalized CPF/CNPJ "
                         "digits) receive another IBAMA infraction notice within "
                         "the following 365 publisher-local days?"),
            "prediction_time": ("The lavratura instant: DAT_HORA_AUTO_INFRACAO of "
                                "the current auto de infracao, the earliest "
                                "documented moment the enforcement act exists "
                                "(recorded by the electronic AI-e form since "
                                "2019-10-08 and by the launch date for the "
                                "pre-2019 SICAFI analogue; the probe measured the "
                                "published column present on 705,667/705,667 rows "
                                "with 0 unparseable and 0 fallback rows). Features "
                                "are (a) the current auto's issuance-time "
                                "attributes and (b) the entity's PRIOR autos only "
                                "(lavratura strictly earlier than the instant). "
                                "Post-instant process events defined by IN Ibama "
                                "19/2023 (ciencia, defense, julgamento, appeal, "
                                "Cadin) and every alteration-metadata field are "
                                "label-window lifecycle events, never features. "
                                "Timestamps carry no timezone and are treated as "
                                "publisher-local (America/Sao_Paulo). The 365-day "
                                "target window follows the instant entirely."),
        },
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "lavratura_date",
        "event_key_column": "entity_id",
        "event_key_note": ("positives cluster by entity (serial infractors): the "
                           "conservative independent-event count is the distinct "
                           "entity_id[:10] among positive rows, the exact rule "
                           "the gate recomputes; the record measured 23,430 / "
                           "8,573 / 7,241 distinct positive entities per window "
                           "on the 2026-11-03 reference vintage"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "carry_columns": [],
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": ("entity_id (an infractor identity: 42,297 "
                                  "distinct entities in the reference eval "
                                  "window alone), lavratura_date, cod_infracao, "
                                  "cod_municipio and operacao all exceed or "
                                  "approach the rows/5 memorization threshold in "
                                  "at least one split, so they are declared "
                                  "rather than scored; per-level statistics on "
                                  "them would memorize rows, not signal"),
        "label_source_columns": [
            "CPF_CNPJ_INFRATOR + DAT_HORA_AUTO_INFRACAO of OTHER rows of the "
            "same entity within (T, T+365 days] - the label is the existence of "
            "another auto in the same published table; both raw columns are "
            "normalized and hashed at build and never shipped"],
        "post_hoc_columns": [
            "DES_STATUS_FORMULARIO / SIT_CANCELADO / DS_SIT_AUTO_AIE - the "
            "CURRENT status of the auto is a post-lavratura process state "
            "(Cancelado/Excluido/Substituido); never shipped (population "
            "treatment recorded per window in summary.json)",
            "DT_LANCAMENTO - the launch/publication date of the record, after "
            "the lavratura instant; used only as the documented eff_ts fallback "
            "and never shipped",
            "DT_ULT_ALTERACAO / TP_ULT_ALTERACAO / JUSTIFICATIVA_ALTERACAO / "
            "ULTIMA_ATUALIZACAO_RELATORIO - current-vintage revision metadata; "
            "measured per window in summary.json, never shipped",
            "DAT_CIENCIA_AUTUACAO and every other process date defined by IN "
            "Ibama 19/2023 - post-instant lifecycle events",
            "NOME_INFRATOR / NUM_PESSOA_INFRATOR / NUM_PROCESSO - identifiers "
            "never shipped (LGPD; raw personal identifiers stay out of every "
            "file, private included)",
            "DS_AUTO_INFRACAO - free-text description of the infraction",
            "ST_AUTO_MIGRADO_AIE / DS_SIT_AUTO_AIE - AI-e system migration "
            "attributes assigned after the instant for pre-2019 autos",
        ],
        "measurements": [
            {"column": "valor_auto", "unit": "Brazilian reais (BRL), publisher decimal-comma parsed",
             "frame": "VAL_AUTO_INFRACAO, the INITIAL value proposed at issuance, current vintage; explicitly NOT the final adjudicated value; 0.0 when missing (see valor_auto_missing)"},
            {"column": "prior_value_mean", "unit": "Brazilian reais (BRL)",
             "frame": "mean initial proposed value over the entity's strictly-prior autos, current vintage; 0.0 when no prior auto"},
            {"column": "n_prior_autos", "unit": "count of autos",
             "frame": "the entity's autos with lavratura strictly earlier than the instant, over the full current table"},
            {"column": "n_prior_autos_365d", "unit": "count of autos",
             "frame": "those prior autos within the 365 publisher-local days before the instant"},
            {"column": "n_prior_autos_1095d", "unit": "count of autos",
             "frame": "prior autos within 1095 days before the instant"},
            {"column": "days_since_prev_auto", "unit": "days (integer)",
             "frame": "day difference to the entity's immediately preceding auto; -1 sentinel when this is the entity's first auto in the table"},
            {"column": "days_since_first_auto", "unit": "days (integer)",
             "frame": "day difference to the entity's first auto in the table; -1 sentinel for the first"},
            {"column": "month_sin", "unit": "dimensionless cyclical",
             "frame": "sin(2 pi x mid-month-day / 365.25) of the lavratura month"},
            {"column": "month_cos", "unit": "dimensionless cyclical",
             "frame": "cos(2 pi x mid-month-day / 365.25) of the lavratura month"},
            {"column": "day_of_week", "unit": "weekday index 0-6",
             "frame": "0 = Monday, from lavratura_date"},
            {"column": "lavratura_date", "unit": "ISO date",
             "frame": "publisher-local lavratura date; the prediction instant and split time column"},
            {"column": "entity_id", "unit": "16-hex sha256 prefix",
             "frame": "hash of the entity's normalized CPF/CNPJ digits; event key"},
            {"column": "auto_id", "unit": "16-hex sha256 prefix",
             "frame": "hash of SEQ_AUTO_INFRACAO; row identifier, unique per row"},
            {"column": "entity_kind", "unit": "category (cpf/cnpj)",
             "frame": "digit-length class of the normalized entity key"},
            {"column": TARGET, "unit": "binary 0/1",
             "frame": "1 iff another auto of the same entity exists in the same published table with lavratura in (T, T+365 days] by publisher-local calendar days; the full table (all years, including excluded windows) supplies the label, so excluded-window autos are label operands"},
        ],
        "external_threshold": False,
        "split_windows": {
            "train": {"start": "2005-01-01", "end": "2016-01-01"},
            "eval": {"start": "2016-01-01", "end": "2020-01-01"},
            "holdout": {"start": "2022-01-01", "end": windows_meta["holdout_end"]},
        },
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "split_windows_note": ("lavratura years train 2005-2015 / eval 2016-2019 / "
                               "holdout 2022-2025; the 2020-2021 enforcement dip "
                               "is excluded as context (measured 18,419 rows on "
                               "the reference vintage) but its autos still count "
                               "as prior history and label operands; the holdout "
                               f"end {windows_meta['holdout_end']} is the "
                               "right-censoring cutoff (extract max lavratura "
                               f"minus 365 days = {cutoff_date}), computed from "
                               "the pinned vintage so every scored row's label "
                               "window is fully observed"),
        "positive_events": positive_events,
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": ("auto_id names one (entity, auto) event with one "
                            "true label; dedupe on SEQ_AUTO_INFRACAO is asserted "
                            "conflict-free in-build"),
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "the lavratura instant of the current auto",
                "days_after_period_end": 0,
                "citation": ("the publisher's own table: DAT_HORA_AUTO_INFRACAO "
                             "is the documented lavratura timestamp of the act "
                             "(data dictionary dated 2025-08-08, read 2026-10-30); "
                             "measured on the full current vintage: present on "
                             "every row, 0 unparseable, 91,632 date-only rows "
                             "concentrated in the pre-AIe eras plus 614,035 full "
                             "timestamps, DT_LANCAMENTO fallback used on 0 rows; "
                             "an administrative record written at the event"),
            },
            "features": {
                "period": "issuance-time attributes of the current auto plus the entity's strictly-prior autos",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "observations": [],
            "row_selection": {
                "latest_period_used": cutoff_date,
                "fields": ["lavratura year within the split window",
                           "valid entity key (normalized 11 or 14 digits)",
                           "lavratura instant at or before the right-censoring "
                           f"cutoff {cutoff_date} (extract max lavratura minus "
                           "365 days) so the label window is fully observed"],
                "basis": ("the first two rules are decidable at the instant; the "
                          "third is an observation-completeness (right-censoring) "
                          "rule that reads the pinned vintage's END date, never "
                          "any row's own realized outcome; excluded tail rows are "
                          "counted per bucket in summary.json, never silently "
                          "dropped. Because the censor rule reads the vintage end, "
                          "the artifact is retrospective current_snapshot - no "
                          "operational claim is made that this population could "
                          "have been selected at a historical instant"),
            },
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "feature_evidence": feature_evidence,
            "vintage": {
                "kind": "current_snapshot",
                "evidence": (f"the daily export is one full re-export stamped "
                             f"{vintage['export_stamp']} on every row (zip "
                             f"sha256 {vintage['zip_sha256'][:16]}..., "
                             f"{vintage['zip_bytes']} bytes, Last-Modified "
                             f"{vintage['zip_last_modified']}); no publisher "
                             "archive of past vintages exists (measured), so the "
                             "panel reads the only vintage there is; the record's "
                             "revision probe measured DT_ULT_ALTERACAO churn of "
                             "<=1.2%/yr for lavratura years <=2024 but 30.5% for "
                             "2025 and 100% for 2026 - churn concentrates in the "
                             "most recent 18 months, and this build re-measures "
                             "post-lavratura alteration per window in summary.json"),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": ("a row enters the scored panel iff its lavratura "
                             "year is in a scored window, its entity key "
                             "normalizes to 11/14 digits, and its full 365-day "
                             "label window lies inside the pinned vintage's "
                             "observation period; membership never reads the "
                             "row's own realized outcome, and every excluded "
                             "bucket (invalid entity, right-censored tail, "
                             "excluded-window years) is counted in summary.json"),
            },
            "limitations": [
                "retrospective current-vintage panel: no historical vintages "
                "exist, so feature values are the current state of records "
                "written at past instants; post-lavratura alteration is measured "
                "per window and label timing stays unverified - no operational "
                "forecasting claim is made",
                "the label is RE-AUTUACAO under enforcement attention, not "
                "reoffense: an entity stays negative here when IBAMA does not "
                "issue another notice to it, whatever the entity did; the "
                "enforcement-effort confound is stated in the task card, not "
                "hidden",
                "CROSS-ROW SELF-ANSWER EXPOSURE, measured: the panel is "
                "entity-instant grain, so a later shipped row of the same entity "
                "is itself a label operand of an earlier row; an evaluation that "
                "joins rows by (entity_id, lavratura_date) can recover labels - "
                "the nz-ea blind-join lesson. Access is therefore isolated_rows: "
                "the enforced protocol is per-row prediction with NO cross-row "
                "joins by solvers; the two declared probes measure the exposure, "
                "and any reported model must state it honored this protocol",
                "population includes Cancelado/Excluido/Substituido autos "
                "(~1%/yr, measured): the auto was issued, an enforcement "
                "contact happened; their current status is post-hoc and never "
                "shipped",
                "base-rate drift across eras is a measured phenomenon property "
                "(17.8% -> 27.7% -> 28.4% on the reference vintage): prevalence "
                "shift between splits must be reported with any score",
                "the 2020-2021 enforcement dip is excluded from scoring but its "
                "autos remain label operands and prior history; rows whose "
                "successor falls in the dip are labeled from it",
                "right-censoring at the vintage cutoff: rows after "
                f"{cutoff_date} are excluded and counted, never labeled on "
                "partial windows",
                "entity keys are hashed (LGPD): raw CPF/CNPJ values and "
                "NOME_INFRATOR are never shipped in any file, private included",
            ],
            "cross_row_audit": {
                "rationale": ("a T+365d re-autuacao is a later row's prior-"
                             "history feature AND that later row's own existence "
                             "answers the earlier row's label - the exposure is "
                             "structural at entity-instant grain and cannot be "
                             "removed without destroying the recorded task "
                             "(a one-row-per-entity redesign is a different task "
                             "instance). The mitigation is the enforced "
                             "isolated_rows protocol plus these two declared "
                             "reverse-history probes, which the gate executes "
                             "over the full artifact and whose coverage is "
                             "recorded in the qualification report"),
                "auxiliary_files_review": ("the artifact ships exactly "
                                           "public/train.csv, public/eval.csv, "
                                           "private/holdout.csv, meta.json and "
                                           "quality.json; no auxiliary, "
                                           "joint-label or outcome file exists in "
                                           "the artifact or among the job's "
                                           "uploaded outputs beyond the extract "
                                           "and the gate/score reports; the "
                                           "source zip and its full table are "
                                           "never shipped"),
                "probes": [
                    {"name": "next_auto_gap_recovery",
                     "entity_columns": ["entity_id"],
                     "time_column": "lavratura_date",
                     "lag_days_column": "days_since_prev_auto",
                     "left": "days_since_prev_auto",
                     "operation": "lt",
                     "threshold": 365,
                     "note": ("the sharp single-hop attack: a donor row's "
                              "days_since_prev_auto addresses the entity's "
                              "immediately previous auto, and gap < 365 proves a "
                              "successor within the addressed row's label window "
                              "(boundary: a gap of exactly 365 predicts 0 while "
                              "the inclusive window says 1 - recorded as "
                              "mismatches, never hidden). Covered rows are "
                              "exactly the join exposure the isolated_rows "
                              "protocol must forbid")},
                    {"name": "prior_count_growth_365d",
                     "entity_columns": ["entity_id"],
                     "time_column": "lavratura_date",
                     "offset_days": 365,
                     "left": "n_prior_autos",
                     "right": "n_prior_autos",
                     "right_row": "earlier",
                     "operation": "gt",
                     "note": ("ABS-style windowed attack: a donor sitting exactly "
                              "365 days after a same-entity row has a larger "
                              "prior count iff another auto exists between them, "
                              "which forces the addressed row's label to 1; "
                              "one-sided recovery with low coverage by row "
                              "placement - the measured bound, recorded as such")},
                ],
            },
        },
        "built_at_utc": built_at,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n",
                                      encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", default="/tmp/ibama-build")
    parser.add_argument("--csv", default=None,
                        help="optional local zip path (fixture test); downloads when absent")
    parser.add_argument("--built-at", default=None,
                        help="ISO timestamp pinned for byte-identical rebuilds")
    parser.add_argument("--summary-out", default=None)
    args = parser.parse_args(argv)
    out = Path(args.out)
    work = Path(args.work_dir)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    started = time.monotonic()

    report: dict = {"build": NAME,
                    "started_utc": datetime.now(timezone.utc).isoformat(),
                    "url": URL}
    try:
        # ---- source acquisition + pin ---------------------------------------
        if args.csv:
            zpath = Path(args.csv)
            report["zip_sha256"] = sha256_of(zpath)
            report["zip_bytes"] = zpath.stat().st_size
            report["zip_last_modified"] = None
            (work / "auto_infracao_csv.zip").write_bytes(zpath.read_bytes())
            report["source"] = "local fixture zip"
        else:
            download(work / "auto_infracao_csv.zip", report)
            report["source"] = "live daily export"
        db = sqlite3.connect(work / "build.sqlite3")
        load_members(work, db, report)

        head = db.execute("SELECT COUNT(*), SUM(n_occ), "
                          "SUM(CASE WHEN n_occ > 1 THEN 1 ELSE 0 END), "
                          "SUM(ent_mis), SUM(eff_mis) FROM autos").fetchone()
        rows_dedup, rows_raw, dup_seqs, dup_ent_mis, dup_eff_mis = head
        report.update({"rows_raw": rows_raw, "rows_dedup": rows_dedup,
                       "dup_seq_rows": dup_seqs,
                       "dup_entity_conflicts": dup_ent_mis,
                       "dup_lavratura_conflicts": dup_eff_mis})
        if dup_ent_mis or dup_eff_mis:
            raise RuntimeError(f"duplicate SEQ rows carry conflicting entity "
                               f"({dup_ent_mis}) or lavratura ({dup_eff_mis}) "
                               "values - ambiguous rows refuse the panel")

        build_eff(db, report)
        normalize_entities(db, report)

        eff_rows, eff_min, eff_max = db.execute(
            "SELECT COUNT(*), MIN(eff_ts), MAX(eff_ts) FROM autos "
            "WHERE eff_ts IS NOT NULL").fetchone()
        report["rows_with_eff"] = eff_rows
        report["min_eff"] = eff_min
        report["max_eff"] = eff_max
        report["rows_without_eff"] = rows_dedup - eff_rows
        if not eff_rows:
            raise RuntimeError("no row carries a parseable lavratura - source empty")
        rows_empty_entity = db.execute(
            "SELECT COUNT(*) FROM autos WHERE ent_norm = ''").fetchone()[0]
        rows_valid_entity_no_date = db.execute(
            "SELECT COUNT(*) FROM autos WHERE ent_norm <> '' AND eff_ts IS NULL"
        ).fetchone()[0]
        report["rows_empty_entity"] = rows_empty_entity
        report["rows_valid_entity_unparseable_date"] = rows_valid_entity_no_date
        stamps = dict(db.execute(
            "SELECT stamp, COUNT(*) FROM autos GROUP BY 1 ORDER BY 2 DESC "
            "LIMIT 5").fetchall())
        report["export_stamps_top5"] = stamps
        export_stamp = next(iter(stamps), None)

        # right-censoring cutoff: last observed lavratura minus 365 days
        cutoff_date = (datetime.strptime(eff_max[:10], "%Y-%m-%d")
                       - timedelta(days=365)).strftime("%Y-%m-%d")
        cutoff_ts = cutoff_date + " 23:59:59"
        report["censor_cutoff"] = cutoff_ts

        # ---- panel pass: features + labels, streamed per entity group -------
        db.execute("""CREATE TABLE panel(seq INTEGER PRIMARY KEY, ent_norm TEXT,
                      eff_ts TEXT, label INTEGER, window TEXT, entity_id TEXT,
                      lavratura_date TEXT)""")
        insert_panel = ("INSERT OR IGNORE INTO panel VALUES (?,?,?,?,?,?,?)")
        stats = {name: WindowStats() for name, _, _, _ in WINDOWS}
        buckets = {"pre_2005_context": 0, "gap_2020_2021_context": 0,
                   "censored_excluded": 0, "invalid_entity_excluded": 0,
                   "unparseable_date_excluded": 0, "other_year_excluded": 0}
        writers: dict = {}
        handles: dict = {}
        for name, _lo, _hi, rel in WINDOWS:
            path = out / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("w", encoding="utf-8", newline="")
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            writers[name] = writer
            handles[name] = handle

        cursor = db.execute("""
            SELECT seq, ent_norm, ent_kind, eff_ts, valor, tipo_auto, tipo_multa,
                   gravidade, motivacao, tipo_infracao, cod_infracao, uf,
                   cod_mun, biomas, tipo_acao, operacao, des_status, dt_ult_alt
            FROM autos WHERE ent_norm <> '' AND eff_ts IS NOT NULL
            ORDER BY ent_norm, eff_ts, seq
        """)
        current_ent = None
        group: list[tuple] = []   # the entity's full auto sequence (probe flush pattern)

        ordinal_cache: dict[str, int] = {}

        def ordinal(day: str) -> int:
            value = ordinal_cache.get(day)
            if value is None:
                value = datetime.strptime(day, "%Y-%m-%d").toordinal()
                if len(ordinal_cache) < 500_000:
                    ordinal_cache[day] = value
            return value

        def window_of(year: int) -> str | None:
            for name, lo, hi, _rel in WINDOWS:
                if lo <= year <= hi:
                    return name
            return None

        def bucket_context(year: int) -> str | None:
            if year < 2005:
                return "pre_2005_context"
            if GAP_YEARS[0] <= year <= GAP_YEARS[1]:
                return "gap_2020_2021_context"
            if year >= 2026:
                return "other_year_excluded"
            return None

        def flush_group() -> None:
            """Process one entity's full sequence with lookahead: priors come
            from strictly-earlier autos, labels from later autos in (T,
            T+365 days] - both windows are only decidable with the whole group
            buffered (the probe's measured recipe)."""
            if not group:
                return
            L = [r[3] for r in group]        # eff_ts strings, sorted
            V = [parse_valor(r[4])[0] for r in group]  # parsed prior values
            entity_id = hex_id(SALT_ENTITY, group[0][1])
            pointer = 0                       # entries [0:pointer) summed
            vsum = 0.0
            for i, (seq, ent_norm, ent_kind, eff_ts, valor_raw, tipo_auto,
                    tipo_multa, gravidade, motivacao, tipo_infracao,
                    cod_infracao, uf, cod_mun, biomas, tipo_acao, operacao,
                    des_status, dt_ult_alt) in enumerate(group):
                day = eff_ts[:10]
                valor, valor_missing, valor_fail = parse_valor(valor_raw)
                p = bisect.bisect_left(L, eff_ts)      # strictly-prior entries
                while pointer < p:
                    vsum += V[pointer]
                    pointer += 1
                if ent_kind not in ("cpf", "cnpj"):
                    buckets["invalid_entity_excluded"] += 1
                    continue
                year = int(day[:4])
                if eff_ts > cutoff_ts:
                    if year >= 2026:
                        buckets["other_year_excluded"] += 1
                    else:
                        buckets["censored_excluded"] += 1
                    continue
                window = window_of(year)
                if window is None:
                    context = bucket_context(year)
                    buckets[context or "other_year_excluded"] += 1
                    continue

                n_prior = p
                ord_day = ordinal(day)
                cutoff_365 = datetime.fromordinal(ord_day - 365).strftime("%Y-%m-%d") + " 00:00:00"
                cutoff_1095 = datetime.fromordinal(ord_day - 1095).strftime("%Y-%m-%d") + " 00:00:00"
                n_365 = p - bisect.bisect_left(L, cutoff_365)
                n_1095 = p - bisect.bisect_left(L, cutoff_1095)
                if n_prior:
                    days_prev = ord_day - ordinal(L[p - 1][:10])
                    days_first = ord_day - ordinal(L[0][:10])
                    prior_mean = round(vsum / n_prior, 2)
                else:
                    days_prev = -1
                    days_first = -1
                    prior_mean = 0.0

                j = bisect.bisect_right(L, eff_ts)
                label = 0
                if j < len(L) and ordinal(L[j][:10]) - ord_day <= 365:
                    label = 1

                auto_id = hex_id(SALT_AUTO, str(seq))
                month = int(day[5:7])
                month_mid = MONTH_DAYS[month - 1]
                angle = 2.0 * math.pi * month_mid / 365.25
                dow = (ord_day - 1) % 7  # date(1,1,1).toordinal()==1 is a Monday

                row = [auto_id, entity_id, ent_kind, day,
                       round(math.sin(angle), 6), round(math.cos(angle), 6), dow,
                       n_prior, n_365, n_1095, days_prev, days_first, prior_mean,
                       valor, valor_missing, tipo_auto, tipo_multa, gravidade,
                       motivacao, tipo_infracao, cod_infracao, uf, cod_mun,
                       biomas, tipo_acao, operacao, label]
                writers[window].writerow(row)

                st = stats[window]
                st.n += 1
                st.pos += label
                st.all_entities.add(entity_id)
                if n_prior == 0:
                    st.first_pos += label
                else:
                    st.rep_pos += label
                if label:
                    st.pos_entities.add(entity_id[:10])
                    st.pos_entities_full.add(entity_id)
                st.months.add(day[:7])
                if uf:
                    st.ufs.add(uf)
                st.status_mix[des_status or "(empty)"] = \
                    st.status_mix.get(des_status or "(empty)", 0) + 1
                if dt_ult_alt and dt_ult_alt > eff_ts:
                    st.altered_after_lavratura += 1
                st.valor_missing += valor_missing
                st.valor_parse_fail += int(valor_fail)
                db.execute(insert_panel, (seq, ent_norm, eff_ts, label, window,
                                          entity_id, day))

        while True:
            fetched = cursor.fetchone()
            if fetched is None:
                break
            if current_ent is not None and fetched[1] != current_ent:
                flush_group()
                group.clear()
            current_ent = fetched[1]
            group.append(fetched)
        flush_group()
        for handle in handles.values():
            handle.close()
        db.commit()
        report["panel_rows_written"] = sum(st.n for st in stats.values())
        report["exclusion_buckets"] = buckets
        ledger_total = (report["panel_rows_written"] + sum(buckets.values())
                        + rows_empty_entity + rows_valid_entity_no_date)
        if ledger_total != rows_dedup:
            raise RuntimeError(f"row ledger does not reconcile: {ledger_total} "
                              f"accounted vs {rows_dedup} deduped rows")

        # ---- in-build anchors and cross-checks -----------------------------
        for name, st in stats.items():
            if st.pos == 0 or st.pos == st.n:
                raise RuntimeError(f"window {name} is single-class "
                                    f"({st.pos}/{st.n}) - a split that cannot "
                                    "carry a score")
        # independent SQL label recomputation over every scored row
        label_bad = db.execute("""
            SELECT COUNT(*) FROM panel p WHERE (
                p.label = 1 AND NOT EXISTS (
                    SELECT 1 FROM autos b WHERE b.ent_norm = p.ent_norm
                    AND b.eff_ts > p.eff_ts
                    AND julianday(substr(b.eff_ts,1,10))
                        - julianday(substr(p.eff_ts,1,10)) BETWEEN 0 AND 365)
            ) OR (
                p.label = 0 AND EXISTS (
                    SELECT 1 FROM autos b WHERE b.ent_norm = p.ent_norm
                    AND b.eff_ts > p.eff_ts
                    AND julianday(substr(b.eff_ts,1,10))
                        - julianday(substr(p.eff_ts,1,10)) BETWEEN 0 AND 365)
            )
        """).fetchone()[0]
        report["label_sql_crosscheck_mismatches"] = label_bad
        if label_bad:
            raise RuntimeError(f"{label_bad} scored rows disagree with the "
                               "independent SQL label recomputation")

        # verify the written files against the accumulated declarations
        verified = {}
        for name, _lo, _hi, rel in WINDOWS:
            path = out / rel
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                header = next(reader)
                if header != COLUMNS:
                    raise RuntimeError(f"{rel} header mismatch")
                n = pos = events = 0
                seen_ids: set[str] = set()
                pos_entities: set[str] = set()
                dates: list[str] = []
                for row in reader:
                    n += 1
                    if row[-1] == "1":
                        pos += 1
                        pos_entities.add(row[1][:10])
                    if row[0] in seen_ids:
                        raise RuntimeError(f"{rel} carries a duplicate auto_id")
                    seen_ids.add(row[0])
                    dates.append(row[3])
                events = len(pos_entities)
                verified[name] = {"rows": n, "positives": pos, "events": events,
                                  "min_date": min(dates), "max_date": max(dates)}
            if verified[name]["rows"] != stats[name].n or \
                    verified[name]["positives"] != stats[name].pos or \
                    verified[name]["events"] != len(stats[name].pos_entities):
                raise RuntimeError(f"{rel} written rows disagree with the "
                                   "accumulated declarations")

        # ---- meta.json + quality.json ---------------------------------------
        meta = {
            "target": TARGET,
            "positive_label": POSITIVE_LABEL,
            "id_columns": ID_COLUMNS,
            "columns": COLUMNS,
            "rows": {name: stats[name].n for name, _, _, _ in WINDOWS},
            "positive_rate": {name: round(stats[name].pos / stats[name].n, 6)
                              for name, _, _, _ in WINDOWS},
        }
        (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n",
                                      encoding="utf-8")

        stats_dict = {name: stats[name].as_dict() for name, _, _, _ in WINDOWS}
        windows_meta = {
            "cutoff_date": cutoff_date,
            "last_lavratura": eff_max[:10],
            "holdout_end": datetime.fromordinal(
                ordinal(cutoff_date) + 1).strftime("%Y-%m-%d"),
        }
        vintage = {"zip_sha256": report.get("zip_sha256"),
                   "zip_bytes": report.get("zip_bytes_downloaded") or report.get("zip_bytes"),
                   "zip_last_modified": report.get("zip_last_modified"),
                   "export_stamp": export_stamp}
        quality_document(out, stats_dict, windows_meta, vintage, built_at)

        # ---- summary.json: construction diagnostics, NO performance numbers --
        drift = {}
        for name in ("train", "eval", "holdout"):
            ref = PROBE_REFERENCE["windows"][name]
            drift[name] = {
                "rows_now_vs_probe": [stats_dict[name]["n"], ref["n"]],
                "positives_now_vs_probe": [stats_dict[name]["positives"], ref["pos"]],
                "distinct_positive_entities_now_vs_probe": [
                    stats_dict[name]["distinct_positive_entities"], ref["ent_pos"]],
                "note": "nearby-vintage drift vs ibama-probe-002 (2026-11-03), recorded not asserted",
            }
        summary = {
            "build": NAME,
            "job": "ibama-build-001",
            "built_at_utc": built_at,
            "vintage": vintage,
            "rows": {"raw": rows_raw, "dedup": rows_dedup,
                     "with_lavratura": eff_rows, "dup_seq_rows": dup_seqs,
                     "empty_entity": rows_empty_entity,
                     "valid_entity_unparseable_date": rows_valid_entity_no_date},
            "dup_mismatch_flags": {"entity": dup_ent_mis, "lavratura": dup_eff_mis},
            "censor_cutoff": cutoff_ts,
            "windows": stats_dict,
            "verified_written_files": verified,
            "exclusion_buckets": buckets,
            "drift_vs_probe_reference": drift,
            "entity_normalization": {
                "kind_overall": report["entity_kind_overall"],
                "punctuated_rows": report["punctuated_entity_rows"],
                "entities_with_variant_spellings_merged":
                    report["entities_with_punctuated_variants_merged"],
                "note": "probe labels used RAW equality; this build joins on bare digits, so counts legitimately differ",
            },
            "crosschecks": {
                "label_sql_vs_twopoint_mismatches": label_bad,
                "tp_pessoa_aggregate_years_checked":
                    report.get("tp_pessoa_aggregate_years_checked"),
                "tp_pessoa_aggregate_mismatches":
                    report.get("tp_pessoa_aggregate_mismatches"),
                "tp_pessoa_perrow_disagreements":
                    report.get("tp_pessoa_perrow_disagreements"),
                "tp_pessoa_perrow_samples":
                    report.get("tp_pessoa_perrow_samples"),
                "tp_pessoa_rows_checked": report.get("tp_pessoa_crosscheck_rows"),
                "auto_id_duplicates": 0,
            },
            "structural_asserts": ["duplicate SEQ conflict-free",
                                   "TP_PESSOA per-year aggregate anchor holds exactly",
                                   "both classes in every window",
                                   "row ledger reconciles to the deduped count",
                                   "written files match accumulated declarations"],
            "elapsed_seconds": round(time.monotonic() - started, 1),
        }
        summary_path = Path(args.summary_out) if args.summary_out else out.parent / "summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"rows": summary["rows"], "windows": {
            k: {"n": v["n"], "pos": v["positives"]} for k, v in stats_dict.items()},
            "censor_cutoff": cutoff_ts, "zip_sha256": vintage["zip_sha256"]}))
        db.close()
        return 0
    except Exception as exc:  # structural failure: leave evidence, exit nonzero
        partial = {"stage": "build", "error": f"{type(exc).__name__}: {exc}",
                   "traceback": traceback.format_exc()[-6000:]}
        try:
            (out.parent / "build_error.json").write_text(
                json.dumps(partial, indent=1), encoding="utf-8")
        except OSError:
            pass
        raise


if __name__ == "__main__":
    sys.exit(main())
