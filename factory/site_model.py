"""Release-to-site contract. Offline; only a small, explicit public projection leaves the factory."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

from .common import FactoryError

SCHEMA = 1
SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_INPUT = 256 * 1024


def require(condition, message):
    if not condition:
        raise FactoryError(message)


def encoded(value):
    return quote(value, safe="")


def dump(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def read(path):
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), f"Expected regular input file: {path}")
    require(path.stat().st_size <= MAX_INPUT, f"Metadata exceeds 256 KiB: {path}")
    return json.loads(path.read_text())


def slug(value):
    require(isinstance(value, str) and SLUG.fullmatch(value) and value not in (".", ".."),
            "Dataset names, tags and repository components must be safe path components")
    return value


def repository(value):
    require(isinstance(value, str), "Repository must be owner/name")
    if value.startswith("https://github.com/"):
        value = value[len("https://github.com/"):]
    parts = value.split("/")
    require(len(parts) == 2, "Repository must be owner/name or its canonical GitHub URL")
    for part in parts:
        slug(part)
    require(not parts[1].endswith(".git"), "Use the repository name without .git")
    return value


def pages_url(repo):
    owner, name = repository(repo).split("/")
    require(name.lower() != f"{owner.lower()}.github.io", "The account root Pages site is reserved")
    return f"https://{owner.lower()}.github.io/{name}/"


def text_field(value, name, limit=5000):
    require(isinstance(value, str) and 0 < len(value) <= limit, f"Missing or oversized text: {name}")
    return value


def flatten_splits(raw):
    """One flat {name: {rows, positives}} view of a manifest's splits.

    A dataset with levels carries its splits per level. The record and the published manifest must
    be read through the same rule, or the publish check compares two different shapes and refuses a
    correct release - which is exactly what happened: `project` flattened by level and
    `check_manifest` did not.
    """
    if raw and all(isinstance(v, dict) and "rows" not in v for v in raw.values()):
        return {f"{level}-{split}": entry
                for level, per_level in sorted(raw.items())
                for split, entry in sorted(per_level.items())}
    return dict(raw)


def config_names(raw):
    """The config names a manifest's splits are grouped by, in order. Empty for a single-config set.

    A dataset with levels needs its config named in a loading command; a flat one must not be given
    a config it does not have. Both the Hub card and the dataset page print that command, so both
    derive the names through this one rule rather than each guessing.
    """
    if raw and all(isinstance(v, dict) and "rows" not in v for v in raw.values()):
        return sorted(raw)
    return []


def project(package, editorial, config):
    """Construct a renderer-independent record. Never export whole manifests or job records."""
    package = Path(package)
    m, d = read(package / "MANIFEST.json"), read(package / "DESTINATIONS.json")
    require(config.get("schema_version") == SCHEMA and editorial.get("schema_version") == SCHEMA,
            "Unsupported site configuration or editorial schema")
    require(config.get("hosting") == "github-project-pages", "Only project Pages hosting is configured")
    catalog = repository(config["catalog_repository"])
    gh = repository(m["repository"])
    require(catalog != gh, "Catalogue and dataset need separate repositories")
    name, tag, artifact = slug(m["dataset"]), slug(m["release_tag"]), m["artifact_version"]
    require(bool(SHA.fullmatch(str(artifact))), "Invalid artifact version")
    require(d.get("release_tag") == tag and d.get("artifact_version") == artifact,
            "Destination evidence describes a different release or artifact")
    dest = d["destinations"]
    for platform, key in (("github", "release_tag"), ("huggingface", "revision")):
        entry = dest[platform]
        require(entry.get("verified") is True and entry.get(key) == tag,
                f"{platform}: this release has not been verified")
    require(repository(dest["github"]["repo"]) == gh, "GitHub destination differs from manifest")
    hf = repository(dest["huggingface"]["repo"])
    qualification = m["qualification"]
    require(qualification.get("artifact_version") == artifact and
            str(qualification.get("result", "")).startswith("PASSED"),
            "A passing qualification for this exact artifact is required")
    # Verify only the small package files we use. No CSV reads and no model work.
    for filename in ("README.md", "LICENSE.md", "RELEASE_NOTES.md"):
        path = package / filename
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_INPUT,
                f"Missing or oversized package document: {filename}")
        require(digest(path.read_bytes()) == m["package_files"].get(filename),
                f"Package document changed since its manifest: {filename}")
    urls = {
        "catalog": pages_url(catalog), "website": pages_url(gh),
        "version": pages_url(gh) + f"versions/{encoded(tag)}/",
        "github": "https://github.com/" + gh,
        "github_release": f"https://github.com/{gh}/releases/tag/{encoded(tag)}",
        "huggingface": "https://huggingface.co/datasets/" + hf,
        "huggingface_version": f"https://huggingface.co/datasets/{hf}/tree/{encoded(tag)}",
    }
    assets = {}
    for logical, item in sorted(m["assets"].items()):
        filename = slug(item["asset_name"])
        require(SHA.fullmatch(str(item["sha256"])) and type(item["bytes"]) is int and item["bytes"] >= 0,
                "Asset needs a SHA-256 digest and non-negative byte count")
        require(m["files"].get(logical) == {"bytes": item["bytes"], "sha256": item["sha256"]},
                "Manifest file and asset digests disagree")
        require(logical in dest["github"].get("files_verified", []), "GitHub verification omits an asset")
        # The Hub path comes from the manifest when the dataset declares one. A level-structured
        # dataset does not follow the flat data/<asset>.csv rule, and assuming it did meant the
        # website could never be built for such a release. The flat rule remains the default.
        hf_path = (m.get("hub_paths") or {}).get(logical) or (
            f"data/{filename}" if filename.endswith(".csv") else filename)
        require(hf_path in dest["huggingface"].get("files_verified", []), "Hub verification omits an asset")
        assets[filename] = {"bytes": item["bytes"], "sha256": item["sha256"], "hf_path": hf_path,
                            "download": f"https://github.com/{gh}/releases/download/{encoded(tag)}/{encoded(filename)}"}
    require(bool(assets), "No release assets")
    # A dataset with levels carries its splits per level; the page shows every split of every level
    # rather than silently rendering only the first, and a flat manifest is untouched.
    raw_splits = flatten_splits(m["splits"])
    splits = {}
    for key, entry in raw_splits.items():
        slug(key)
        require(type(entry["rows"]) is int and entry["rows"] > 0, "Split rows must be positive integers")
        splits[key] = {"rows": entry["rows"]}
        if "positives" in entry:
            positives = entry["positives"]
            require(type(positives) is int and 0 <= positives <= entry["rows"], "Invalid positive count")
            splits[key]["positives"] = positives
    source = m["source"]
    require(source["landing_page"].startswith("https://"), "Source link must be HTTPS")
    terms = m["licenses"]
    licenses = {key: text_field(terms[key]["spdx"], key, 100)
                for key in ("code", "data_compilation", "source_data")}
    licenses.update({key: text_field(terms["source_data"][key], key)
                     for key in ("attribution", "citation")})
    licenses["compilation_scope"] = text_field(terms["data_compilation"]["scope"], "compilation scope")
    post = editorial["post"]
    require(isinstance(post["paragraphs"], list) and 0 < len(post["paragraphs"]) <= 20, "Post needs paragraphs")
    require(isinstance(editorial["limitations"], list) and len(editorial["limitations"]) <= 20,
            "Limitations must be a short list")
    date.fromisoformat(editorial["release_date"])
    revision = editorial.get("site_revision", 1)
    require(type(revision) is int and revision >= 1, "site_revision must be a positive integer")
    baseline = m.get("baseline") or {}
    # A single-level release records one contract; a dataset with levels records one per level. The
    # page reports whichever shape the manifest actually has instead of assuming the first's.
    contract = baseline.get("contract") or {}
    level_metrics = {}
    for level, data in sorted((baseline.get("artifact") or {}).get("levels", {}).items()):
        if isinstance(data.get("eval_auc"), (int, float)):
            level_metrics[level] = {"eval_auc": float(data["eval_auc"]),
                                    "contract_ok": data.get("contract_ok") is True}
    metrics = {}
    if contract.get("contract_ok") is True and "eval_auc_from_validate_py" in contract:
        auc = float(contract["eval_auc_from_validate_py"])
        require(0 <= auc <= 1, "Invalid baseline AUC")
        metrics["Evaluation ROC AUC"] = auc
    record = {
        "schema_version": SCHEMA, "site_revision": revision, "dataset": name, "release_tag": tag, "artifact_version": artifact,
        "github_repository": gh, "hf_repository": hf, "urls": urls,
        "title": text_field(editorial["title"], "title", 160),
        "summary": text_field(editorial["summary"], "summary", 1000),
        "task_type": text_field(editorial["task_type"], "task type", 100),
        "domain": text_field(editorial["domain"], "domain", 100), "release_date": editorial["release_date"],
        "post": {"title": text_field(post["title"], "post title", 200),
                 "paragraphs": [text_field(p, "post paragraph") for p in post["paragraphs"]]},
        "limitations": [text_field(p, "limitation") for p in editorial["limitations"]],
        "assets": assets, "splits": splits, "licenses": licenses,
        # Named so the page can print a loading command that runs: a config-less call against a
        # multi-config dataset raises, and the page is where most readers copy the command from.
        "configs": config_names(m["splits"]),
        "source": {"name": source["name"], "url": source["landing_page"]},
        "qualification": {"gate_version": qualification["gate_version"], "result": qualification["result"]},
        "baseline": {"metrics": metrics, "scope": baseline.get("scope", m.get("scope", ""))},
    }
    record["record_sha256"] = digest(dump(record))
    return record


START, END = "<!-- dataset-factory:links -->", "<!-- /dataset-factory:links -->"


def check_manifest(record, manifest):
    """Check what a remote pinned manifest says, as well as the provider's asset digests."""
    require(manifest.get("release_tag") == record["release_tag"] and
            manifest.get("artifact_version") == record["artifact_version"], "Pinned manifest identifies another release")
    splits = {k: {field: v[field] for field in ("rows", "positives") if field in v}
              for k, v in flatten_splits(manifest["splits"]).items()}
    require(splits == record["splits"], "Pinned manifest split counts differ")
    require(config_names(manifest["splits"]) == record.get("configs", []),
            "Pinned manifest config names differ")
    assets = {v["asset_name"]: {k: v[k] for k in ("bytes", "sha256")} for v in manifest["assets"].values()}
    require(assets == {name: {k: v[k] for k in ("bytes", "sha256")} for name, v in record["assets"].items()},
            "Pinned manifest assets differ")
    terms = manifest["licenses"]
    require(all(terms[k]["spdx"] == record["licenses"][k] for k in ("code", "data_compilation", "source_data")),
            "Pinned manifest licence terms differ")
    require(all(terms["source_data"][k] == record["licenses"][k] for k in ("attribution", "citation")),
            "Pinned manifest attribution or citation differs")


def links(record):
    u = record["urls"]
    return (f"{START}\n**Dataset Factory · {record['release_tag']}**\n\n"
            f"[Dataset website]({u['version']}) · [GitHub release]({u['github_release']}) · "
            f"[Hugging Face]({u['huggingface_version']}) · [Catalogue]({u['catalog']})\n\n"
            f"Artifact: {record['artifact_version']}\n{END}")


def linked_readme(original, record):
    require(original.count(START) == original.count(END) and original.count(START) <= 1,
            "README contains ambiguous managed navigation markers")
    if START in original:
        begin, after = original.split(START, 1)
        _, tail = after.split(END, 1)
        return begin + links(record) + tail
    # Append so that Hugging Face's YAML header and author-written documentation are preserved.
    return original.rstrip() + "\n\n" + links(record) + "\n"
