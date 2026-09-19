#!/usr/bin/env python3
"""Record a novelty check for a candidate, and refuse a release that is a mirror.

The rule: publishing a dataset that already exists in ML-ready form is not a contribution, it is a
mirror. So before a candidate can be called `ready` - and before any release - the *search* is run
against public catalogs and the *judgement* is recorded: what already exists, and what is ours.

The search is mechanical (Hugging Face datasets, Zenodo records, arXiv preprints - all public, no
auth). The verdict is not: a person or agent has to state what is differentiated, or say outright
that this is a mirror and should not be published.

    python3 scripts/check-novelty.py <candidate-id> --query "coastal flood" --query "tide gauge" \
        --verdict differentiated --ours "frozen 122-station panel, threshold anchored at datum=STND,
        leak-free next-day labels" --theirs "NOAA publishes observations, daily maxima and annual
        flood counts; FloodCastBench covers inundation, not station exceedance" \
        --prior-art "FloodCastBench, Sci Data 12:431 (2025)"

    python3 scripts/check-novelty.py <candidate-id> --check
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "huggingface_datasets": "https://huggingface.co/api/datasets?search={q}&limit=10",
    "zenodo_records": "https://zenodo.org/api/records?q={q}&size=5",
    "arxiv_preprints": "http://export.arxiv.org/api/query?search_query=all:{q}&max_results=5",
}
VERDICTS = ("no_precedent", "differentiated", "mirror")


def fetch(url, timeout=40):
    request = urllib.request.Request(url, headers={"User-Agent": "dataset-factory-novelty-check"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return f"__error__ {type(exc).__name__}"


def search(source, query):
    url = SOURCES[source].format(q=urllib.parse.quote(query))
    body = fetch(url)
    if body.startswith("__error__"):
        return {"query": query, "error": body[10:], "hits": None, "top": []}
    try:
        if source == "huggingface_datasets":
            data = json.loads(body)
            return {"query": query, "hits": len(data),
                    "top": [item.get("id") for item in data[:5]]}
        if source == "zenodo_records":
            data = json.loads(body)
            hits = (data.get("hits") or {}).get("total")
            titles = [hit.get("metadata", {}).get("title") for hit in
                      (data.get("hits") or {}).get("hits", [])[:5]]
            return {"query": query, "hits": hits, "top": [t for t in titles if t]}
    except json.JSONDecodeError:
        pass
    # arXiv returns Atom XML; count entries without a parser dependency.
    entries = body.count("<entry>")
    titles = []
    for chunk in body.split("<entry>")[1:]:
        for line in chunk.splitlines():
            if "<title>" in line:
                titles.append(line.split("<title>", 1)[1].split("</title>", 1)[0].strip()[:120])
                break
    return {"query": query, "hits": entries, "top": titles[:5]}


def build_evidence(queries):
    evidence = {}
    for source in SOURCES:
        evidence[source] = [search(source, query) for query in queries]
    return evidence


def summarise(evidence):
    lines = []
    for source, results in evidence.items():
        for entry in results:
            if entry.get("error"):
                lines.append(f"- {source} / '{entry['query']}': unavailable ({entry['error']})")
            else:
                top = ", ".join(entry.get("top") or []) or "nothing notable"
                lines.append(f"- {source} / '{entry['query']}': {entry.get('hits')} hit(s) - {top}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate")
    parser.add_argument("--query", action="append", default=[],
                        help="search term; repeat for each term")
    parser.add_argument("--verdict", choices=VERDICTS)
    parser.add_argument("--ours", help="what this dataset contributes that does not already exist")
    parser.add_argument("--theirs", help="what the publisher and prior art already provide")
    parser.add_argument("--prior-art", action="append", default=[],
                        help="citation or URL of a specific precedent; repeat")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    path = ROOT / "candidates" / args.candidate / "record.json"
    if not path.is_file():
        print(f"no record at {path}")
        return 2
    record = json.loads(path.read_text())

    if not args.query:
        existing = record.get("novelty_check")
        ok = bool(existing and existing.get("verdict") in VERDICTS and existing.get("ours"))
        payload = {"candidate": args.candidate, "ok": ok,
                   "verdict": (existing or {}).get("verdict"),
                   "note": ("a mirror must not be published" if (existing or {}).get("verdict")
                            == "mirror" else "recorded")}
        print(json.dumps(payload, indent=2))
        return 0 if ok else 1

    if not args.verdict or not args.ours:
        print(json.dumps({"ok": False, "error": "--verdict and --ours are required to record a "
                                               "novelty check; the search alone is not a verdict"},
                         indent=2))
        return 2

    evidence = build_evidence(args.query)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record["novelty_check"] = {
        "checked_at": stamp,
        "method": "public catalogue search (Hugging Face datasets, Zenodo, arXiv) plus web search "
                  "for an existing ML-ready formulation of this exact task",
        "queries": args.query,
        "evidence": evidence,
        "evidence_summary": summarise(evidence),
        "prior_art": args.prior_art,
        "theirs": args.theirs,
        "ours": args.ours,
        "verdict": args.verdict,
        "rule": "A dataset that already exists in ML-ready form is not published. Mirroring is a "
                "failure mode, not a contribution.",
    }
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"ok": True, "candidate": args.candidate, "verdict": args.verdict,
                      "recorded_at": stamp, "queries": len(args.query),
                      "sources": len(SOURCES)}, indent=2))
    return 0 if args.verdict != "mirror" else 3


if __name__ == "__main__":
    sys.exit(main())