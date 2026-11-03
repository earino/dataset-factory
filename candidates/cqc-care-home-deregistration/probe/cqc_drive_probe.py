#!/usr/bin/env python3
"""Probe CQC Google Drive archive folders (embeddedfolderview, anonymous, no JS).

Answers: vintage depth (earliest dated file) and naming pattern for the three
CQC bulk-file archives linked from https://www.cqc.org.uk/about-us/transparency/using-cqc-data
"""
import re
import urllib.request

FOLDERS = {
    "care_directory (weekly csv)": "0B1jvn_rdpdEzMUtiNVoyeW9rb2M",
    "care_directory_with_filters (monthly ods)": "1Y6V6r-q2l4lJYKuZL0DXw25VDUTH6L4N",
    "care_directory_with_ratings (monthly ods)": "1N9JH4DhoKvb5SO6I9ObqRmhPgxD_m_pS",
}

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def fetch(folder_id):
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode("utf-8", "replace")

def names(html):
    # embeddedfolderview lists entries as <div class="flip-entry-title">NAME</div>
    return re.findall(r'flip-entry-title">([^<]+)</div>', html)

for label, fid in FOLDERS.items():
    try:
        status, html = fetch(fid)
        files = names(html)
        print(f"== {label} status={status} entries={len(files)}")
        for f in files[:5]:
            print("   first:", f)
        for f in files[-5:]:
            print("   last: ", f)
    except Exception as e:
        print(f"== {label} ERROR: {type(e).__name__}: {e}")
