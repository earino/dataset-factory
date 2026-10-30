# Recipe of worker job za-dws-access-001 (2026-10-30): the recorded next-action access
# test that settled this candidate's park verdict. Ran on a Hetzner cx23 worker from
# .factory/job-sources/za-dws-access-001/ (gitignored); copied here so the evidence
# has a durable recipe. Result: dws.gov.za 403 from the worker too; niwis timeout;
# data.gov.gh refused. See measurements.worker_access_test_2026_10_30 in record.json.
"""Bounded read-only access probe: DWS (ZA) weekly dam bulletins + data.gov.gh, from the worker network.

Discovery evidence only. Prints one JSON line per step to stdout (captured in
container.log) and writes /output/summary.json for the collected report.

Bounds: <= 40 requests, <= 30 MB total, 30 s per request, 8-minute hard deadline.
Stdlib only. Exits 0 as long as the summary was written, even if some targets failed.
"""
import hashlib
import html as htmllib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

START = time.time()
DEADLINE = START + 8 * 60
BUDGET_REQUESTS = 40
BUDGET_BYTES = 30 * 1024 * 1024
PER_REQ_TIMEOUT = 30
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

state = {"requests": 0, "bytes": 0}
summary = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "steps": []}


def log(step):
    summary["steps"].append(step)
    print(json.dumps(step, ensure_ascii=False)[:4000], flush=True)


def budget_ok():
    return state["requests"] < BUDGET_REQUESTS and state["bytes"] < BUDGET_BYTES and time.time() < DEADLINE


def fetch(url, max_bytes=2 * 1024 * 1024):
    """GET with redirect follow; returns a result dict (body attached under 'body' if 2xx)."""
    step = {"url": url}
    if not budget_ok():
        step["skipped"] = "budget/deadline reached"
        return step
    state["requests"] += 1
    t0 = time.time()
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=PER_REQ_TIMEOUT) as resp:
            data = b""
            while len(data) < max_bytes:
                chunk = resp.read(65536)
                if not chunk:
                    break
                data += chunk
            state["bytes"] += len(data)
            step.update({
                "status": resp.status,
                "final_url": resp.geturl(),
                "content_type": resp.headers.get("Content-Type"),
                "server": resp.headers.get("Server"),
                "content_length_header": resp.headers.get("Content-Length"),
                "bytes_downloaded": len(data),
                "truncated": len(data) >= max_bytes,
                "elapsed_s": round(time.time() - t0, 2),
                "body_sha256": hashlib.sha256(data).hexdigest(),
                "body_head": data[:400].decode("utf-8", "replace"),
            })
            step["body"] = data
    except urllib.error.HTTPError as exc:
        state["bytes"] += 0
        step.update({"status": exc.code, "error": "HTTPError",
                     "elapsed_s": round(time.time() - t0, 2)})
        try:
            step["body_head"] = exc.read(400).decode("utf-8", "replace")
        except Exception:
            pass
    except Exception as exc:
        step.update({"error": f"{type(exc).__name__}: {exc}",
                     "elapsed_s": round(time.time() - t0, 2)})
    return step


def text_of(data):
    raw = data.decode("utf-8", "replace")
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", htmllib.unescape(raw)).strip()


def links_of(base_url, data):
    raw = data.decode("utf-8", "replace")
    out = []
    for m in re.finditer(r"""(?is)<a\b[^>]*href\s*=\s*["']([^"'#]+)["']""", raw):
        href = m.group(1).strip()
        if not href or href.lower().startswith(("javascript:", "mailto:")):
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        out.append(absolute.split("#")[0])
    return out


# --- Step 0: egress context (which network is asking?) -------------------------
try:
    ip = fetch("https://ipinfo.io/json", max_bytes=8192)
    body = ip.pop("body", None) or b"{}"
    try:
        info = json.loads(body)
        ip = {k: v for k, v in ip.items() if k != "body_head"}
        ip["egress"] = {k: info.get(k) for k in ("ip", "city", "region", "country", "org")}
    except Exception:
        ip["body_head"] = str(body[:200])
    log({"step": "egress_context", **{k: v for k, v in ip.items() if k != "body"}})
except Exception as exc:
    log({"step": "egress_context", "error": f"{type(exc).__name__}: {exc}"})

# --- Step 1: DWS root (https + http) -----------------------------------------
root = fetch("https://www.dws.gov.za/")
root_body = root.pop("body", None)
log({"step": "dws_root_https", **{k: v for k, v in root.items() if k not in ("body", "body_head")},
     "body_head": root.get("body_head")})

http_root = fetch("http://www.dws.gov.za/")
http_root.pop("body", None)
log({"step": "dws_root_http", **{k: v for k, v in http_root.items() if k not in ("body", "body_head")}})

# --- Step 2: weekly bulletin page --------------------------------------------
weekly = fetch("https://www.dws.gov.za/Hydrology/Weekly/WeeklyBulletins.aspx")
weekly_body = weekly.pop("body", None)
weekly_public = {k: v for k, v in weekly.items() if k != "body_head"}
weekly_public["body_head"] = weekly.get("body_head")
log({"step": "dws_weekly_bulletins_page", **weekly_public})

