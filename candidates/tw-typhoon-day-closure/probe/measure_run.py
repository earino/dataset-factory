"""Worker measurement pass: read-only source-side aggregates for two East Asia
candidates (discovery split-capacity evidence; no labelled rows or panels emitted).

Part A (jp-moe-pollen-exceedance): all MOE Hanako pollen archive files (env.go.jp
  page_00209.html, 2003-2021). Per (season, region) file: station series count,
  valid station-days (24/24 valid hourly values), censored/incomplete days, and
  positive station-day counts at fixed daily-total thresholds. Old non-zip (.xls)
  files are counted, not parsed.

Part B (tw-typhoon-day-closure): DGPA closure-announcement census over the
  bundled 500-record list (2001-2026). For each announcement: fetch detail page,
  fetch the nds.html attachment, decode (utf-8/big5), segment the visible text by
  the 22 county names, classify each county row (full-day county-wide closure /
  partial-district-school / half-day / open / other). Aggregate per year and
  count consecutive-date event runs. Per-county per-date rows are NOT stored.

Writes /output/measure_report.json only.
"""
import io
import json
import re
import ssl
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (scout-research; dataset-factory) measure/1.0"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE  # DGPA chain lacks Subject Key Identifier (recorded 2026-10-22)
DGPA = "https://www.dgpa.gov.tw"
ENV_BASE = "https://www.env.go.jp"
ARCHIVE = ENV_BASE + "/page_00209.html"
THRESHOLDS = [40, 80, 160, 320, 640, 1280]
MISSING_RE = re.compile(r"^-99\d+$")

COUNTIES = ["臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市", "基隆市",
            "新竹市", "嘉義市", "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣",
            "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"]


def county_variants():
    out = []
    for c in COUNTIES:
        v = {c, c.replace("臺", "台"), c.replace("市", "巿"), c.replace("臺", "台").replace("市", "巿")}
        out.append((c, sorted(v)))
    return out


CVAR = county_variants()


def fetch(url, timeout=45, tries=3, limit=None):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                body = r.read(limit) if limit else r.read()
            return body, len(body)
        except Exception as e:  # noqa: BLE001 - record and retry
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


