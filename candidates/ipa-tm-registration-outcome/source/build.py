#!/usr/bin/env python3
"""Discovery aggregate-count job for `ipa-tm-registration-outcome`.

Runs on an expendable worker only. Downloads IPRAPID.zip (the weekly IP
Australia open-data product, CC BY 4.0) once, then streams the six CSV members
without extracting them to disk, filtering to ip_right_type == trade_mark, and
measures the aggregates the candidate record needs before any construction:

* filing counts by application_date year and by Australian financial year
  (for the publisher cross-check);
* outcome per application: standing registered event vs pre-grant terminal
  event vs censored, by filing year - the split-capacity and eligibility
  evidence;
* pending (censored) share by filing year, to set the eligibility cutoff;
* feature coverage: Nice class counts, goods/services/both, mark-type flags,
  applicant type/country/state/ABN, agent presence, Madrid/direct channel,
  founding-applicant effective-date lag, and prior-TM-history distribution
  with its registration-rate association (first headroom signal);
* classification_date - application_date lag (filing-time availability of the
  Nice classes) and event-declared vs application_date lag;
* three dated example applications with full timelines for the record;
* fetch cost measured (bytes, seconds, sha256).

No dataset is constructed here; the output is one compact JSON report.
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import sys
import time
import urllib.request
import zipfile
from array import array
from collections import Counter

URL = ("https://data.gov.au/data/dataset/423000b8-5735-4447-bcb9-792644bcd7ea/"
       "resource/c79b3af6-3720-44ac-9e39-6a68f5635924/download/iprapid.zip")
TM = "trade_mark"

REG_CATEGORIES = {"registered", "registered_historical", "granted", "granted_historical"}
FAIL_CATEGORIES = {"refused", "refused_historical", "rejected", "withdrawn",
                   "lapsed", "lapsed_historical", "linked", "linked_historical",
                   "cancelled", "not_filed", "voided"}


def parse_date(s):
    if not s or len(s) < 10:
        return None
    try:
        return datetime.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None


def trueish(s):
    return str(s).strip().upper() in ("TRUE", "T", "1", "Y")


def fetch(url, path):
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "scout-discovery/1.0"})
    h = hashlib.sha256()
    n = 0
    with urllib.request.urlopen(req, timeout=900) as r:
        lm = r.headers.get("Last-Modified")
        cl = r.headers.get("Content-Length")
        with open(path, "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
                h.update(b)
                n += len(b)
    dt = time.time() - t0
    return {"url": url, "bytes": n, "seconds": round(dt, 1),
            "MBps": round(n / 1e6 / dt, 1) if dt else None,
            "last_modified": lm, "content_length": cl,
            "sha256": h.hexdigest(),
            "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def table_stream(zf, name):
    fh = zf.open(name)
    text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline="")
    reader = csv.reader(text)
    header = next(reader)
    return header, reader


def idx(header, name):
    return header.index(name) if name in header else None


def require(header, report, table, *names):
    """Exit with the observed header recorded if an essential column is absent."""
    missing = [n for n in names if n not in header]
    if missing:
        report.data.setdefault("header_failures", {})[table] = {"missing": missing, "header": header}
        report.save()
        print(f"FAIL: {table} header missing {missing}: {header}")
        raise SystemExit(2)


def pick(row, header, i):
    if i is None:
        return None
    return row[i]


def subset(row, header, keys):
    """Row dict restricted to the keys the table actually carries."""
    return {k: row[header.index(k)] for k in keys if k in header}


class Report:
    def __init__(self, out_path):
        self.out_path = out_path
        self.data = {}

    def save(self):
        with open(self.out_path, "w") as f:
            json.dump(self.data, f, indent=1, sort_keys=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--zip", required=True)
    ap.add_argument("--url", default=URL)
    ap.add_argument("--skip-download", action="store_true",
                    help="use the existing --zip file as-is (local smoke test)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rep = Report(os.path.join(args.out, "report.json"))
    t_start = time.time()
    rep.data["passes"] = {}

    # ---- fetch (measured) --------------------------------------------------
    if args.skip_download or (os.path.exists(args.zip) and os.path.getsize(args.zip) > 10 ** 9):
        rep.data["fetch"] = {"note": "zip already present; download not repeated"}
    else:
        rep.data["fetch"] = fetch(args.url, args.zip)
    rep.save()

    z = zipfile.ZipFile(args.zip)
    members = [(i.filename, i.file_size, i.compress_size) for i in z.infolist()]
    rep.data["members"] = [{"name": n, "uncompressed_bytes": u, "compressed_bytes": c}
                           for n, u, c in members]
    rep.save()
    names = [n for n, _, _ in members]

    def find(table):
        cands = [n for n in names if table in n]
        if len(cands) != 1:
            print(f"FAIL: member for {table!r} not uniquely found: {cands}")
            return None
        return cands[0]

    f_app = find("application.csv")
    f_events = find("application_events.csv")
    f_class = find("application_classification.csv")
    f_links = find("application_links.csv")
    f_party = find("party_activity.csv")
    f_desc = find("application_description.csv")
    if any(v is None for v in (f_app, f_events, f_class, f_links, f_party, f_desc)):
        return 2

    headers_seen = {}
    examples = {}
    ex_lock = {"reg": False, "refused": False, "withdrawn": False}
    rep.data["headers"] = headers_seen  # live reference: headers recorded even on a later crash

    # ---- pass 1: application table ----------------------------------------
    t0 = time.time()
    header, rows = table_stream(z, f_app)
    headers_seen["application"] = header
    require(header, rep, "application", "ip_right_type", "application_number",
            "application_date", "status")
    c_type = idx(header, "ip_right_type")
    c_num = idx(header, "application_number")
    c_sub = idx(header, "ip_right_sub_type")
    c_status = idx(header, "status")
    c_adate = idx(header, "application_date")
    c_reg = idx(header, "gained_registration_status_date")
    if None in (c_type, c_num, c_adate, c_status):
        print(f"FAIL: application header missing key columns: {header}")
        return 2

    app_date = {}            # app -> application_date (date)
    app_info = {}           # app -> (status, sub_type, has_gained_registration_status_date)
    tm_status = Counter()
    tm_sub = Counter()
    n_rows_all = n_tm = 0
    for row in rows:
        n_rows_all += 1
        if row[c_type] != TM:
            continue
        n_tm += 1
        num = row[c_num]
        d = parse_date(row[c_adate])
        status = row[c_status]
        sub = pick(row, header, c_sub) or ""
        has_reg = bool(pick(row, header, c_reg))
        if d is not None:
            app_date[num] = d
        app_info[num] = (status, sub, has_reg)
        tm_status[status] += 1
        tm_sub[sub] += 1
        if d is not None and d.year == 2015 and len(examples) < 3:
            if not ex_lock["reg"] and (has_reg or status in ("registered", "protected")):
                examples[num] = {"kind": "registered", "application_row": dict(zip(header, row))}
                ex_lock["reg"] = True
            elif not ex_lock["refused"] and status == "refused":
                examples[num] = {"kind": "refused", "application_row": dict(zip(header, row))}
                ex_lock["refused"] = True
            elif not ex_lock["withdrawn"] and status == "withdrawn":
                examples[num] = {"kind": "withdrawn", "application_row": dict(zip(header, row))}
                ex_lock["withdrawn"] = True
    p = rep.data["passes"]
    p["application_seconds"] = round(time.time() - t0, 1)
    p["application_rows_all_rights"] = n_rows_all
    p["application_rows_trade_mark"] = n_tm
    rep.data["application"] = {
        "rows_trade_mark": n_tm,
        "tm_status_counts": dict(tm_status.most_common()),
        "tm_sub_type_counts": dict(tm_sub.most_common()),
    }
    rep.save()

    # ---- pass 2: links -----------------------------------------------------
    t0 = time.time()
    header, rows = table_stream(z, f_links)
    headers_seen["application_links"] = header
    require(header, rep, "application_links", "ip_right_type", "application_number", "link_type")
    c_type = idx(header, "ip_right_type")
    c_num = idx(header, "application_number")
    c_lt = idx(header, "link_type")
    link_counts = Counter()
    apps_madrid = set()
    apps_convention = set()
    apps_divisional = set()
    n_all = n_tmr = 0
    for row in rows:
        n_all += 1
        if row[c_type] != TM:
            continue
        n_tmr += 1
        lt = row[c_lt]
        link_counts[lt] += 1
        num = row[c_num]
        if lt == "madrid_import":
            apps_madrid.add(num)
        elif lt == "convention_priority":
            apps_convention.add(num)
        elif lt in ("divisional_parent", "divisional_parent_unresolved"):
            apps_divisional.add(num)
        if num in examples:
            examples[num].setdefault("links", []).append(dict(zip(header, row)))
    p["links_seconds"] = round(time.time() - t0, 1)
    p["links_rows_all_rights"] = n_all
    p["links_rows_trade_mark"] = n_tmr
    rep.data["links"] = {
        "link_type_counts_tm": dict(link_counts.most_common(30)),
        "apps_with_madrid_import": len(apps_madrid),
        "apps_with_convention_priority": len(apps_convention),
        "apps_with_divisional_parent": len(apps_divisional),
    }
    rep.save()

    # ---- pass 3: classification ---------------------------------------------
    t0 = time.time()
    header, rows = table_stream(z, f_class)
    headers_seen["application_classification"] = header
    require(header, rep, "application_classification", "ip_right_type", "application_number")
    c_type = idx(header, "ip_right_type")
    c_num = idx(header, "application_number")
    c_cur = idx(header, "is_current")
    c_class = idx(header, "classification")
    c_coarse = idx(header, "coarse_classification_area")
    c_cdate = idx(header, "classification_date")
    n_all = n_tmr = 0
    cls_per_app = {}
    coarse_counts = Counter()
    lag_buckets = Counter()
    for row in rows:
        n_all += 1
        if row[c_type] != TM:
            continue
        n_tmr += 1
        if c_cur is not None and not trueish(row[c_cur]):
            continue
        num = row[c_num]
        if c_class is not None:
            cls_per_app.setdefault(num, set()).add(row[c_class])
        if c_coarse is not None:
            coarse_counts[row[c_coarse]] += 1
        if c_cdate is not None:
            cd = parse_date(row[c_cdate])
            ad = app_date.get(num)
            if cd is None or ad is None:
                lag_buckets["null_or_missing"] += 1
            else:
                days = (cd - ad).days
                if days < 0:
                    lag_buckets["negative"] += 1
                elif days == 0:
                    lag_buckets["0_days"] += 1
                elif days <= 7:
                    lag_buckets["1-7_days"] += 1
                elif days <= 30:
                    lag_buckets["8-30_days"] += 1
                elif days <= 90:
                    lag_buckets["31-90_days"] += 1
                elif days <= 365:
                    lag_buckets["91-365_days"] += 1
                else:
                    lag_buckets["over_365_days"] += 1
        if num in examples:
            examples[num].setdefault("classes", []).append(
                subset(row, header, ("classification", "classification_area",
                                     "coarse_classification_area", "classification_date")))
    cls_hist = Counter()
    for s in cls_per_app.values():
        k = len(s)
        if k == 1:
            cls_hist["1"] += 1
        elif k == 2:
            cls_hist["2"] += 1
        elif k == 3:
            cls_hist["3"] += 1
        elif k <= 5:
            cls_hist["4-5"] += 1
        elif k <= 9:
            cls_hist["6-9"] += 1
        else:
            cls_hist["10+"] += 1
    p["classification_seconds"] = round(time.time() - t0, 1)
    p["classification_rows_all_rights"] = n_all
    p["classification_rows_trade_mark"] = n_tmr
    rep.data["classification"] = {
        "distinct_nice_class_counts_per_app": dict(cls_hist),
        "coarse_classification_area_counts": dict(coarse_counts.most_common(10)),
        "classification_date_minus_application_date": dict(lag_buckets),
    }
    rep.save()

    # ---- pass 4: party activity ---------------------------------------------
    t0 = time.time()
    header, rows = table_stream(z, f_party)
    headers_seen["party_activity"] = header
    require(header, rep, "party_activity", "ip_right_type", "application_number",
            "party_id", "party_role_category")
    c_type = idx(header, "ip_right_type")
    c_num = idx(header, "application_number")
    c_pid = idx(header, "party_id")
    c_rcat = idx(header, "party_role_category")
    c_ptype = idx(header, "party_type")
    c_abn = idx(header, "abn")
    c_cc = idx(header, "country_code")
    c_sc = idx(header, "state_code")
    c_eff = idx(header, "effective_from_date")
    c_found = idx(header, "is_founding")
    n_all = n_tmr = 0
    party_type_counts = Counter()
    country_counts = Counter()
    state_counts = Counter()
    abn_yes = abn_no = 0
    eff_buckets = Counter()
    apps_agent = set()
    app_party = {}            # app -> founding applicant party_id
    app_party_founding = {}   # app -> bool (stored row was founding)
    party_apps = {}           # party_id -> array of application years
    for row in rows:
        n_all += 1
        if row[c_type] != TM:
            continue
        n_tmr += 1
        num = row[c_num]
        rcat = pick(row, header, c_rcat) or ""
        if rcat == "applicant_agent":
            apps_agent.add(num)
        if rcat != "applicant":
            continue
        found = trueish(pick(row, header, c_found)) if c_found is not None else True
        stored = app_party_founding.get(num)
        if stored is True:
            continue
        if stored is False and not found:
            continue
        pid = pick(row, header, c_pid)
        app_party[num] = pid
        app_party_founding[num] = found
        ad = app_date.get(num)
        if ad is not None and pid:
            party_apps.setdefault(pid, array("i")).append(ad.year)
        party_type_counts[pick(row, header, c_ptype)] += 1
        country_counts[pick(row, header, c_cc)] += 1
        state_counts[pick(row, header, c_sc)] += 1
        if pick(row, header, c_abn):
            abn_yes += 1
        else:
            abn_no += 1
        if c_eff is not None and ad is not None:
            ed = parse_date(row[c_eff])
            if ed is None:
                eff_buckets["null"] += 1
            else:
                days = (ed - ad).days
                if days == 0:
                    eff_buckets["same_day"] += 1
                elif 0 < days <= 7:
                    eff_buckets["within_7_days_after"] += 1
                elif days > 7:
                    eff_buckets["later"] += 1
                else:
                    eff_buckets["before_filing"] += 1
        if num in examples:
            examples[num].setdefault("parties", []).append(
                subset(row, header, ("party_id", "party_role", "party_type", "party_name", "abn",
                                     "country_code", "state_code", "postcode", "effective_from_date",
                                     "is_current", "is_founding")))
    p["party_seconds"] = round(time.time() - t0, 1)
    p["party_rows_all_rights"] = n_all
    p["party_rows_trade_mark"] = n_tmr
    rep.data["party"] = {
        "founding_applicant_party_type": dict(party_type_counts.most_common()),
        "founding_applicant_country_top15": dict(country_counts.most_common(15)),
        "founding_applicant_state_top10": dict(state_counts.most_common(10)),
        "founding_applicant_abn_present": abn_yes,
        "founding_applicant_abn_absent": abn_no,
        "founding_applicant_effective_from_vs_application": dict(eff_buckets),
        "apps_with_agent": len(apps_agent),
    }
    rep.save()

    # ---- pass 5: description --------------------------------------------------
    t0 = time.time()
    header, rows = table_stream(z, f_desc)
    headers_seen["application_description"] = header
    require(header, rep, "application_description", "ip_right_type", "application_number",
            "description_type")
    c_type = idx(header, "ip_right_type")
    c_num = idx(header, "application_number")
    c_dt = idx(header, "description_type")
    n_all = n_tmr = 0
    desc_type_counts = Counter()
    apps_word_phrase = set()
    for row in rows:
        n_all += 1
        if row[c_type] != TM:
            continue
        n_tmr += 1
        dt = row[c_dt]
        desc_type_counts[dt] += 1
        num = row[c_num]
        if dt == "trade_mark_word_mark_phrase":
            apps_word_phrase.add(num)
        if num in examples and dt in ("trade_mark_word_mark_phrase", "trade_mark_image_words",
                                       "trade_mark_image_description"):
            examples[num].setdefault("descriptions", []).append(
                {"description_type": dt, "description_value": row[header.index("description_value")]})
    p["description_seconds"] = round(time.time() - t0, 1)
    p["description_rows_all_rights"] = n_all
    p["description_rows_trade_mark"] = n_tmr
    rep.data["description"] = {
        "description_type_counts_tm": dict(desc_type_counts.most_common(25)),
        "apps_with_word_mark_phrase": len(apps_word_phrase),
    }
    rep.save()

    # ---- pass 6: events (labels) ----------------------------------------------
    t0 = time.time()
    header, rows = table_stream(z, f_events)
    headers_seen["application_events"] = header
    require(header, rep, "application_events", "ip_right_type", "application_number",
            "is_standing", "event_category", "event_declared_date")
    c_type = idx(header, "ip_right_type")
    c_num = idx(header, "application_number")
    c_stand = idx(header, "is_standing")
    c_cat = idx(header, "event_category")
    c_ed = idx(header, "event_declared_date")
    n_all = n_tmr = 0
    outcome = {}            # app -> 1 registered / 2 failed-before-registration / absent = censored
    cat_counts = Counter()
    ttreg_hist = Counter()  # months between application_date and first standing reg event (declared), 6-month bins
    within = Counter()
    for row in rows:
        n_all += 1
        if row[c_type] != TM:
            continue
        n_tmr += 1
        cat = pick(row, header, c_cat)
        num = row[c_num]
        if cat is not None:
            cat_counts[cat] += 1
        if num in examples:
            examples[num].setdefault("events", []).append(
                subset(row, header, ("event_type", "event_category", "event_effective_date",
                                     "event_declared_date", "is_standing")))
        if c_stand is not None and not trueish(row[c_stand]):
            continue
        if cat in REG_CATEGORIES:
            if outcome.get(num) != 1:
                outcome[num] = 1
                ad = app_date.get(num)
                ed = parse_date(pick(row, header, c_ed))
                if ad is not None and ed is not None:
                    months = (ed.year - ad.year) * 12 + (ed.month - ad.month)
                    ttreg_hist[min(max(months // 6 * 6, 0), 60)] += 1
                    if months <= 12:
                        within["within_1y"] += 1
                    if months <= 24:
                        within["within_2y"] += 1
                    if months <= 36:
                        within["within_3y"] += 1
                    if months <= 60:
                        within["within_5y"] += 1
        elif cat in FAIL_CATEGORIES and outcome.get(num, 0) != 1:
            outcome[num] = 2
    p["events_seconds"] = round(time.time() - t0, 1)
    p["events_rows_all_rights"] = n_all
    p["events_rows_trade_mark"] = n_tmr
    rep.data["events"] = {
        "event_category_counts_tm": dict(cat_counts.most_common(40)),
        "apps_with_standing_registered_event": sum(1 for v in outcome.values() if v == 1),
        "apps_with_fail_event_no_reg": sum(1 for v in outcome.values() if v == 2),
        "time_to_registration_months_6m_bins_cap60": {str(k): v for k, v in sorted(ttreg_hist.items())},
        "registration_declared_within": dict(within),
    }
    rep.save()

    # ---- reconcile: outcome by filing year, splits, history, cross-checks -------
    by_year = {}
    fy_counts = Counter()
    regdate_vs_events = {"agree": 0, "events_reg_no_regdate": 0, "regdate_no_events_reg": 0}
    for num, ad in app_date.items():
        info = app_info.get(num)
        o = outcome.get(num, 0)
        d = by_year.setdefault(ad.year, [0, 0, 0, 0])
        d[0] += 1
        if o == 1:
            d[1] += 1
        elif o == 2:
            d[2] += 1
        else:
            d[3] += 1
        fy = ad.year if ad.month >= 7 else ad.year - 1
        fy_counts[f"FY{fy}-{str(fy + 1)[2:]}"] += 1
        if info is not None:
            has_rd = info[2]
            if o == 1 and has_rd:
                regdate_vs_events["agree"] += 1
            elif o == 1 and not has_rd:
                regdate_vs_events["events_reg_no_regdate"] += 1
            elif o != 1 and has_rd:
                regdate_vs_events["regdate_no_events_reg"] += 1

    by_year_clean = {}
    for y, d in sorted(by_year.items()):
        by_year_clean[str(y)] = {
            "n": d[0], "registered": d[1], "failed_before_registration": d[2],
            "censored": d[3], "censored_share": round(d[3] / d[0], 4) if d[0] else None,
        }

    splits = {}
    for name, lo, hi in [("train_1995_2013", 1995, 2013),
                         ("eval_2014_2018", 2014, 2018),
                         ("holdout_2019_2023", 2019, 2023),
                         ("holdout_2019_2022", 2019, 2022)]:
        n = r = f_ = c = 0
        for y, d in by_year.items():
            if lo <= y <= hi:
                n += d[0]
                r += d[1]
                f_ += d[2]
                c += d[3]
        splits[name] = {"n": n, "registered": r, "failed_before_registration": f_,
                        "censored": c, "censored_share": round(c / n, 4) if n else None}

    hist2 = {"prior0": [0, 0], "prior1plus": [0, 0]}
    for num, ad in app_date.items():
        if not (2010 <= ad.year <= 2019):
            continue
        o = outcome.get(num, 0)
        if o == 0:
            continue
        pid = app_party.get(num)
        prior = 0
        if pid and pid in party_apps:
            prior = sum(1 for v in party_apps[pid] if v < ad.year)
        key = "prior0" if prior == 0 else "prior1plus"
        hist2[key][0 if o == 1 else 1] += 1

    rep.data["outcome_by_filing_year"] = by_year_clean
    rep.data["filing_counts_by_australian_financial_year"] = dict(sorted(fy_counts.items()))
    rep.data["label_reconciliation_events_vs_gained_registration_status_date"] = regdate_vs_events
    rep.data["splits_candidate"] = splits
    rep.data["prior_history_vs_outcome_2010_2019"] = {
        "prior0": {"registered": hist2["prior0"][0], "failed": hist2["prior0"][1]},
        "prior1plus": {"registered": hist2["prior1plus"][0], "failed": hist2["prior1plus"][1]},
    }
    rep.data["examples"] = examples
    rep.data["headers"] = headers_seen
    rep.data["passes"]["total_seconds"] = round(time.time() - t_start, 1)
    rep.save()

    n_tm_final = rep.data["application"]["rows_trade_mark"]
    n_reg = rep.data["events"]["apps_with_standing_registered_event"]
    if n_tm_final < 100000 or n_reg < 1000:
        print(f"FAIL: implausible counts (tm apps {n_tm_final}, standing-reg {n_reg})")
        return 2
    print("OK: report written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
