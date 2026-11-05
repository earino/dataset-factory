#!/usr/bin/env python3
"""Probe: fetch (or read) one Traffic Commissioner 'Applications and Decisions' gazette
PDF and measure its structure: publication metadata and entry counts per section.

Discovery evidence for candidates/tc-gv-licence-application-outcome (2026-11-05).
Anonymous read-only fetch; one bounded file per run.

    python3 probe_gazette_sample.py <local.pdf | https://...pdf> [--out result.json]

Sections measured (AD gazette, goods vehicles):
  1.1 new applications, 1.2 variation applications,
  2.1 new granted, 2.2 new refused, 2.3 variation granted, 2.4 variation refused,
  4.1 withdrawn, 4.2 grants not taken up, 5.1 PI notices, 5.2 PI decisions,
  7.1 surrendered, 7.2 terminated.
Entries are counted as licence-reference tokens (e.g. OF2094843) at line starts.
"""

import argparse
import json
import re
import sys
import urllib.request

SECTION_MARKS = [
    "Section 1.1", "Section 1.2", "Section 2.1", "Section 2.2", "Section 2.3",
    "Section 2.4", "Section 4.1", "Section 4.2", "Section 5.1", "Section 5.2",
    "Section 7.1", "Section 7.2", "Section 8",
]


def load_pdf_bytes(source):
    if source.startswith("http"):
        req = urllib.request.Request(source, headers={"User-Agent": "urllib"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    with open(source, "rb") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out")
    args = ap.parse_args()

    from pypdf import PdfReader
    import io

    data = load_pdf_bytes(args.source)
    reader = PdfReader(io.BytesIO(data))
    full = "\n".join((p.extract_text() or "") for p in reader.pages)

    pub = re.findall(r"Publication Date:\s*([\d/]+)", full)
    num = re.findall(r"Publication Number:\s*(\d+)", full)
    deadline = re.findall(r"Objection Deadline Date:\s*([\d/]+)", full)

    positions = [(m, full.find(m)) for m in SECTION_MARKS if full.find(m) >= 0]
    positions.sort(key=lambda x: x[1])
    sections = {}
    for k, (mark, start) in enumerate(positions):
        end = positions[k + 1][1] if k + 1 < len(positions) else len(full)
        seg = full[start:end]
        # entry = reference token (2 letters + 7 digits) - first occurrence per segment line
        sections[mark] = len(re.findall(r"[A-Z]{2}\d{7}\b", seg))

    pi_grounds = re.findall(r"(S1[34]|S2[26])\s*-([^\n]+)", full)

    result = {
        "source": args.source,
        "bytes": len(data),
        "pages": len(reader.pages),
        "publication_date": pub[0] if pub else None,
        "publication_number": num[0] if num else None,
        "objection_deadline": deadline[0] if deadline else None,
        "entries_by_section": sections,
        "pi_ground_codes_sample": [{"code": c, "text": t.strip()} for c, t in pi_grounds[:10]],
    }
    print(json.dumps(result, indent=1))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(result, fh, indent=1)


if __name__ == "__main__":
    sys.exit(main())