file_links = []
page_links = []
dated = []
if weekly_body and weekly.get("status") == 200:
    all_links = links_of(weekly["final_url"], weekly_body)
    file_ext = re.compile(r"\.(pdf|xls|xlsx|doc|docx|csv|zip)(\?|$)", re.I)
    for link in all_links:
        if file_ext.search(link):
            file_links.append(link)
        else:
            page_links.append(link)
    file_links = sorted(set(file_links))
    page_links = sorted(set(page_links))

    # date/year extraction from file names
    dated = []
    for link in file_links:
        name = link.rsplit("/", 1)[-1]
        years = re.findall(r"(20\d{2})", name)
        dmy = re.findall(r"(\d{1,2})[-_ ]?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-_ ]?(20\d{2})?",
                         name, re.I)
        ymd = re.findall(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
        dated.append({"url": link, "name": name, "years": years,
                      "dmy": ["-".join(x for x in d if x) for d in dmy],
                      "ymd": ["-".join(ymd[0])] if ymd else []})
    log({"step": "dws_weekly_archive_enum",
         "file_link_count": len(file_links),
         "page_link_count": len(page_links),
         "file_links_sample": dated[:200],
         "page_links_sample": page_links[:60],
         "weekly_page_text_head": text_of(weekly_body)[:1500]})

# --- Step 3: NIWIS portal ------------------------------------------------------
niwis = fetch("https://niwis.dws.gov.za/niwis2/")
niwis.pop("body", None)
log({"step": "niwis2_root", **{k: v for k, v in niwis.items() if k not in ("body", "body_head")}})

# --- Step 4: terms/disclaimer instrument (from root links) --------------------
terms_pages = []
if root_body and root.get("status") == 200:
    candidates = []
    for link in links_of(root.get("final_url", "https://www.dws.gov.za/"), root_body):
        if re.search(r"(disclaimer|terms|copyright|legal|privacy)", link, re.I):
            candidates.append(link)
    candidates = sorted(set(candidates))[:2]
    log({"step": "terms_link_candidates", "links": candidates})
    for link in candidates:
        if not budget_ok():
            break
        page = fetch(link)
        body = page.pop("body", None)
        text = text_of(body)[:3000] if body else None
        log({"step": "terms_page", **{k: v for k, v in page.items() if k not in ("body", "body_head")},
             "text_head": text})
        if text:
            terms_pages.append({"url": link, "text_head": text})
# Always try the common SA-gov path too if nothing matched on the root page.
if not terms_pages and budget_ok():
    page = fetch("https://www.dws.gov.za/Disclaimer")
    body = page.pop("body", None)
    log({"step": "terms_page_fallback_disclaimer", **{k: v for k, v in page.items() if k not in ("body", "body_head")}})

# --- Step 5: newest weekly file -> schema evidence ----------------------------
if file_links:
    def date_key(entry):
        marks = entry.get("ymd") or entry.get("dmy") or [str(max(entry.get("years") or ["0"]))]
        return marks[0]
    newest = max(dated, key=date_key) if dated else {"url": file_links[-1], "name": file_links[-1].rsplit("/", 1)[-1]}
    blob = fetch(newest["url"], max_bytes=15 * 1024 * 1024)
    body = blob.pop("body", None)
    info = {k: v for k, v in blob.items() if k not in ("body", "body_head")}
    info["file_name"] = newest.get("name")
    log({"step": "newest_weekly_file", **info})
    if body and body[:2] == b"PK":
        try:
            zf = zipfile.ZipFile(io.BytesIO(body))
            names = zf.namelist()
            wb = zf.read("xl/workbook.xml").decode("utf-8", "replace")
            sheets = re.findall(r'<sheet[^>]*name="([^"]+)"', wb)
            shared = []
            if "xl/sharedStrings.xml" in names:
                sraw = zf.read("xl/sharedStrings.xml").decode("utf-8", "replace")
                shared = [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<si>(.*?)</si>", sraw, re.S)]
            sheet1 = next((n for n in names if re.match(r"xl/worksheets/sheet1?\.xml$", n)), None)
            row_count = None
            first_rows = []
            if sheet1:
                sxml = zf.read(sheet1).decode("utf-8", "replace")
                row_count = len(re.findall(r"<row\b", sxml))
                rows = re.findall(r"<row\b.*?</row>", sxml, re.S)[:3]
                for row in rows:
                    cells = []
                    for cm in re.finditer(r"<c\b[^>]*?(?:t=\"(\w+)\")?[^>]*>(.*?)</c>", row, re.S):
                        ctype, inner = cm.group(1), cm.group(2)
                        vm = re.search(r"<v>(.*?)</v>", inner, re.S)
                        if not vm:
                            cells.append(None)
                        elif ctype == "s":
                            cells.append(shared[int(vm.group(1))])
                        else:
                            cells.append(vm.group(1))
                    first_rows.append(cells)
            log({"step": "weekly_file_xlsx_schema", "zip_entries": len(names),
                 "sheet_names": sheets, "row_count": row_count,
                 "first_rows": first_rows})
        except Exception as exc:
            log({"step": "weekly_file_xlsx_schema", "error": f"{type(exc).__name__}: {exc}"})
    elif body:
        log({"step": "weekly_file_kind", "magic": body[:8].hex(),
             "is_pdf": body[:4] == b"%PDF"})

# --- Step 6: Ghana control (reopen condition (a)) ------------------------------
gh = fetch("https://data.gov.gh/")
gh.pop("body", None)
log({"step": "data_gov_gh", **{k: v for k, v in gh.items() if k not in ("body", "body_head")}})

# --- finalize ------------------------------------------------------------------
summary["totals"] = {"requests": state["requests"], "bytes_downloaded": state["bytes"],
                     "elapsed_s": round(time.time() - START, 1)}
summary["deadline_hit"] = time.time() >= DEADLINE
try:
    with open("/output/summary.json", "w") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print("SUMMARY_WRITTEN", flush=True)
    sys.exit(0)
except Exception as exc:
    print(f"SUMMARY_WRITE_FAILED {type(exc).__name__}: {exc}", flush=True)
    sys.exit(1)
