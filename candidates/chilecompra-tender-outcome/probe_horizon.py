#!/usr/bin/env python3
"""Probe: award timing / terminal-state evidence for chilecompra-tender-outcome.

Answers, from the publisher's own records (anonymous OCDS API, bounded samples
of one closed cohort month per split), the questions the selection review
turned on:

  Q2  per-award `date` field presence (awards[].date) and award-release dates;
      contracts[] presence and any signature/date-like fields.
  Q4  award status sequences over time (does a later release supersede an
      earlier status?); lag from first tender release to first award release;
      fraction of processes with a terminal award state (active/unsuccessful/
      cancelled) within candidate horizons H; how a last-terminal-within-H
      rule differs from the pooled any-active rule the last build used.

Bounded discovery evidence: 3 list requests + 2 document requests per sampled
process (~1 req/s measured). No prediction panel is built and no performance
number is computed. Writes nothing; prints a compact JSON report.

Run from the candidate directory:  python3 probe_horizon.py
"""
import json
import time
import urllib.request

BASE = "https://api.mercadopublico.cl/APISOCDS/OCDS"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
MONTHS = [(2019, 6), (2020, 6), (2021, 6)]  # one closed month per split cohort
N = 40
HORIZONS = [90, 120, 150, 180, 270, 365]

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


def first_tender_date(tdoc):
    dates = [r.get("date") for r in (tdoc.get("releases") or [])
             if "tender" in (r.get("tag") or []) and r.get("date")]
    return min(dates) if dates else None


def award_entries(adoc):
    """[(release_date, entry)] from award-tagged releases, date-ordered."""
    out = []
    for rel in (adoc.get("releases") or []):
        tags = rel.get("tag") or []
        if "award" in tags or "awardUpdate" in tags:
            for entry in (rel.get("awards") or []):
                out.append((rel.get("date") or "", entry))
    out.sort(key=lambda pair: pair[0])
    return out


def contracts_in(doc):
    found = []
    for rel in (doc.get("releases") or []):
        found.extend(rel.get("contracts") or [])
    found.extend((doc.get("compiledRelease") or {}).get("contracts") or [])
    return found


