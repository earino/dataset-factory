#!/usr/bin/env python3
"""Reproduce the acnc-charity-ais-deadline-compliance discovery measurements.

Fetches the ACNC register CSV and the AIS year CSVs (2019-2024) from data.gov.au with
anonymous HTTPS GETs, then prints every discovery figure recorded in record.json:
per-year row counts and on-time/late shares, prior-filer absence transitions, the
per-charity eligibility-frame counts with the 90-day pre-deadline instant, and window
sums for the candidate split. Memory-light: each file is streamed and reduced to
per-ABN tuples; safe on a 2 GiB host. Bulk files go to a scratch directory and are not
meant to be committed.

Usage: python3 probe_ais_metrics.py [--scratch DIR] [--download]
Without --download it reuses files already in the scratch directory (no network).
"""
import argparse
import calendar
import collections
import csv
import datetime
import json
import os
import time
import urllib.request

REGISTER_URL = ('https://data.gov.au/data/dataset/b050b242-4487-4306-abf5-07ca073e5594/'
                'resource/8fb32972-24e9-4c95-885e-7140be51be8a/download/datadotgov_main.csv')
# AIS CSV resource URLs (reporting-period years with CSV; 2013-2018 are XLSX-only).
AIS_URLS = {
    '19': 'https://data.gov.au/data/dataset/34b35c52-8af0-4cc1-aa0b-2278f6416d09/resource/76006467-18f2-4094-a1cb-50544fd9b7b2/download/datadotgov_ais19.csv',
    '20': 'https://data.gov.au/data/dataset/28a94374-d516-4200-a6f8-c09e76f58cc5/resource/62c7b3d3-4358-4d57-b810-a36732d36e2d/download/datadotgov_ais20.csv',
    '21': 'https://data.gov.au/data/dataset/db8def1b-b3ba-4536-98eb-60c99e5495e5/resource/bbb19fa5-2f63-49cb-96b2-523e25828f27/download/datadotgov_ais21.csv',
    '22': 'https://data.gov.au/data/dataset/311c24f3-fc09-42e7-8362-f15a76334a75/resource/cfbcf6f1-7ce5-472f-bfd3-a478e67e0366/download/datadotgov_ais22.csv',
    '23': 'https://data.gov.au/data/dataset/ff6905d6-9d5d-4ef1-8478-72b833864fb7/resource/2b0fb746-57c5-4523-bb4c-74b7b78279d9/download/datadotgov_ais23.csv',
    '24': 'https://data.gov.au/data/dataset/276ec1bc-4971-461c-88bc-be9f3c99a0f8/resource/710630ea-1202-4bbb-95f7-3973a972ddf8/download/datadotgov_ais24.csv',
}
YEARS = sorted(AIS_URLS)          # ['19', ..., '24']
GROUP_MEMBERS_URL = ('https://data.gov.au/data/dataset/276ec1bc-4971-461c-88bc-be9f3c99a0f8/'
                     'resource/b3e3a122-67cb-46eb-a1ea-25137f53e734/download/datadotgov_ais24_group_members.xlsx')


def pdate(s):
    try:
        dd, mm, yy = s.split('/')
        return datetime.date(int(yy), int(mm), int(dd))
    except Exception:
        return None


def fetch(url, path):
    t0 = time.time()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=300) as r, open(path, 'wb') as f:
        n = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
    print(f'  {os.path.basename(path)}: {n} bytes in {time.time() - t0:.1f} s')
    return n


def slim(path):
    """Stream one AIS CSV -> {abn: (due, received, fin_report_to, name, size)}."""
    out = {}
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        rdr = csv.DictReader(f)
        cols = {h.strip().lower(): h for h in (rdr.fieldnames or [])}
        for r in rdr:
            abn = r.get(cols.get('abn', ''), '')
            if not abn:
                continue
            out[abn] = (pdate(r.get(cols.get('ais due date', ''), '')),
                        pdate(r.get(cols.get('date ais received', ''), '')),
                        pdate(r.get(cols.get('fin report to', ''), '')),
                        r.get(cols.get('charity name', ''), ''),
                        r.get(cols.get('charity size', ''), ''))
    return out


def due_offsets(path):
    """Modal (due date - period end) offset in months, keyed by period-end month."""
    per = collections.defaultdict(collections.Counter)
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        rdr = csv.DictReader(f)
        cols = {h.strip().lower(): h for h in (rdr.fieldnames or [])}
        for r in rdr:
            due = pdate(r.get(cols.get('ais due date', ''), ''))
            end = pdate(r.get(cols.get('fin report to', ''), ''))
            if due and end:
                per[end.month][(due.year - end.year) * 12 + (due.month - end.month)] += 1
    return {m: c.most_common(1)[0][0] for m, c in per.items()}


