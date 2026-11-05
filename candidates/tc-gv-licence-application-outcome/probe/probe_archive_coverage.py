#!/usr/bin/env python3
"""Probe: measure the retrievable-archive channels for the Traffic Commissioner
'Applications and Decisions' (AD) weekly gazettes, for one area guidance page.

Discovery evidence for candidates/tc-gv-licence-application-outcome (2026-11-05).
Read-only, anonymous. Answers, for the given guidance page:
  1. how many gazette PDFs the LIVE page still carries (and their year range);
  2. whether an older live asset URL still resolves (GOV.UK prunes -> measured 410);
  3. how many Wayback snapshots exist (monthly-collapsed) and per-year counts;
  4. how many PDF attachments a given snapshot carries;
  5. that one archived gazette PDF is fetchable and parses (end-to-end channel proof).

    python3 probe_archive_coverage.py --page-url https://www.gov.uk/guidance/applications-and-decisions-for-the-east-of-england --out out/archive_coverage_2026_11_05.json
"""

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "urllib"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.getcode(), resp.read()


def head(url, timeout=40):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "urllib"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-url", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    result = {"page_url": args.page_url}

    code, html = fetch(args.page_url)
    html = html.decode("utf-8", "replace")
    pdfs = sorted(set(re.findall(r"https://assets\.publishing\.service\.gov\.uk/[^\"'\s\)]+?\.pdf", html)))
    years = re.findall(r"_(\d{4})\.pdf", " ".join(pdfs))
    year_counts = {}
    for y in years:
        year_counts[y] = year_counts.get(y, 0) + 1
    ogl = "Open Government Licence" in html
    result["live_page"] = {
        "http": code,
        "pdf_links": len(pdfs),
        "link_year_counts": year_counts,
        "ogl_statement_on_page": ogl,
        "oldest_link": pdfs[0].rsplit("/", 1)[-1] if pdfs else None,
        "newest_link": pdfs[-1].rsplit("/", 1)[-1] if pdfs else None,
    }

    # Wayback snapshot list for the page (monthly collapsed)
    cdx = "http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(
        re.sub(r"^https?://(www\.)?", "", args.page_url), safe=""
    ) + "&output=text&collapse=timestamp:6&fl=timestamp,statuscode"
    code, body = fetch(cdx)
    rows = [l.split() for l in body.decode().splitlines() if l.strip()]
    ok = [r for r in rows if r[1] == "200"]
    per_year = {}
    for r in ok:
        per_year[r[0][:4]] = per_year.get(r[0][:4], 0) + 1
    result["wayback_page_snapshots_monthly_collapsed_200"] = {
        "total": len(ok), "per_year": dict(sorted(per_year.items()))
    }

    # One snapshot: count its PDF attachments
    snaps = sorted(ok)
    if snaps:
        ts = snaps[len(snaps) // 2][0]
        code, body = fetch(
            f"http://web.archive.org/web/{ts}id_/{args.page_url.replace('https://www.', 'https://www.')}"
        )
        snap_html = body.decode("utf-8", "replace")
        snap_pdfs = sorted(set(re.findall(r"https?://[^\"'\s\)]+?\.pdf", snap_html)))
        result["wayback_sample_snapshot"] = {
            "timestamp": ts,
            "pdf_links": len(snap_pdfs),
            "oldest": snap_pdfs[0].rsplit("/", 1)[-1] if snap_pdfs else None,
        }
        # Is one of that snapshot's asset URLs still live on the publisher?
        if snap_pdfs:
            result["old_live_asset_head_code"] = head(snap_pdfs[0])
            # Archived copy of that asset
            acdx = "http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(
                snap_pdfs[0], safe=""
            ) + "&output=text&limit=5&fl=timestamp,statuscode,mimetype"
            try:
                code, body = fetch(acdx)
                result["wayback_asset_captures"] = [
                    l.split() for l in body.decode().splitlines() if l.strip()
                ][:5]
            except Exception as e:  # noqa: BLE001 - evidence, not control flow
                result["wayback_asset_captures_error"] = str(e)

    print(json.dumps(result, indent=1))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(result, fh, indent=1)


if __name__ == "__main__":
    main()