def main():
    t0 = time.time()
    report = {}
    for year, month in MONTHS:
        key = f"{year}-{month:02d}"
        doc = json.loads(get(f"{BASE}/listaOCDSAgnoMes/{year}/{month}/1/{N}"))
        processes = []
        tags_seen, item_keys = set(), None
        for item in doc.get("data") or []:
            if item_keys is None:
                item_keys = sorted(item.keys())
            url_award = (item.get("urlAward") or "").replace("http://", "https://")
            url_tender = (item.get("urlTender") or "").replace("http://", "https://")
            rec = {"has_url_award": bool(url_award)}
            if not url_award:
                processes.append(rec)
                continue
            try:
                adoc = json.loads(get(url_award))
            except Exception as exc:
                rec["award_fetch_error"] = repr(exc)[:60]
                processes.append(rec)
                continue
            for rel in adoc.get("releases") or []:
                tags_seen.update(rel.get("tag") or [])
            rec["award_entries"] = [
                {"rel_date": ts(rel_date),
                 "status": (entry.get("status") or "").strip(),
                 "statusDetails": (entry.get("statusDetails") or "").strip(),
                 "award_date": ts(entry.get("date"))}
                for rel_date, entry in award_entries(adoc)]
            compiled = (adoc.get("compiledRelease") or {}).get("awards") or []
            rec["compiled_awards"] = [
                {"status": (e.get("status") or "").strip(),
                 "statusDetails": (e.get("statusDetails") or "").strip(),
                 "award_date": ts(e.get("date"))}
                for e in compiled]
            contracts = contracts_in(adoc)
            rec["contracts_in_award_doc"] = len(contracts)
            if contracts and key == f"{MONTHS[0][0]}-{MONTHS[0][1]:02d}":
                rec["contract_example_keys"] = sorted(contracts[0].keys())
            if url_tender:
                try:
                    tdoc = json.loads(get(url_tender))
                    pub = first_tender_date(tdoc)
                    rec["pub_date"] = ts(pub)
                    rec["tender_contracts"] = len(contracts_in(tdoc))
                    for rel in tdoc.get("releases") or []:
                        tags_seen.update(rel.get("tag") or [])
                    first = [r for r in (tdoc.get("releases") or [])
                             if "tender" in (r.get("tag") or []) and r.get("date")]
                    first.sort(key=lambda r: r["date"])
                    if first:
                        rec["first_release_status"] = \
                            ((first[0].get("tender") or {}).get("status") or "").strip()
                except Exception as exc:
                    rec["tender_fetch_error"] = repr(exc)[:60]
            processes.append(rec)
        report[key] = {"n_listed": len(doc.get("data") or []),
                       "total": doc.get("pagination", {}).get("total"),
                       "item_keys": item_keys, "tags_seen": sorted(tags_seen),
                       "processes": processes}

    # aggregates
    agg = {}
    for key, block in report.items():
        procs = block["processes"]
        with_pub = [p for p in procs if p.get("pub_date")]
        entries_all = [e for p in procs for e in p.get("award_entries") or []]
        entry_date_present = sum(1 for e in entries_all if e["award_date"])
        lags, terminal_frac, seq_patterns = [], {}, {}
        rule_disagreement, terminal_within = 0, {h: 0 for h in HORIZONS}
        states_at_180 = {}
        for p in with_pub:
            entries = p.get("award_entries") or []
            if not entries:
                seq_patterns["no_award_entries"] = \
                    seq_patterns.get("no_award_entries", 0) + 1
                continue
            pub = p["pub_date"]
            first_rel = min(e["rel_date"] for e in entries)
            if first_rel >= pub:
                lag = (time.mktime(time.strptime(first_rel, "%Y-%m-%d"))
                       - time.mktime(time.strptime(pub, "%Y-%m-%d"))) / 86400.0
                lags.append(int(lag))
            statuses = [e["status"] for e in entries]
            distinct = sorted(set(statuses))
            seq_patterns["->".join(distinct) if len(distinct) > 1
                          else distinct[0] or "EMPTY"] = \
                seq_patterns.get("->".join(distinct) if len(distinct) > 1
                                 else distinct[0] or "EMPTY", 0) + 1
            # pooled rule (old build): any active -> adjudicated; all
            # unsuccessful -> deserted; all cancelled -> revoked; else other
            pooled = ("active" if "active" in statuses else
                      "unsuccessful" if statuses and all(s == "unsuccessful"
                                                         for s in statuses) else
                      "cancelled" if statuses and all(s == "cancelled"
                                                      for s in statuses) else
                      "other")
            for h in HORIZONS:
                within = [e for e in entries if e["rel_date"] and e["rel_date"] <=
                          time.strftime("%Y-%m-%d", time.localtime(
                              time.mktime(time.strptime(pub, "%Y-%m-%d")) + h * 86400))]
                terminal = [e for e in reversed(within)
                           if e["status"] in ("active", "unsuccessful", "cancelled")]
                if terminal:
                    terminal_within[h] += 1
                    if h == 180:
                        states_at_180[terminal[0]["status"]] = \
                            states_at_180.get(terminal[0]["status"], 0) + 1
                        last = terminal[0]["status"]
                        if last != pooled:
                            rule_disagreement += 1
        lags.sort()
        agg[key] = {
            "n_with_pub_date": len(with_pub),
            "n_processes": len(procs),
            "no_url_award": sum(1 for p in procs if not p.get("has_url_award")),
            "award_entries_total": len(entries_all),
            "awards_dot_date_present": entry_date_present,
            "award_release_count_distribution": {
                str(k): sum(1 for p in procs
                            if len(p.get("award_entries") or []) == k)
                for k in sorted({len(p.get("award_entries") or [])
                                 for p in procs})},
            "first_award_release_lag_days": {
                "n": len(lags), "min": lags[0] if lags else None,
                "p50": lags[len(lags) // 2] if lags else None,
                "p90": lags[int(len(lags) * 0.9)] if lags else None,
                "max": lags[-1] if lags else None},
            "status_sequence_patterns": seq_patterns,
            "terminal_within_H": {str(h): terminal_within[h] for h in HORIZONS},
            "terminal_state_at_180": states_at_180,
            "pooled_vs_last_within_180_disagreement": rule_disagreement,
            "compiled_awards_processes": sum(
                1 for p in procs if p.get("compiled_awards")),
            "compiled_awards_with_date": sum(
                1 for p in procs for e in p.get("compiled_awards") or []
                if e["award_date"]),
            "contracts_in_award_doc_processes": sum(
                1 for p in procs if p.get("contracts_in_award_doc")),
            "contracts_in_tender_doc_processes": sum(
                1 for p in procs if p.get("tender_contracts")),
            "first_release_status_active": sum(
                1 for p in procs if p.get("first_release_status") == "active"),
        }
    print(json.dumps({"months": {k: {kk: vv for kk, vv in v.items()
                                     if kk != "processes"}
                                for k, v in report.items()},
                      "aggregate": agg,
                      "cost": {"requests": reqs["count"],
                               "bytes": reqs["bytes"],
                               "seconds": round(time.time() - t0, 1)}},
                     indent=1, default=str))


if __name__ == "__main__":
    main()
