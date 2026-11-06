#!/usr/bin/env python3
"""Discovery probe: extract every bird-flu entry from the gov.uk England
notifiable-animal-disease case listing (public HTML finder) and compute the
season-level aggregates that decide split capacity.

Questions this answers:
- how many entries are per-premises cases (AIV ids) vs zone/regulatory entries
  (the provenance mix of this listing),
- opened-date and county distribution of premises cases per Oct-Sep outbreak
  season,
- how many county-weeks per season carry at least one new premises case.

Read-only against the publisher. Writes probe_case_listing_result.json next to
this script (compact aggregates + per-entry rows). Re-runnable.

    python3 candidates/defra-avian-influenza-spillover/probe_case_listing.py
"""

import datetime as dt
import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://www.gov.uk/animal-disease-cases-england?disease_type%5B%5D=bird-flu&page={}"
HERE = Path(__file__).resolve().parent
OUT = HERE / "probe_case_listing_result.json"

CARD_RE = re.compile(
    r'<li class="gem-c-document-list__item[^"]*">(.*?)(?=<li class="gem-c-document-list__item|</ul>)',
    re.S,
)
TITLE_RE = re.compile(r'<a[^>]*href="(/animal-disease-cases-england/[^"]+)"[^>]*>(.*?)</a>', re.S)
ATTR_RE = re.compile(r'<li class="gem-c-document-list__attribute">\s*([A-Za-z ]+?):\s*(.*?)</li>', re.S)
TIME_RE = re.compile(r'<time datetime="([^"]+)"')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dataset-factory-discovery/1.0"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read().decode("utf-8", "replace")
    return data, len(data), time.time() - t0


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s.replace("&amp;", "&")).strip()


def county_from_title(title):
    t = re.sub(r"\(AIV\s*[^)]*\)", "", title)
    t = re.sub(r"^Bird flu:\s*", "", t).strip()
    parts = [p.strip() for p in t.split(",")]
    return parts[-1] if len(parts) >= 2 else ""


def season_of(d):
    y = d.year if d.month >= 10 else d.year - 1
    return "%d-%02d" % (y, (y + 1) % 100)


def main():
    entries = []
    pages = 0
    total_bytes = 0
    t_start = time.time()
    for page in range(1, 60):
        html, nbytes, _ = fetch(BASE.format(page))
        pages += 1
        total_bytes += nbytes
        cards = CARD_RE.findall(html)
        if not cards:
            break
        before = len(entries)
        for card in cards:
            m = TITLE_RE.search(card)
            if not m:
                continue
            href, raw_title = m.group(1), strip_tags(m.group(2))
            attrs = {}
            for label, value in ATTR_RE.findall(card):
                tm = TIME_RE.search(value)
                attrs[label.strip()] = strip_tags(tm.group(1)) if tm else strip_tags(value)
            entries.append(
                {
                    "url_path": href,
                    "title": raw_title,
                    "type": attrs.get("type", ""),
                    "zone_restriction": attrs.get("Control zone restriction", ""),
                    "zone_type": attrs.get("Control zone type", ""),
                    "strain": attrs.get("Virus strain", ""),
                    "opened": attrs.get("Opened", ""),
                    "closed": attrs.get("Closed", ""),
                }
            )
        print("page %d: %d cards (%d total)" % (page, len(cards), len(entries)))
        if len(entries) == before:
            break
        time.sleep(0.4)

    premises, non_premises = [], []
    for e in entries:
        # Premises cases carry an outbreak id: current "(AIV 2026/23)" or 2022-era
        # "(2022/73)" / "(SOS AIV 2022/19)". Zone/regulatory entries carry none.
        e["is_premises_case"] = "(AIV" in e["title"] or bool(
            re.search(r"\([^)]*20\d\d/\d+\)", e["title"])
        )
        if e["is_premises_case"]:
            e["county"] = county_from_title(e["title"])
            try:
                d = dt.date.fromisoformat(e["opened"])
                e["opened_date"] = d.isoformat()
                e["season"] = season_of(d)
                iso = d.isocalendar()
                e["iso_week"] = "%d-W%02d" % (iso[0], iso[1])
            except ValueError:
                e["opened_date"], e["season"], e["iso_week"] = "", "", ""
            premises.append(e)
        else:
            non_premises.append(e)

    def agg_season(rows):
        out = {}
        for e in rows:
            s = e.get("season") or "unknown"
            a = out.setdefault(
                s,
                {"cases": 0, "counties": set(), "county_weeks": set(), "no_date": 0},
            )
            a["cases"] += 1
            if e["opened_date"]:
                a["counties"].add(e["county"])
                a["county_weeks"].add((e["county"], e["iso_week"]))
            else:
                a["no_date"] += 1
        for s, a in out.items():
            a["distinct_counties"] = len(a.pop("counties"))
            a["positive_county_weeks"] = len(a.pop("county_weeks"))
        return out

    strain_mix = {}
    for e in premises:
        strain_mix[e["strain"]] = strain_mix.get(e["strain"], 0) + 1

    non_prem_kinds = {}
    for e in non_premises:
        k = "prevention zone" if "prevention zone" in e["title"].lower() else (
            "control zone/area" if ("control" in e["title"].lower() or "area" in e["title"].lower())
            else "other"
        )
        non_prem_kinds[k] = non_prem_kinds.get(k, 0) + 1

    result = {
        "probed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_url": "https://www.gov.uk/animal-disease-cases-england?disease_type%5B%5D=bird-flu",
        "listing_total_declared": 340,
        "pages_fetched": pages,
        "requests": pages,
        "bytes_fetched": total_bytes,
        "wall_seconds": round(time.time() - t_start, 1),
        "entries_total": len(entries),
        "premises_cases": len(premises),
        "non_premises_entries": len(non_premises),
        "non_premises_kinds": non_prem_kinds,
        "premises_strain_mix": strain_mix,
        "per_season": agg_season(premises),
        "per_entry": [
            {
                k: e[k]
                for k in ("title", "county", "opened_date", "season", "iso_week", "strain")
            }
            for e in premises
        ],
        "non_premises_titles_sample": [e["title"] for e in non_premises[:12]],
    }
    OUT.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(
        "DONE entries=%d premises=%d non-premises=%d -> %s"
        % (len(entries), len(premises), len(non_premises), OUT.name)
    )


if __name__ == "__main__":
    main()