def derived_due(offsets, period_end):
    off = offsets.get(period_end.month)
    if off is None:
        return None
    m = period_end.month + off
    yy = period_end.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return datetime.date(yy, m, min(period_end.day, calendar.monthrange(yy, m)[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scratch', default='/opt/data/cache/scratch')
    ap.add_argument('--download', action='store_true', help='fetch files missing from scratch')
    args = ap.parse_args()
    os.makedirs(args.scratch, exist_ok=True)

    paths = {}
    if args.download:
        print('fetching (single anonymous HTTPS GET per file):')
        for name, url in [('acnc_main.csv', REGISTER_URL)] + [(f'acnc_ais{y}.csv', u) for y, u in AIS_URLS.items()]:
            p = os.path.join(args.scratch, name)
            if not os.path.exists(p):
                fetch(url, p)
            paths[os.path.basename(p)[8:10] if 'ais' in name else 'reg'] = p
    else:
        for y in YEARS:
            p = os.path.join(args.scratch, f'acnc_ais{y}.csv')
            if os.path.exists(p):
                paths[y] = p
        p = os.path.join(args.scratch, 'acnc_main.csv')
        if os.path.exists(p):
            paths['reg'] = p
    have = [y for y in YEARS if y in paths]
    print('AIS year files available:', have)

    # per-year rows and lateness
    per_year = {}
    for y in have:
        rows = on = late = und = 0
        with open(paths[y], newline='', encoding='utf-8', errors='replace') as f:
            rdr = csv.DictReader(f)
            cols = {h.strip().lower(): h for h in (rdr.fieldnames or [])}
            for r in rdr:
                rows += 1
                due = pdate(r.get(cols.get('ais due date', ''), ''))
                rc = pdate(r.get(cols.get('date ais received', ''), ''))
                if due is None or rc is None:
                    und += 1
                elif rc <= due:
                    on += 1
                else:
                    late += 1
        per_year[y] = (rows, on, late, und)
        print(f'20{y}: rows={rows} ontime={on} ({on / rows:.4f}) late={late} ({late / rows:.4f}) undated={und}')

    # prior-filer absence transitions
    abns = {y: set(slim(paths[y])) for y in have}
    print('prior-filer absence transitions:')
    for a, b in zip(have, have[1:]):
        only = len(abns[a] - abns[b])
        print(f'  20{a}->20{b}: prior={len(abns[a])} absent={only} ({only / len(abns[a]):.4f})')

    # eligibility-frame counts: eligible = prior received <= (target due - 90 days)
    targets = [y for y in have if y != have[0]]
    frame = {}
    for Y in targets:
        P = str(int(Y) - 1).zfill(2)
        if P not in paths:
            continue
        offsets = due_offsets(paths[Y])
        prior = slim(paths[P])
        cur = slim(paths[Y])
        eligible = pos_late = pos_never = neg = 0
        for abn, (p_due, p_recv, p_end, _, _) in prior.items():
            if p_recv is None or p_end is None:
                continue
            c_due, c_recv = cur[abn][0] if abn in cur else None, cur[abn][1] if abn in cur else None
            if c_due is not None:
                du = c_due
            else:
                try:
                    du = derived_due(offsets, datetime.date(p_end.year + 1, p_end.month, p_end.day))
                except ValueError:
                    du = None
            if du is None:
                continue
            if p_recv > du - datetime.timedelta(days=90):
                continue
            eligible += 1
            if c_recv is not None:
                if c_recv <= du:
                    neg += 1
                else:
                    pos_late += 1
            else:
                pos_never += 1
        frame[Y] = dict(eligible=eligible, neg=neg, pos_late=pos_late, pos_never=pos_never,
                        pos=pos_late + pos_never)
        print(f'target 20{Y}: eligible={eligible} ontime={neg} late_pos={pos_late} never_pos={pos_never} '
              f'pos_rate={(pos_late + pos_never) / max(1, eligible):.4f}')
    if {'20', '21'} <= set(frame):
        e = frame['20']['eligible'] + frame['21']['eligible']
        p = frame['20']['pos'] + frame['21']['pos']
        print(f'train 2020-2021: {e} rows / {p} positives ({p / e:.4f})')
    if {'22', '23'} <= set(frame):
        e = frame['22']['eligible'] + frame['23']['eligible']
        p = frame['22']['pos'] + frame['23']['pos']
        print(f'eval 2022-2023: {e} rows / {p} positives ({p / e:.4f})')
    if '24' in frame:
        print(f"holdout 2024: {frame['24']['eligible']} rows / {frame['24']['pos']} positives "
              f"({frame['24']['pos'] / frame['24']['eligible']:.4f})")

    # group members: unique 11-digit ABNs inside the shared strings of the xlsx
    if args.download:
        p = os.path.join(args.scratch, 'acnc_group_members_24.xlsx')
        if not os.path.exists(p):
            fetch(GROUP_MEMBERS_URL, p)
        import io
        import re
        import zipfile
        zf = zipfile.ZipFile(p)
        ss = zf.read('xl/sharedStrings.xml').decode('utf-8', errors='replace')
        gm = set(re.findall(r'>\s*(\d{11})\s*<', ss))
        print(f'group members 2024: {len(gm)} unique ABNs; overlap with ais24: '
              f'{len(gm & abns.get("24", set()))}; with ais23: {len(gm & abns.get("23", set()))}; '
              f'with ais19: {len(gm & abns.get("19", set()))}')

    # dated example verification
    if '23' in paths and '24' in paths:
        ex = slim(paths['23']).get('11000073870')
        ex24 = slim(paths['24']).get('11000073870')
        if ex and ex24:
            print('dated example ABN 11000073870 (Integricare Limited):')
            print(f'  2023: due={ex[0]} received={ex[1]} (on time: {ex[1] <= ex[0]})')
            print(f'  2024: due={ex24[0]} received={ex24[1]} -> label(1=fails by due)={int(not (ex24[1] <= ex24[0]))}')


if __name__ == '__main__':
    main()