# ---------------------------------------------------------------- part A
def parse_xlsx(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    ss = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
    strings = re.findall(r"<t[^>]*>(.*?)</t>", ss, re.S)
    sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
    rows = []
    for rm in re.finditer(r"<row[^>]*>(.*?)</row>", sheet, re.S):
        cells = []
        for cm in re.finditer(r"<c\b[^>]*>(.*?)</c>", rm.group(1), re.S):
            tag, body = cm.group(0), cm.group(1)
            vm = re.search(r"<v>(.*?)</v>", body, re.S)
            val = vm.group(1) if vm else None
            if 't="s"' in tag and val is not None:
                try:
                    val = strings[int(val)]
                except ValueError:
                    pass
            cells.append(val)
        rows.append(cells)
    return rows


def parse_xls(data):
    """BIFF .xls via xlrd (2003-2014 archive files). Cells normalised:
    whole-number floats -> int so downstream str() matching works."""
    import xlrd
    book = xlrd.open_workbook(file_contents=data, on_demand=True)
    sh = book.sheet_by_index(0)

    def norm(v):
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v

    return [[norm(sh.cell_value(r, c)) for c in range(sh.ncols)] for r in range(sh.nrows)]


def files_of(seg):
    out, year = {}, None
    for m in re.finditer(r'(20\d\d)年|href="(/content/\d+\.(?:xlsx|xls))"[^>]*>([^<]{2,12})<', seg):
        if m.group(1):
            year = m.group(1)
        else:
            out.setdefault(year, []).append({"region": m.group(3).strip(),
                                            "url": ENV_BASE + m.group(2),
                                            "suffix": m.group(2).rsplit(".", 1)[1]})
    return out


def measure_season_file(entry):
    rec = {"region": entry["region"], "url": entry["url"]}
    body, n = fetch(entry["url"], limit=8_000_000)
    rec["bytes"] = n
    if entry["suffix"] == "xlsx":
        rows = parse_xlsx(body)
    elif entry["suffix"] == "xls":
        try:
            rows = parse_xls(body)
        except ImportError:
            rec["skipped"] = "xlrd unavailable in container"
            return rec
    else:
        rec["skipped"] = f"suffix {entry['suffix']} unrecognised"
        return rec
    data = [r for r in rows if r and r[0] and re.fullmatch(r"20\d\d", str(r[0]))]
    rec["sheet_rows"] = len(rows)
    if not data:
        rec["error"] = "no data rows recognised"
        return rec
    n_series = len(data[0]) - 4
    # The sheets carry a trailing legend column inside the data rows (strings
    # like '-9998:降雪による欠測', 'ツキ'). A series whose cells mostly fail
    # float() is a legend column, not a station - drop it from the counts.
    col_len = [0] * n_series
    col_bad = [0] * n_series
    for r in data:
        for i in range(n_series):
            v = r[4 + i] if 4 + i < len(r) else None
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            try:
                float(v)
            except (TypeError, ValueError):
                col_bad[i] += 1
            col_len[i] += 1
    legend_cols = [i for i in range(n_series) if col_len[i] and col_bad[i] / col_len[i] > 0.3]
    keep = [i for i in range(n_series) if i not in legend_cols]
    rec["series_raw"] = n_series
    n_series = len(keep)
    rec["legend_columns_dropped"] = len(legend_cols)
    rec["series"] = n_series
    rec["data_rows"] = len(data)
    # day -> series -> list of values
    days = {}
    n_missing_cells = 0
    for r in data:
        try:
            m, d = int(r[1]), int(r[2])
        except (TypeError, ValueError):
            continue
        for i in keep:
            v = r[4 + i] if 4 + i < len(r) else None
            if v is None or (isinstance(v, str) and not v.strip()):
                days.setdefault((m, d), {}).setdefault(i, []).append(None)
                n_missing_cells += 1
            else:
                try:
                    x = float(v)
                except (TypeError, ValueError):
                    days.setdefault((m, d), {}).setdefault(i, []).append(None)
                    n_missing_cells += 1
                    continue
                if MISSING_RE.match(str(v)) or x < 0:
                    days.setdefault((m, d), {}).setdefault(i, []).append(None)
                    n_missing_cells += 1
                else:
                    days.setdefault((m, d), {}).setdefault(i, []).append(x)
    rec["missing_or_code_cells"] = n_missing_cells
    valid_days = censored = incomplete = 0
    pos = {t: 0 for t in THRESHOLDS}
    totals = []
    for (m, d), series in days.items():
        for i in keep:
            vals = series.get(i)
            if vals is None or len(vals) != 24:
                incomplete += 1
                continue
            if any(v is None for v in vals):
                censored += 1
                continue
            tot = sum(vals)
            valid_days += 1
            totals.append(tot)
            for t in THRESHOLDS:
                if tot >= t:
                    pos[t] += 1
    rec["valid_station_days"] = valid_days
    rec["censored_station_days"] = censored
    rec["incomplete_station_days"] = incomplete
    rec["positives"] = {str(t): pos[t] for t in THRESHOLDS}
    if totals:
        totals.sort()
        rec["daily_total_quartiles"] = [totals[0], totals[len(totals) // 4],
                                        totals[len(totals) // 2], totals[3 * len(totals) // 4],
                                        totals[-1]]
    return rec


def part_a(report):
    t0 = time.time()
    body, _ = fetch(ARCHIVE, limit=2_000_000)
    text = body.decode("utf-8", "replace")
    seg = text[text.find("〈花粉データ〉"): text.find("〈アメダスデータ〉")]
    pol = files_of(seg)
    per_year = {}
    files = []
    for y in sorted(pol):
        for entry in pol[y]:
            entry["year"] = y
            files.append(entry)
    # schema fixture: first file of the newest full season
    fixture = None
    for entry in files:
        if entry["year"] == "2021" and "関東" in entry["region"]:
            b, _ = fetch(entry["url"], limit=8_000_000)
            rows = parse_xlsx(b)
            fixture = {"url": entry["url"],
                       "header_rows": [[str(c)[:40] for c in (rows[k] if k < len(rows) else [])][:26]
                                       for k in range(min(2, len(rows)))],
                       "first_data_row": [str(c) for c in rows[2][:14]] if len(rows) > 2 else None}
            break
    # schema fixture: first .xls (BIFF) file, to verify the xlrd layout matches
    xls_fixture = None
    for entry in files:
        if entry["suffix"] == "xls":
            b, _ = fetch(entry["url"], limit=8_000_000)
            try:
                rws = parse_xls(b)
            except ImportError:
                rws = None
            if rws:
                xls_fixture = {"url": entry["url"],
                               "first_rows": [[str(c)[:34] for c in (rws[k] if k < len(rws) else [])][:24]
                                              for k in range(min(4, len(rws)))]}
            break
    ok = errs = 0
    for entry in files:
        try:
            rec = measure_season_file(entry)
            ok += 1
        except Exception as e:  # noqa: BLE001
            rec = {"region": entry["region"], "url": entry["url"], "error": repr(e)[:180]}
            errs += 1
        y = entry["year"]
        agg = per_year.setdefault(y, {"files": 0, "series": 0, "valid_station_days": 0,
                                      "censored": 0, "incomplete": 0,
                                      "positives": {str(t): 0 for t in THRESHOLDS}, "errors": 0})
        agg["files"] += 1
        agg["errors"] += 1 if "error" in rec else 0
        if "series" in rec:
            agg["series"] += rec["series"]
            agg["valid_station_days"] += rec.get("valid_station_days", 0)
            agg["censored"] += rec.get("censored_station_days", 0)
            agg["incomplete"] += rec.get("incomplete_station_days", 0)
            pos = rec.get("positives", {})
            for t in THRESHOLDS:
                agg["positives"][str(t)] += pos.get(str(t), 0)
        print(f"A {y} {entry['region']}: valid={rec.get('valid_station_days')} "
              f"pos80={rec.get('positives', {}).get('80')}", flush=True)
    report["pollen"] = {"archive_files": len(files), "parsed_ok": ok, "errors": errs,
                        "per_year": per_year, "kanto_2021_fixture": fixture,
                        "xls_fixture": xls_fixture,
                        "requests": len(files) + 2,
                        "wall_clock_s": round(time.time() - t0, 1)}


# ---------------------------------------------------------------- part B
def visible(h):
    h = re.sub(r"<script[\s\S]*?</script>", "", h)
    h = re.sub(r"<style[\s\S]*?</style>", "", h)
    h = re.sub(r"<[^>]+>", "|", h)
    return re.sub(r"\|{2,}", "|", h)


def classify_segment(seg):
    """Coarse label for the status text of one county row on effective date D."""
    if re.search(r"[鄉鎮區里村學校][^:：]{0,18}[:：]", seg[:20]):
        return "partial"
    seg_d = re.split(r"明天|次日", seg)[0]  # only the D-relevant part
    if "已達停止上班及上課標準" in seg_d or "已達停止辦公及上課" in seg_d:
        return "full"
    open_words = ("照常" in seg_d) or ("未達" in seg_d) or ("尚未" in seg_d)
    stop_work = ("停止上班" in seg_d or "停止辦公" in seg_d) and "未達" not in seg_d
    stop_school = "停止上課" in seg_d and "未達" not in seg_d
    if stop_work and stop_school and not open_words:
        return "full"
    if ("停止" in seg_d) and re.search(r"上午|下午|晚上|中午", seg_d) and not open_words:
        return "half"
    if open_words:
        return "open"
    if "停止" in seg_d:
        return "other_stop"
    return "other"


def parse_county_classes(vis):
    marks = []
    for canon, variants in CVAR:
        for v in variants:
            for m in re.finditer(re.escape(v), vis):
                marks.append((m.start(), m.end(), canon))
    marks.sort()
    out = {}
    seen_spans = set()
    for idx, (s, e, canon) in enumerate(marks):
        if any(s >= a and s < b for a, b in seen_spans):
            continue
        nxt = marks[idx + 1][0] if idx + 1 < len(marks) else min(len(vis), s + 160)
        seg = vis[e:min(nxt, s + 160)]
        cls = classify_segment(seg)
        out[canon] = out.get(canon) or cls
        if cls in ("full",):
            break_next = True
        seen_spans.add((s, e))
    return out


def eff_date(title):
    m = re.match(r"(\d+)年(\d+)月(\d+)日", title)
    if not m:
        return None
    return f"{int(m.group(1)) + 1911}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def measure_announcement(item):
    out = {"pid": item["pid"], "title": item["title"], "date": eff_date(item["title"])}
    try:
        det, _ = fetch(f"{DGPA}/information?uid=374&pid={item['pid']}", limit=300_000)
        atts = [a.replace("&amp;", "&") for a in re.findall(r'href="(/FileConversion[^"]+)"',
                                                             det.decode("utf-8", "replace"))]
        # modern records name the Chinese attachment nds.html; old records use a
        # descriptive .htm name. Either way the Chinese one is the first non-English
        # link (English: name=ndsE.html or name=%e8%8b%b1%e6%96%87%e7%89%88).
        cand = [a for a in atts if "ndse" not in a.lower() and "%e8%8b%b1%e6%96%87" not in a.lower()]
        if not cand:
            out["no_attachment"] = True
            return out
        raw, nb = fetch(DGPA + cand[0], limit=300_000)
        out["attachment_bytes"] = nb
        try:
            h = raw.decode("utf-8")
        except UnicodeDecodeError:
            h = raw.decode("big5", "replace")
        vis = visible(h)
        out["classes"] = parse_county_classes(vis)
        out["n_county_rows"] = len(out["classes"])
        out["has_tomorrow_phrase"] = "明天" in vis
    except Exception as e:  # noqa: BLE001
        out["error"] = repr(e)[:180]
    return out


def part_b(report):
    t0 = time.time()
    items = json.loads(Path("/workspace/tw_items_2026-10-31.json").read_text())
    results = []
    reqs = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(measure_announcement, it): it for it in items}
        done = 0
        for fu in as_completed(futs):
            r = fu.result()
            results.append(r)
            done += 1
            reqs += 2 if r.get("classes") is not None else (1 if not r.get("no_attachment") else 1)
            if done % 50 == 0:
                print(f"B {done}/{len(items)}", flush=True)
    results.sort(key=lambda r: r.get("date") or "")
    per_year = {}
    other_phrases = {}
    fixtures = {}
    for r in results:
        y = (r.get("date") or "????")[:4]
        agg = per_year.setdefault(y, {"announcements": 0, "parsed": 0, "no_rows": 0,
                                      "dates_with_full": 0, "countyday_full": 0,
                                      "countyday_partial": 0, "countyday_half": 0,
                                      "countyday_open": 0, "countyday_other": 0, "errors": 0})
        agg["announcements"] += 1
        if r.get("error"):
            agg["errors"] += 1
            continue
        classes = r.get("classes")
        if not classes:
            agg["no_rows"] += 1
            continue
        agg["parsed"] += 1
        full = sum(1 for c in classes.values() if c == "full")
        if full:
            agg["dates_with_full"] += 1
        agg["countyday_full"] += full
        agg["countyday_partial"] += sum(1 for c in classes.values() if c == "partial")
        agg["countyday_half"] += sum(1 for c in classes.values() if c == "half")
        agg["countyday_open"] += sum(1 for c in classes.values() if c == "open")
        agg["countyday_other"] += sum(1 for c in classes.values() if c in ("other", "other_stop"))
        if r["pid"] in ("13130", "13097") or y == "2001":
            fixtures[r["date"]] = {"pid": r["pid"], "classes": classes}
    # event runs: consecutive dates with >=1 full closure (cluster counts)
    full_dates = sorted(r["date"] for r in results
                        if r.get("classes") and any(c == "full" for c in r["classes"].values()))
    runs = []
    for d in full_dates:
        if runs and (datetime.strptime(d, "%Y-%m-%d") - datetime.strptime(runs[-1][-1], "%Y-%m-%d")).days == 1:
            runs[-1].append(d)
        else:
            runs.append([d])
    report["dgpa"] = {"announcements": len(results),
                      "dates_with_full_closure": len(full_dates),
                      "event_runs_with_full_closure": len(runs),
                      "run_sizes": sorted((len(x) for x in runs), reverse=True)[:12],
                      "per_year": per_year, "fixtures": fixtures,
                      "requests_approx": reqs, "wall_clock_s": round(time.time() - t0, 1)}


def main():
    if "--run" not in __import__("sys").argv:
        print("refusing to run without --run (prevents accidental coordinator-side bulk fetch)")
        return 0
    report = {"started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    part_a(report)
    part_b(report)
    report["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = Path("/output/measure_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print("wrote", out, out.stat().st_size, "bytes", flush=True)


if __name__ == "__main__":
    main()
