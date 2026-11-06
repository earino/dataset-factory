#!/usr/bin/env python3
"""Discovery probe: recover the 2021-22 and 2022-23 outbreak-season England
premises cases from UK Government Web Archive snapshots of the gov.uk
notifiable-animal-disease case listing, because the live listing only reaches
back to September 2022.

The live listing is the current state; archived snapshots are dated vintages.
Each archived page is fetched page-by-page until its declared count is covered,
entries are deduplicated by URL path across snapshots, and per-season counts,
county coverage and positive county-weeks are computed from each entry's
Opened date.

Writes probe_archived_listings_result.json next to this script.

    python3 candidates/defra-avian-influenza-spillover/probe_archived_listings.py
"""

import datetime as dt
import json
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe_archived_listings_result.json"

REPLAY = "https://webarchive.nationalarchives.gov.uk/ukgwa/{ts}mp_/https://www.gov.uk/animal-disease-cases-england{q}"
SNAPSHOTS = [
    "20220301120000",
    "20220615120000",
    "20220715120000",
    "20220815120000",
    "20220915120000",
    "20221015120000",
    "20221215120000",
    "20240106010250",
]
# The publisher's own "previous cases" pointer (read 2026-11-06 on the latest
# situation page) is the 20240106010250 snapshot; the rest are nearest-snapshot
# resolutions of evenly spaced probe timestamps.

CARD_RE = re.compile(
    r'<li class="gem-c-document-list__item[^"]*">(.*?)(?=<li class="gem-c-document-list__item|</ul>)',
    re.S,
)
TITLE_RE = re.compile(r'<a[^>]*href="([^"]*animal-disease-cases-england/[^"]+)"[^>]*>(.*?)</a>', re.S)
ATTR_RE = re.compile(r'<li class="gem-c-document-list__attribute">\s*([A-Za-z ]+?):\s*(.*?)</li>', re.S)
TIME_RE = re.compile(r'<time datetime="([^"]+)"')
COUNT_RE = re.compile(r">([0-9,]+) cases<")
ZONE_WORDS = ("prevention zone", "control zone", "controlled zone", "monitoring", "restriction zone")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dataset-factory-discovery/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s.replace("&amp;", "&")).strip()


def county_from_title(title):
    t = re.sub(r"\(AIV\s*[^)]*\)", "", title)
    t = re.sub(r"\(\s*20\d\d\s*\)", "", t)
    t = re.sub(r"^Bird flu:\s*", "", t).strip()
    parts = [p.strip() for p in t.split(",")]
    return parts[-1] if len(parts) >= 2 else ""


def season_of(d):
    y = d.year if d.month >= 10 else d.year - 1
    return "%d-%02d" % (y, (y + 1) % 100)


def parse_page(html):
    cards = CARD_RE.findall(html)
    entries = []
    declared = COUNT_RE.search(html)
    for card in cards:
        m = TITLE_RE.search(card)
        if not m:
            continue
        href, raw_title = m.group(1), strip_tags(m.group(2))
        if "bird-flu" not in href and "Bird flu" not in raw_title:
            continue
        attrs = {}
        for label, value in ATTR_RE.findall(card):
            tm = TIME_RE.search(value)
            attrs[label.strip()] = strip_tags(tm.group(1)) if tm else strip_tags(value)
        entries.append(
            {
                "url_path": href.split("animal-disease-cases-england/")[-1],
                "title": raw_title,
                "is_zone_entry": any(w in raw_title.lower() for w in ZONE_WORDS),
                "strain": attrs.get("Virus strain", ""),
                "opened": attrs.get("Opened", ""),
            }
        )
    return entries, (declared.group(1) if declared else "?")


def main():
    t_start = time.time()
    by_path = {}
    requests = 0
    bytes_fetched = 0
    snapshots_seen = {}
    for ts in SNAPSHOTS:
        page = 1
        while page < 12:
            q = "" if page == 1 else "?page=%d" % page
            url = REPLAY.format(ts=ts, q=q)
            try:
                html, final_url = fetch(url)
            except Exception as e:
                print(ts, "page", page, "FAILED:", e)
                break
            requests += 1
            bytes_fetched += len(html)
            if page == 1:
                m = re.search(r"/ukgwa/(\d{14})mp_/", final_url)
                resolved = m.group(1) if m else ts
                if resolved in snapshots_seen:
                    print(ts, "->", resolved, "already probed; skipping")
                    break
                snapshots_seen[resolved] = True
                print(ts, "-> resolved snapshot", resolved)
            entries, declared = parse_page(html)
            if not entries:
                break
            new = 0
            bf = 0
            for e in entries:
                if e["is_zone_entry"]:
                    continue
                bf += 1
                if e["url_path"] not in by_path:
                    by_path[e["url_path"]] = e
                    new += 1
            print(
                "  page %d: %d cards, %d bird-flu (%d new), page declares %s cases"
                % (page, len(entries), bf, new, declared)
            )
            # Keep paging until a page carries no more cases (the archived
            # pages hold 49-50 cards, so a count-based break truncates).
            try:
                if bf == 0 or (declared.isdigit() and int(declared.replace(",", "")) <= 50 * page):
                    break
            except AttributeError:
                break
            page += 1
            time.sleep(0.5)
        time.sleep(0.5)

    cases = []
    for e in by_path.values():
        e["county"] = county_from_title(e["title"])
        try:
            d = dt.date.fromisoformat(e["opened"])
            e["opened_date"] = d.isoformat()
            e["season"] = season_of(d)
            iso = d.isocalendar()
            e["iso_week"] = "%d-W%02d" % (iso[0], iso[1])
            cases.append(e)
        except ValueError:
            e["opened_date"], e["season"], e["iso_week"] = "", "", ""
            cases.append(e)

    per_season = {}
    for e in cases:
        s = e.get("season") or "no-date"
        a = per_season.setdefault(
            s, {"cases": 0, "counties": set(), "county_weeks": set(), "no_date": 0}
        )
        a["cases"] += 1
        if e["opened_date"]:
            a["counties"].add(e["county"])
            a["county_weeks"].add((e["county"], e["iso_week"]))
        else:
            a["no_date"] += 1
    for s, a in per_season.items():
        a["distinct_counties"] = len(a["counties"])
        a["positive_county_weeks"] = len(a["county_weeks"])
        a.pop("counties")
        a.pop("county_weeks")

    result = {
        "probed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "replay_pattern": "https://webarchive.nationalarchives.gov.uk/ukgwa/<ts>mp_/https://www.gov.uk/animal-disease-cases-england[?page=N]",
        "snapshots_resolved": sorted(snapshots_seen),
        "requests": requests,
        "bytes_fetched": bytes_fetched,
        "wall_seconds": round(time.time() - t_start, 1),
        "unioned_premises_entries": len(by_path),
        "per_season": per_season,
        "per_entry": [
            {k: e.get(k) for k in ("title", "county", "opened_date", "season", "iso_week")}
            for e in sorted(cases, key=lambda x: x.get("opened_date") or "")
        ],
    }
    OUT.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print("DONE unioned entries:", len(by_path), "->", OUT.name)


if __name__ == "__main__":
    main()
