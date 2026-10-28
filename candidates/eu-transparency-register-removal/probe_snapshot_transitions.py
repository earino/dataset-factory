#!/usr/bin/env python3
"""Namespace-agnostic snapshot parse + transition measurement.

Old register (20141104 ns) exposes <status>; new register (odp ns) does not
(export carries only non-suspended entries). This probe records both.
Usage: tr_transitions2.py A.xml B.xml
"""
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone


def local(tag):
    return tag.rsplit("}", 1)[-1]


import re

_CTRL = re.compile(rb"&#(x[0-9A-Fa-f]+|[0-9]+);")
_KEEP = {9, 10, 13}


def _clean_line(ln):
    # drop character references to invalid XML 1.0 control chars (0-8,11,12,14-31)
    def repl(m):
        try:
            v = int(m.group(1)[1:], 16) if m.group(1)[:1] in (b"x", b"X") else int(m.group(1))
        except ValueError:
            return b""
        return m.group(0) if ((v >= 32 or v in _KEEP) and not (0xD800 <= v <= 0xDFFF) and v not in (0xFFFE, 0xFFFF)) else b""
    return _CTRL.sub(repl, ln)


def smart_open(path):
    with open(path, "rb") as f:
        for line in f:
            yield _clean_line(line)


def parse(path):
    orgs = {}
    export = None
    meta_n = None
    parser = ET.XMLPullParser(events=("end",))

    def handle(elem):
        nonlocal export, meta_n
        tag = local(elem.tag)
        if tag == "exportDate" and export is None:
            export = (elem.text or "").strip()
            elem.clear()
        elif tag == "numberOfIR":
            meta_n = (elem.text or "").strip()
            elem.clear()
        elif tag == "interestRepresentative":
            reg = None
            regdate = None
            lastupd = None
            status = None
            cat = None
            country = None
            for c in elem.iter():
                if c is elem:
                    continue
                t = local(c.tag)
                if t == "identificationCode" and reg is None:
                    reg = (c.text or "").strip()
                elif t == "status" and status is None:
                    status = (c.text or "").strip()
                elif t == "registrationDate":
                    regdate = (c.text or "").strip()
                elif t == "lastUpdateDate":
                    lastupd = (c.text or "").strip()
                elif t in ("registrationCategory", "mainCategory") and cat is None:
                    cat = (c.text or "").strip()
                elif t == "country" and country is None:
                    country = (c.text or "").strip()
            if reg:
                orgs[reg] = (regdate, lastupd, status, cat, country)
            elem.clear()

    for chunk in smart_open(path):
        parser.feed(chunk)
        for event, elem in parser.read_events():
            handle(elem)
    parser.close()
    return export, meta_n, orgs


def ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return None


def days(a, b):
    if a is None or b is None:
        return None
    return (a - b).days


export_a, na, A = parse(sys.argv[1])
export_b, nb, B = parse(sys.argv[2])
ea, eb = ts(export_a), ts(export_b)

st_a = Counter(v[2] for v in A.values())
st_b = Counter(v[2] for v in B.values())
print(f"A: export={export_a} declared={na} parsed={len(A)} statuses={dict(st_a)}")
print(f"B: export={export_b} declared={nb} parsed={len(B)} statuses={dict(st_b)}")
print(f"window days: {days(eb, ea)}")

both = set(A) & set(B)
only_a = set(A) - set(B)
only_b = set(B) - set(A)
print(f"both={len(both)}  A_only(disappeared)={len(only_a)}  B_only(appeared)={len(only_b)}")

# status transitions among orgs present in both (old era)
tr = Counter()
for reg in both:
    sa = A[reg][2] or "none"
    sb = B[reg][2] or "none"
    tr[(sa, sb)] += 1
if any(v[2] for v in A.values()):
    print("status transitions (both-present):")
    for k, v in tr.most_common(12):
        print(f"  {k}: {v}")

# disappearance by days-since-lastUpdate at A
buckets = Counter()
for reg in only_a:
    d = days(ea, ts(A[reg][1]))
    if d is None:
        buckets["no-lastupd"] += 1
    else:
        buckets[(d // 60) * 60] += 1
print("disappeared by days-since-lastUpdate at A (60d buckets):")
for k, v in sorted(buckets.items(), key=lambda kv: str(kv[0])):
    print(f"  {k}: {v}")

# appeared: new vs reactivation
new_reg = 0
react = 0
for reg in only_b:
    rd = ts(B[reg][0])
    if rd is None:
        continue
    if rd <= ea:
        react += 1
    else:
        new_reg += 1
print(f"appeared: new={new_reg}  reactivations={react}")

# survivors updated
upd = sum(1 for r in both if (days(ts(B[r][1]), ts(A[r][1])) or 0) > 0)
print(f"survivors with newer lastUpdate in B: {upd}/{len(both)}")
