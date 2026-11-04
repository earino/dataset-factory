#!/usr/bin/env python3
# Cross-check baseline from the publisher's own "Multas Ambientais Distribuidas por
# Bens Tutelados" product: per-UF per-auto multa listings. Counts rows per Data Auto
# year across all 27 UF files. Writes multas_per_year.json beside the zip.
# Ran 2026-11-04 from the coordinator on the 24,655,019-byte csv zip
# (Last-Modified 2026-11-03T09:07:10Z, sha256 recorded in the output).
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

SCRATCH = Path("/opt/data/cache/scratch")
OUT = Path("/opt/data/dataset-factory/candidates/ibama-auto-infracao-recidivism/probe/out")
OUT.mkdir(parents=True, exist_ok=True)
zpath = SCRATCH / "multas_bens_tutelados_csv.zip"

sha = hashlib.sha256(zpath.read_bytes()).hexdigest()
years = Counter()
tipo_auto = Counter()
no_date = 0
total = 0
with zipfile.ZipFile(zpath) as z:
    members = z.namelist()
    for m in members:
        with z.open(m) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig"),
                                delimiter=";", quotechar='"')
            header = next(reader, None)
            if not header or "Data Auto" not in header:
                continue
            di = header.index("Data Auto")
            ti = header.index("Tipo Auto") if "Tipo Auto" in header else -1
            for row in reader:
                total += 1
                d = row[di].strip() if di < len(row) else ""
                if len(d) >= 10 and d[-4:].isdigit():
                    years[d[-4:]] += 1
                else:
                    no_date += 1
                if ti >= 0 and ti < len(row):
                    tipo_auto[row[ti].strip()] += 1

result = {
    "source": "multas_ambientais_distribuidas_por_bens_tutelados_csv.zip",
    "url": ("https://stibamadadosabertosprd.blob.core.windows.net/dados-abertos/dados/"
            "MULTAS_AMBIENTAIS_DISTRIBUIDAS_POR_BENS_TUTELADOS/"
            "multas_ambientais_distribuidas_por_bens_tutelados_csv.zip"),
    "zip_bytes": zpath.stat().st_size,
    "zip_sha256": sha,
    "members": len(members),
    "rows_total": total,
    "rows_without_parseable_date": no_date,
    "tipo_auto_mix": dict(tipo_auto.most_common()),
    "rows_per_data_auto_year": dict(sorted(years.items())),
}
(OUT / "multas_per_year.json").write_text(json.dumps(result, indent=1))
print(json.dumps({k: v for k, v in result.items() if k != "rows_per_data_auto_year"}, indent=1))
print("per-year:", result["rows_per_data_auto_year"])
