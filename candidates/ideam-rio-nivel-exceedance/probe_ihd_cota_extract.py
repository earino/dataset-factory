#!/usr/bin/env python3
"""Extract official per-station flood thresholds (COTA CRITICA) from an archived
IDEAM IHD (Informe Hidrologico) PDF - the threshold source discovered 2026-10-23.

Current BAH/ITD/BCH bulletins (checked Oct 2026) carry zone-level alerts only; the
per-station cotas live in the historical IHD chart annotations. This script fetches a
Wayback-archived IHD and prints station / cota pairs. See notes.md sections 5-6.

Usage: python3 probe_ihd_cota_extract.py [wayback_url]
Default URL = the IHD dated 01 Oct 2016 used in the discovery session (Wayback capture 2024-08-05; capture date is not publication).
"""
import re
import sys
import urllib.request

from pypdf import PdfReader

DEFAULT = ("http://web.archive.org/web/20240805031921id_/http://www.ideam.gov.co/"
           "documents/78690/558885/10_IHD_Octubre_01_Dia.pdf/"
           "8f72fd41-6a54-4c5a-aef3-50df09ae4f2b")
url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
req = urllib.request.Request(url, headers={"User-Agent": "research-probe/1.0"})
data = urllib.request.urlopen(req, timeout=150).read()
path = "/tmp/ihd_probe.pdf"
open(path, "wb").write(data)
reader = PdfReader(path)
n = 0
for pi, page in enumerate(reader.pages):
    text = page.extract_text() or ""
    upper = text.upper()
    if "COTA" not in upper:
        continue
    for match in re.finditer(
        r"COTA\s*CR[IÍ]TICA\s*(?:REAL\s*)?([0-9]+(?:[.,][0-9]+)?)\s*M", upper
    ):
        preceding = text[max(0, match.start() - 300):match.start()]
        station = re.search(
            r"ESTACION\s*:?\s*([A-ZÁÉÍÓÚÑ0-9 .\-]+?)\s*-?\s*RIO", preceding.upper()
        )
        n += 1
        print(f"page {pi}: station="
              f"{station.group(1).strip() if station else '?'} cota={match.group(1)}")
print(f"total cota values: {n}")
