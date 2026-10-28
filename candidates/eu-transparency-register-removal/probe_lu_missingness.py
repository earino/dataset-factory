#!/usr/bin/env python3
"""Count empty/absent lastUpdateDate in the 2024-12-31 ('2025 - JANUARY') export.

Uses the same control-character-reference sanitizer as tr_transitions2.py.
"""
import re
import xml.etree.ElementTree as ET

_CTRL = re.compile(rb"&#(x[0-9A-Fa-f]+|[0-9]+);")
_KEEP = {9, 10, 13}


def local(tag):
    return tag.rsplit("}", 1)[-1]


def _clean_line(ln):
    def repl(m):
        try:
            v = int(m.group(1)[1:], 16) if m.group(1)[:1] in (b"x", b"X") else int(m.group(1))
        except ValueError:
            return b""
        ok = (v >= 32 or v in _KEEP) and not (0xD800 <= v <= 0xDFFF) and v not in (0xFFFE, 0xFFFF)
        return m.group(0) if ok else b""
    return _CTRL.sub(repl, ln)


n = 0
empty_lu = 0
old_lu = 0
parser = ET.XMLPullParser(events=("end",))
with open("tr_2025JAN.xml", "rb") as f:
    for line in f:
        parser.feed(_clean_line(line))
        for event, elem in parser.read_events():
            if local(elem.tag) == "interestRepresentative":
                n += 1
                lu = None
                for c in elem.iter():
                    if local(c.tag) == "lastUpdateDate":
                        lu = (c.text or "").strip()
                        break
                if not lu:
                    empty_lu += 1
                elif lu[:4] < "2024":
                    old_lu += 1
                elem.clear()
parser.close()

print(f"orgs={n} empty_lastUpdateDate={empty_lu} lastUpdateDate_before_2024={old_lu}")
