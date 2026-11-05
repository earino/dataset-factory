#!/usr/bin/env python3
"""Licence probe for ec-state-aid-investigation-opening (EU/EEA tick 2026-11-05).

Reads, anonymously:
1. the data.europa.eu dataset record (hub search API) - licence field + JSON
   distribution URL;
2. the competition-cases.ec.europa.eu landing page footer links (legal notice /
   reuse pages);
3. the candidate legal-notice / reuse pages found;
4. the S3 open-data bucket listing (is a manifest/licence file served beside
   the JSON dump?).

Outputs: bounded stdout + saved HTML/JSON under probe/out/ (licence probe only,
no case data fetched).
"""
import json
import os
import re
import subprocess

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch(url, path, headers=None, max_time=60):
    h = ["-H", f"User-Agent: {UA}"]
    if headers:
        for k, v in headers.items():
            h += ["-H", f"{k}: {v}"]
    r = subprocess.run(
        ["curl", "-sL", "--max-time", str(max_time), "-w",
         "\n%{http_code} %{size_download} %{url_effective}\n", url, *h, "-o", path],
        capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "no-writeout"
    return tail


def show(path, patterns, ctx=240):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print("  read error:", e)
        return
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            s = max(0, m.start() - ctx)
            e = min(len(text), m.end() + ctx)
            snippet = re.sub(r"\s+", " ", text[s:e])
            print("   ...", snippet[: 2 * ctx])
            break  # first hit per pattern is enough here


print("== 1. data.europa.eu hub record ==")
ds = "fa8d67be-d050-42a4-97ff-9e849805acf9~~1"
p = os.path.join(OUT, "portal_record.json")
print(" ", fetch(f"https://data.europa.eu/api/hub/search/datasets/{ds}", p))
try:
    d = json.load(open(p))
    rec = d.get("result", d)
    print("  title:", (rec.get("title") or {}).get("en"))
    print("  licence:", json.dumps(rec.get("licence"))[:400])
    print("  access_rights:", rec.get("access_rights"))
    dists = rec.get("distributions") or []
    print("  distributions:", len(dists))
    for i, dist in enumerate(dists):
        print(f"   [{i}] title:", json.dumps(dist.get("title"))[:120])
        print("        format:", json.dumps(dist.get("format"))[:200])
        print("        licence:", json.dumps(dist.get("licence"))[:300])
        print("        accessURL:", json.dumps(dist.get("access_url"))[:200])
        print("        downloadURL:", json.dumps(dist.get("download_url"))[:300])
        print("        size:", json.dumps(dist.get("byte_size"))[:120])
        print("        modified:", json.dumps(dist.get("modified"))[:160])
except Exception as e:
    print("  parse error:", e)

print()
print("== 2. competition-cases.ec.europa.eu landing page (footer links) ==")
p2 = os.path.join(OUT, "landing.html")
print(" ", fetch("https://competition-cases.ec.europa.eu/", p2))
links = sorted(set(re.findall(r'href="([^"]*(?:legal|licen[cs]e|reuse|copyright|terms)[^"]*)"',
                              open(p2, encoding="utf-8", errors="replace").read(), re.I)))
print("  candidate links:", links[:20])
show(p2, [r"licen[cs]e", r"reuse", r"copyright"], ctx=200)

print()
print("== 3. S3 bucket listing ==")
p3 = os.path.join(OUT, "s3_list.xml")
print(" ", fetch("https://compcases-open-data-portal-files-prod.s3.eu-west-1.amazonaws.com/?list-type=2", p3))
try:
    text = open(p3, encoding="utf-8", errors="replace").read()
    keys = re.findall(r"<Key>([^<]+)</Key>", text)
    sizes = re.findall(r"<Size>([^<]+)</Size>", text)
    print("  keys:", list(zip(keys, sizes))[:20])
except Exception as e:
    print("  parse error:", e)
