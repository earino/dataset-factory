#!/usr/bin/env python3
"""Portal probe for ns-bwa-advisory-lift-duration (discovery, 2026-10-27).

Reproduces: locating the Nova Scotia Boil Water Advisories package on the
open.canada.ca CKAN (anonymous), reading its record (licence id, resources,
grain-documenting notes), and the sibling-channel negatives:
- NL register header (bounded 6 KiB range read) - no lift date column
- (MB/QC/ECCC negatives were read via package_show the same way; their ids are
  printed by the query for re-checking)

No bulk downloads. Aggregate metadata only.
"""
import json
import urllib.request
import urllib.parse

UA = {"User-Agent": "scout-discovery/1.0 (dataset-factory research)"}
CKAN = "https://open.canada.ca/data/en/api/3/action"


def get_json(url, timeout=60):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            data = json.loads(r.read())
            return data if isinstance(data, dict) else {"error": "unexpected shape"}
    except Exception as e:
        return {"error": repr(e)[:150]}


def main():
    out = {}
    res = get_json(f"{CKAN}/package_search?" + urllib.parse.urlencode(
        {"q": "Boil Water Advisories", "rows": 20}))
    hits = []
    ns_id = None
    results = res.get("result") or {}
    for p in results.get("results", []):
        if not isinstance(p, dict):
            continue
        org = p.get("organization")
        org_name = org.get("name") if isinstance(org, dict) else org
        if org_name in ("ns-ne", "nl-tnl", "mb", "qc", "ec"):
            hits.append({"org": org_name, "id": p.get("id"), "title": p.get("title", "")[:80]})
            if org_name == "ns-ne":
                ns_id = p.get("id")
    out["portal_hits"] = hits

    if ns_id:
        res = get_json(f"{CKAN}/package_show?" + urllib.parse.urlencode({"id": ns_id}))
        p = res.get("result") or {}
        if isinstance(p, dict):
            out["ns_package"] = {
                "id": ns_id, "title": p.get("title"),
                "license_id": p.get("license_id"),
                "notes": p.get("notes"),
                "modified": p.get("metadata_modified"),
                "resources": [{"fmt": r.get("format"), "url": (r.get("url") or "")[:120]}
                              for r in p.get("resources", []) if isinstance(r, dict)],
            }

    # NL sibling: bounded range read of the register header (no lift column)
    req = urllib.request.Request(
        "https://opendata.gov.nl.ca/public/opendata/filedownload/?file-id=17146",
        headers={**UA, "Range": "bytes=0-6143"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            head = r.read(2048).decode("utf-8", "replace")
        out["nl_register_header"] = head.split("\r\n")[0]
        out["nl_has_lift_date_column"] = "RESCIND" in head.upper() or "REMOVED" in head.upper() or "LIFT" in head.upper()
    except Exception as e:
        out["nl_register_header"] = f"error: {e!r:.150}"

    print(json.dumps(out, indent=1, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
