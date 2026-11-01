#!/usr/bin/env python3
"""Bounded byte-range sample of DG COMP case-data-SA.json (704 MB) on S3.

Extracts, from each 2 MB range: case keys, notification dates, member states,
aid categories, simplified-procedure flags, last-decision dates, and all
decisionTypes values seen (the Article 108(2) label source).
Ranged GET only - the full file never transits this host.
"""
import json
import re
import subprocess
import sys

URL = ("https://compcases-open-data-portal-files-prod.s3.eu-west-1.amazonaws.com/"
       "case-data-SA.json")
TOTAL = 703863715  # measured Content-Length 2026-10-30


def fetch_range(start, end, path):
    subprocess.run(
        ["curl", "-s", "--max-time", "120", "-r", f"{start}-{end}", URL, "-o", path],
        check=True,
    )
    return path


def probe(path, label):
    text = open(path, encoding="utf-8", errors="replace").read()
    keys = re.findall(r'"(SA\.\d+)"\s*:\s*\{', text)
    notif = re.findall(r'"caseNotificationDate"\s*:\s*\[\s*"(\d{4}-\d{2}-\d{2})"', text)
    lastdec = re.findall(r'"caseLastDecisionDate"\s*:\s*\[\s*"(\d{4}-\d{2}-\d{2})"', text)
    ms = re.findall(r'"caseMemberState"\s*:\s*\[\s*"(\{[^"]+\})"', text)
    cat = re.findall(r'"caseAidCategory"\s*:\s*\[\s*"(\{[^"]+\})"', text)
    simp = re.findall(r'"caseSimplifiedProcedure"\s*:\s*\[\s*"(\w+)"', text)
    dts = re.findall(r'"decisionTypes"\s*:\s*\[\s*(.*?)\]', text)
    dt_values = []
    for d in dts:
        for m in re.findall(r'\\?"label\\?":\\?"([^"\\]+)', d):
            dt_values.append(m)
    ms_lab = {}
    for m in ms:
        try:
            ms_lab[json.loads(m)["label"]] = ms_lab.get(json.loads(m)["label"], 0) + 1
        except Exception:
            pass
    cat_lab = {}
    for m in cat:
        try:
            cat_lab[json.loads(m)["label"]] = cat_lab.get(json.loads(m)["label"], 0) + 1
        except Exception:
            pass
    print(f"===== {label} ({len(text)} bytes sampled) =====")
    print("case keys:", len(keys), "first:", keys[:3], "last:", keys[-3:] if keys else [])
    print("notif dates:", len(notif), "min:", min(notif) if notif else None,
          "max:", max(notif) if notif else None)
    if lastdec:
        print("lastDecisionDate present in", len(lastdec), "case blocks")
    print("memberStates:", dict(sorted(ms_lab.items(), key=lambda x: -x[1])[:8]))
    print("aidCategories:", dict(sorted(cat_lab.items(), key=lambda x: -x[1])))
    print("simplifiedProcedure values:", {v: simp.count(v) for v in set(simp)})
    from collections import Counter
    print("decisionTypes labels (top):", Counter(dt_values).most_common(15))
    print("empty decisionTypes arrays:", sum(1 for d in dts if d.strip() == ""))
    print()
    return keys


if __name__ == "__main__":
    ranges = [
        (0, 2000000, "sa_head.json", "HEAD 0-2MB"),
        (TOTAL // 2, TOTAL // 2 + 2000000, "sa_mid.json", "MIDDLE ~351MB"),
        (TOTAL - 2000001, TOTAL - 1, "sa_tail.json", "TAIL last 2MB"),
    ]
    for start, end, path, label in ranges:
        fetch_range(start, end, path)
        probe(path, label)
