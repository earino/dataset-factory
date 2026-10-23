#!/usr/bin/env python3
"""Probe 2: detail evidence for chilecompra-tender-outcome selection questions.

Small bounded follow-up to probe_horizon.py (which kept only aggregates):
  - status x statusDetails cross-tab on award entries (label vocabulary);
  - the exact processes NOT terminal within 180d in the 2020-06 sample;
  - lag-0 (award release dated at publication) examples;
  - urlContract documents for 2021-06 items: do contract signature dates
    exist, and what fields do they carry? (Q2)

~65 requests. Writes nothing; prints JSON.
Run:  python3 probe_horizon2.py
"""
import json
import time
import urllib.request

BASE = "https://api.mercadopublico.cl/APISOCDS/OCDS"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
reqs = {"count": 0, "bytes": 0}


def get(url, timeout=45):
    reqs["count"] += 1
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        body = resp.read()
    reqs["bytes"] += len(body)
    return body


def ts(value):
    return str(value or "")[:10]


def main():
    t0 = time.time()
    out = {"vocab": {}, "late_2020": [], "lag_zero": [], "contracts": []}
    details = {}
    for year, month in [(2019, 6), (2020, 6), (2021, 6)]:
        key = f"{year}-{month:02d}"
        doc = json.loads(get(f"{BASE}/listaOCDSAgnoMes/{year}/{month}/1/15"))
        procs = []
        for item in doc.get("data") or []:
            rec = {"ocid": item.get("ocid"),
                   "has_url_contract": bool(item.get("urlContract"))}
            url_award = (item.get("urlAward") or "").replace("http://", "https://")
            url_tender = (item.get("urlTender") or "").replace("http://", "https://")
            entries = []
            if url_award:
                adoc = json.loads(get(url_award))
                rels = [(r.get("date") or "", r) for r in (adoc.get("releases") or [])
                        if "award" in (r.get("tag") or []) or "awardUpdate" in (r.get("tag") or [])]
                rels.sort(key=lambda p: p[0])
                rec["award_release_count"] = len(rels)
                for rel_date, rel in rels:
                    for e in (rel.get("awards") or []):
                        entries.append({"rel_date": ts(rel_date),
                                        "rel_tags": rel.get("tag"),
                                        "status": (e.get("status") or "").strip(),
                                        "statusDetails": (e.get("statusDetails") or "").strip(),
                                        "award_date": ts(e.get("date"))})
            rec["award_entries"] = entries
            if url_tender:
                tdoc = json.loads(get(url_tender))
                tenders = [r for r in (tdoc.get("releases") or [])
                           if "tender" in (r.get("tag") or []) and r.get("date")]
                tenders.sort(key=lambda r: r["date"])
                rec["pub_date"] = ts(tenders[0]["date"]) if tenders else None
                rec["first_release_status"] = \
                    ((tenders[0].get("tender") or {}).get("status") or "").strip() \
                    if tenders else None
            procs.append(rec)
            for e in entries:
                k = (e["status"], e["statusDetails"])
                out["vocab"][repr(k)] = out["vocab"].get(repr(k), 0) + 1
        details[key] = procs

        if key == "2020-06":
            for p in procs:
                ents = p.get("award_entries") or []
                pub = p.get("pub_date")
                if not ents:
                    out["late_2020"].append({"ocid": p["ocid"], "pub": pub,
                                             "why": "no_award_entries",
                                             "rel_count": p.get("award_release_count")})
                elif pub and min(e["rel_date"] for e in ents) > "2020-12-27":
                    out["late_2020"].append({"ocid": p["ocid"], "pub": pub,
                                             "entries": ents})
        if key == "2019-06":
            for p in procs:
                ents = p.get("award_entries") or []
                if ents and p.get("pub_date") and \
                        min(e["rel_date"] for e in ents) == p["pub_date"]:
                    out["lag_zero"].append({"ocid": p["ocid"], "pub": p["pub_date"],
                                            "entries": ents[:2]})
                    if len(out["lag_zero"]) >= 3:
                        break

    # contract documents for 2021-06 items that have urlContract
    doc = json.loads(get(f"{BASE}/listaOCDSAgnoMes/2021/6/1/40"))
    fetched = 0
    for item in doc.get("data") or []:
        url_contract = (item.get("urlContract") or "").replace("http://", "https://")
        if url_contract and fetched < 5:
            fetched += 1
            cdoc = json.loads(get(url_contract))
            contracts = []
            for rel in cdoc.get("releases") or []:
                contracts.extend(rel.get("contracts") or [])
            contracts.extend((cdoc.get("compiledRelease") or {}).get("contracts") or [])
            sample = []
            for c in contracts[:2]:
                sample.append({k: c.get(k) for k in
                               ("id", "status", "date", "period", "signatureDate",
                                "awardID", "value")})
            out["contracts"].append({
                "ocid": item.get("ocid"), "n_contracts": len(contracts),
                "release_tags": [r.get("tag") for r in cdoc.get("releases") or []],
                "sample": sample})
    out["detail_sample"] = {"n_per_month": {k: len(v) for k, v in details.items()},
                            "first_release_status": {
        k: sorted({p.get("first_release_status") for p in v})
        for k, v in details.items()}}
    out["cost"] = {"requests": reqs["count"], "bytes": reqs["bytes"],
                   "seconds": round(time.time() - t0, 1)}
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
