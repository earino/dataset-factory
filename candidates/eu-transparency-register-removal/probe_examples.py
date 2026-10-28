#!/usr/bin/env python3
"""Worked dated examples for the transparency-register record.

Picks, from snapshot A, two orgs and prints their observable fields:
 - one that disappears from snapshot B (removed: annual update missed);
 - one that survives with a lastUpdate shortly after A.
Prints identificationCode, name, category, country, registrationDate,
lastUpdateDate in A (and in B for the survivor).
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

NS_A = "{http://intragate.ec.europa.eu/transparencyregister/odp}"
NS_B = "{http://intragate.ec.europa.eu/transparencyregister/intws/20141104}"


def local(tag):
    return tag.rsplit("}", 1)[-1]


def parse(path):
    orgs = {}
    export = None
    for event, elem in ET.iterparse(path, events=("end",)):
        tag = local(elem.tag)
        if tag == "exportDate" and export is None:
            export = (elem.text or "").strip()
            elem.clear()
        elif tag == "interestRepresentative":
            d = {"reg": None, "name": None, "cat": None, "country": None,
                 "regdate": None, "lastupd": None, "epa": None, "membersFTE": None}
            for c in elem.iter():
                if c is elem:
                    continue
                t = local(c.tag)
                if t == "identificationCode" and d["reg"] is None:
                    d["reg"] = (c.text or "").strip()
                elif t == "originalName" and d["name"] is None:
                    d["name"] = (c.text or "").strip()
                elif t in ("registrationCategory", "subCategory") and d["cat"] is None:
                    d["cat"] = (c.text or "").strip()
                elif t == "country" and d["country"] is None:
                    d["country"] = (c.text or "").strip()
                elif t == "registrationDate":
                    d["regdate"] = (c.text or "").strip()
                elif t == "lastUpdateDate":
                    d["lastupd"] = (c.text or "").strip()
                elif t == "EPAccreditedNumber":
                    d["epa"] = (c.text or "").strip()
                elif t == "membersFTE":
                    d["membersFTE"] = (c.text or "").strip()
            if d["reg"]:
                orgs[d["reg"]] = d
            elem.clear()
    return export, orgs


export_a, A = parse("tr_2023JAN.xml")
export_b, B = parse("tr_2023JUN.xml")
print(f"A export: {export_a}\nB export: {export_b}")

gone = sorted((set(A) - set(B)), key=lambda r: A[r]["name"] or "")
shown_gone = 0
# prefer a disappearance whose lastUpdate is typical (deadline passed mid-window)
for r in gone:
    lu = A[r]["lastupd"]
    if lu and "2022-04" <= lu[:7] <= "2022-08":
        d = A[r]
        print("\nREMOVED example (in A, absent from B):")
        for k in ("reg", "name", "cat", "country", "regdate", "lastupd", "epa"):
            print(f"  {k}: {d[k]}")
        shown_gone += 1
        if shown_gone >= 2:
            break

surv = (set(A) & set(B))
shown = 0
for r in sorted(surv, key=lambda x: (B[x]["lastupd"] or "")):
    db = B[r]
    da = A[r]
    print("\nSURVIVOR example (updated soon after A):")
    for k in ("reg", "name", "cat", "country"):
        print(f"  {k}: {da[k]}")
    print(f"  regdate: {da['regdate']}")
    print(f"  lastUpdate A: {da['lastupd']}")
    print(f"  lastUpdate B: {db['lastupd']}")
    shown += 1
    if shown >= 2:
        break
