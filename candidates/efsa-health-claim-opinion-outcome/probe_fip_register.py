#!/usr/bin/env python3
"""Discovery probe: DG SANTE FIP EU health-claims register - status/type/year counts.

Reproduces the 2026-11-06 measurements recorded in record.json/notes.md:
  - one anonymous bulk GET returns the whole published register as nested JSON
    (19,885,668 bytes on 2026-11-06, 2,337 published policy items);
  - per-claim fields: hcClaimType, hcClaimStatus, hcClaim wording,
    hcReasonsForNonAuth, hcCondOfUse, EFSA question number + opinion URL,
    applicant fields (13.5/14);
  - decision year: 13.1 items carry the opinion citation 'YYYY;V(I):NNNN' in the
    question-number field; 13.5/14 items carry 'Q-YYYY-NNNNN' (application year).

Run:  python3 probe_fip_register.py [output_dir]
Keeps only aggregate counts; the bulk JSON stays in a scratch dir you pass (or
/tmp) and is NOT meant to be committed.
"""
import collections
import json
import re
import subprocess
import sys
import tempfile
import time

URL = ("https://ec.europa.eu/food/food-feed-portal/backend/api/"
       "policy-items?foodDomain=nut&authorisationType=nut_auth")
QK = "hcEfsaOpinionReferenceWrapper.hcEfsaOpinionReferenceMap.hcEfsaQuestionNbr"
TK = "hcCharacteristicWrapper.hcClaimType"
SK = "hcCharacteristicWrapper.hcClaimStatus"


def flatten(node, prefix=""):
    out = {}
    for ch in node.get("childrenValues") or []:
        vi = ch.get("valueIdentifier")
        p = prefix + (vi or "")
        if vi and ch.get("value") is not None:
            out[p] = ch.get("value")
        if ch.get("childrenValues"):
            out.update(flatten(ch, p + "."))
    return out


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
    path = outdir.rstrip("/") + "/fip_nut_policy_items.json"
    t0 = time.time()
    subprocess.run(["curl", "-s", "--max-time", "180", "-o", path, URL], check=True)
    dur = time.time() - t0
    size = len(open(path, "rb").read())
    rows = [flatten(it) for it in json.load(open(path))]
    print(f"fetched {size} bytes in {dur:.1f}s, {len(rows)} published items")
    st = collections.Counter()
    for f in rows:
        st[(f.get(TK), f.get(SK))] += 1
    print("claimType x claimStatus:")
    for (t, s), c in sorted(st.items(), key=lambda x: -x[1]):
        print(f"  {t} {s}: {c}")
    by_op_year = collections.defaultdict(lambda: collections.Counter())
    by_app_year = collections.defaultdict(lambda: collections.Counter())
    odd = []
    for f in rows:
        q = f.get(QK) or ""
        if f.get(TK) == "HCLBT_13_1":
            m = re.match(r"^(\d{4});", q)
            if m:
                by_op_year[m.group(1)][f.get(SK)] += 1
            else:
                odd.append(q)
        else:
            m = re.match(r"^(?:EFSA-)?Q-(\d{4})-", q)
            if m:
                by_app_year[m.group(1)][f.get(SK)] += 1
            else:
                odd.append(q)
    print("Art 13.1 by opinion-citation year x status:")
    for y in sorted(by_op_year):
        print(f"  {y}: " + ", ".join(f"{k}={v}" for k, v in sorted(by_op_year[y].items())))
    print("Art 13.5/14 by application (Q-number) year x status:")
    for y in sorted(by_app_year):
        print(f"  {y}: " + ", ".join(f"{k}={v}" for k, v in sorted(by_app_year[y].items())))
    if odd:
        print("unparseable question numbers:", odd)


if __name__ == "__main__":
    main()
