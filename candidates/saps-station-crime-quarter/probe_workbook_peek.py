#!/usr/bin/env python3
"""Peek inside the SAPS quarterly crime-stats XLSX: sheet names + sample strings."""
import re
import sys
import zipfile

path = sys.argv[1]
z = zipfile.ZipFile(path)
names = z.namelist()
print("zip entries:", len(names))
print("sheets:", [n for n in names if n.startswith("xl/worksheets/")][:8])
ss = None
for n in names:
    if n == "xl/sharedStrings.xml":
        ss = z.read(n).decode("utf-8", "replace")
        break
if ss:
    strings = re.findall(r"<t[^>]*>([^<]+)</t>", ss)
    print("shared strings:", len(strings))
    print("first 25:", strings[:25])
    # station-ish strings: those with a known province prefix or 'SAPS' in the name
    stations = [s for s in strings if "SAPS" in s][:10]
    print("sample station-like:", stations)
    cats = [s for s in strings if any(k in s.lower() for k in
            ("murder", "burglary", "theft", "assault", "robbery", "sexual"))][:12]
    print("sample category-like:", cats)
else:
    print("no sharedStrings.xml found")
