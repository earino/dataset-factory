#!/usr/bin/env python3
"""Reproduce the discovery measurements for anm-sigbm-emergency-transition.

Reads (downloads to scratch if absent) the ANM SIGBM open registry snapshot
and prints the schema/value-mix/identity-resolution measurements recorded in
candidates/anm-sigbm-emergency-transition/notes.md (probe date 2026-11-07).

Access caveats (measured, see notes.md #2):
  - the server omits its TLS intermediate: pass the Sectigo OV R36 AIA
    intermediate via --cacert, or the download fails with
    'unable to get local issuer certificate';
  - the WAF returns HTTP 403 for a default curl/python UA; a full Chrome UA
    is accepted.

Usage:
  python3 probe_registry_mix.py --all        # schema + mixes + identity probe
  python3 probe_registry_mix.py --identity  # identity probe only
"""

import argparse
import csv
import hashlib
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

URL = "https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv"
# Digest of the snapshot measured 2026-11-07T00:04Z and re-verified identical at
# 00:12Z. The registry updates daily ("Atualizacao: Diaria"): a mismatch below
# means a newer snapshot - re-measure and record the new digest, never ship a
# stale assumption.
SHA256 = "6aa5f152db495348d9e22abbc0bcdc4cba17fc6f4070772b279f445b18ee574a"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Outubro 2026 bulletin, Tabela 4 (dams with emergency status changed during
# the month) + one dam from each of Tabelas 5-8 (state lists as of 01/11/2026).
TRANSITIONS = [
    ("7a", "MG", "NOVA LIMA"),
    ("Bacia de Acumulação 01", "SC", "URUSSANGA"),
    ("Barragem B1A", "MG", "BRUMADINHO"),
    ("Barragem B5", "PA", "ITAITUBA"),
    ("BARRAGEM DE REJEITOS PGDM", "GO", "PILAR DE GOIÁS"),
    ("BARRAGEM02", "GO", "CAVALCANTE"),
    ("Bom Retiro 2", "SP", "LEME"),
    ("MBR II SUL", "SP", "IBIÚNA"),
    ("PDE02", "PA", "PARAUAPEBAS"),
    ("Portal", "MG", "ITABIRA"),
    ("Sul Inferior", "MG", "BARÃO DE COCAIS"),
]
LIST_DAMS = [
    ("Barragem Serra Azul", "MG", "ITATIAIÇU"),
    ("Belíssima", "RO", "ARIQUEMES"),
    ("Barragem CBC", "RS", "CAÇAPAVA DO SUL"),
    ("km 190", "AP", "SERRA DO NAVIO"),
]


def fetch(path: Path) -> None:
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == SHA256:
        return
    chain = path.with_suffix(".chain.pem")
    if not chain.is_file():
        crt = subprocess.run(
            ["curl", "-s", "--max-time", "60",
             "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"],
            capture_output=True, check=True).stdout
        pem = subprocess.run(
            ["openssl", "x509", "-inform", "DER", "-outform", "PEM"],
            input=crt, capture_output=True, check=True).stdout
        chain.write_bytes(pem)
    subprocess.run(
        ["curl", "-s", "--cacert", str(chain), "--max-time", "300", "-A", UA,
         "-H", "Accept: text/csv,*/*;q=0.8",
         "-H", "Accept-Language: pt-BR,pt;q=0.9,en;q=0.8",
         "-o", str(path), URL],
        check=True)
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != SHA256:
        sys.exit(f"sha256 mismatch: {got} != {SHA256} (snapshot changed; re-measure)")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--identity", action="store_true")
    args = ap.parse_args()
    if not (args.all or args.identity):
        ap.error("give --all or --identity")

    path = Path("/opt/data/cache/scratch/Barragens.csv")
    fetch(path)
    rows = list(csv.reader(open(path, encoding="latin-1")))
    hdr, data = rows[0], [r for r in rows[1:] if r[0].strip()]
    print(f"rows (dams): {len(data)}  columns: {len(hdr)}")

    def col(name):
        return hdr.index(name)

    if args.all:
        for name in ["Nível de Emergência", "Categoria de Risco - CRI",
                     "Dano Potencial Associado - DPA",
                     "Método construtivo da barragem", "Situação Operacional",
                     "Inserido na PNSB", "Necessita de PAEBM", "UF"]:
            print(f"--- {name}")
            for v, n in Counter(r[col(name)] for r in data).most_common(10):
                print(f"    {n:4d}  {v[:70]}")
        print("--- crosstab level x PNSB (all 77 Alerta/Emergencia dams are PNSB=Sim):")
        for k, v in sorted(Counter(
                (r[col("Nível de Emergência")][:16], r[col("Inserido na PNSB")])
                for r in data).items(), key=lambda x: -x[1])[:8]:
            print("   ", k, v)

    reg = {}
    for r in data:
        key = (norm(r[col("Nome")]), norm(r[col("UF")]), norm(r[col("Município")]))
        reg.setdefault(key, []).append(r)
    unique = ambiguous = missing = 0
    print("--- identity probe: bulletin rows -> registry (Nome, UF, Município)")
    for n, u, m in TRANSITIONS + LIST_DAMS:
        hits = reg.get((norm(n), norm(u), norm(m)), [])
        if len(hits) == 1:
            unique += 1
            print(f"OK   {n[:32]:32s} -> ID {hits[0][0]}")
        elif len(hits) > 1:
            ambiguous += 1
            print(f"AMB  {n[:32]:32s} -> {len(hits)} candidates")
        else:
            missing += 1
            print(f"MISS {n[:32]:32s} ({u}, {m})")
    total = len(TRANSITIONS) + len(LIST_DAMS)
    print(f"identity: unique {unique}, ambiguous {ambiguous}, "
          f"name-variant/missing {missing} of {total}")


if __name__ == "__main__":
    main()
