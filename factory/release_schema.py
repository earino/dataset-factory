"""The read contract for releases, including historical published JSON shapes.

Reading a historical release is not qualification or permission to publish it. The
row-level gate remains the only acceptance check for a constructed artifact.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
import re

from .common import FactoryError

UNKNOWN = "not recorded"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
AUC_KEYS = ("eval_auc", "train_py_eval_auc", "validate_py_eval_auc", "auc_from_train_py",
            "auc_eval_runner_measured", "eval_auc_from_train_py", "eval_auc_from_validate_py",
            "auc_from_validate_py")


class ReleaseShapeError(FactoryError):
    def __init__(self, path, field, reason):
        self.path, self.field, self.reason = str(path), field, reason
        super().__init__(f"{path}: {field}: {reason}")


def read_object(path):
    path = Path(path)
    try:
        if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
            raise ReleaseShapeError(path, "$", "expected a regular metadata file <= 2 MiB")
        value = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise ReleaseShapeError(path, "$", f"cannot read JSON ({type(exc).__name__})") from exc
    if not isinstance(value, dict):
        raise ReleaseShapeError(path, "$", "expected an object")
    return value


def _object(value, path, key):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ReleaseShapeError(path, key, "expected an object")
    return value


def as_release(value):
    """Compatibility for pure render helpers; operational callers must use load_release."""
    return value if isinstance(value, Release) else from_manifest(value, strict=False)


def record_destination(path, kind, fields, *, release_tag=None):
    """Merge one verification record, refusing corrupt existing metadata; atomically replace it."""
    path = Path(path)
    data = read_object(path) if path.exists() else {}
    normalise_destinations(data, path)
    if release_tag is not None:
        if data.get("release_tag") not in (None, release_tag):
            raise ReleaseShapeError(path, "release_tag", "destination record identifies another release")
        data["release_tag"] = release_tag
    entries = data.get("destinations") or {}
    data["destinations"] = entries
    entries[kind] = {**entries.get(kind, {}), **fields}
    normalise_destinations(data, path)
    atomic_write(path, json.dumps(data, indent=2) + "\n")


def atomic_write(path, text):
    path = Path(path)
    if path.is_symlink():
        raise ReleaseShapeError(path, "$", "refusing to replace a symlink")
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _number(value, path, key):
    try:
        if isinstance(value, bool):
            raise ValueError()
        number = float(value)
        if not math.isfinite(number) or not 0 <= number <= 1:
            raise ValueError()
        return number
    except (ValueError, TypeError, OverflowError):
        raise ReleaseShapeError(path, key, "expected a finite number in [0, 1]") from None


@dataclass(frozen=True)
class Split:
    rows: int
    positives: int | None = None
    positive_rate: float | None = None
    config: str | None = None
    name: str = ""
    evidence: str = ""

    def counts(self):
        return {"rows": self.rows, **({"positives": self.positives} if self.positives is not None else {})}


def normalise_splits(raw, path="<manifest>", field="splits") -> dict[str, Split]:
    """Flatten protocol splits, retaining config identity; never infer counts from rates."""
    if raw is None or raw == {}:
        return {}
    if not isinstance(raw, dict):
        raise ReleaseShapeError(path, field, "expected a split map")
    result = {}

    def group(entries, prefix=None):
        for name, entry in entries.items():
            key = f"{field}.{prefix + '.' if prefix else ''}{name}"
            if not isinstance(entry, dict) or "rows" not in entry:
                raise ReleaseShapeError(path, key, "missing row count (a file path is not a count)")
            rows, positives = entry["rows"], entry.get("positives")
            if type(rows) is not int or rows <= 0:
                raise ReleaseShapeError(path, key + ".rows", "expected a positive integer")
            if positives is not None and (type(positives) is not int or not 0 <= positives <= rows):
                raise ReleaseShapeError(path, key + ".positives", "expected an integer between 0 and rows")
            rate = entry.get("positive_rate")
            if rate is not None:
                rate = _number(rate, path, key + ".positive_rate")
            flat = f"{prefix}-{name}" if prefix else name
            if flat in result:
                raise ReleaseShapeError(path, key, "flattened split name collides")
            result[flat] = Split(rows, positives, rate, prefix, name, f"{path}:{key}")

    if all(isinstance(v, dict) and "rows" not in v for v in raw.values()):
        for config, entries in raw.items():
            group(entries, config)
    else:
        group(raw)
    return result


@dataclass(frozen=True)
class Baseline:
    eval_auc: float | None
    scope: str | None = None
    references: dict[str, float] = field(default_factory=dict)
    per_config: dict[str, float] = field(default_factory=dict)
    evidence: str = ""
    artifact_id: str | None = None
    narrative: str = ""

    def display(self, digits=4):
        if self.eval_auc is not None:
            value = f"{self.eval_auc:.{digits}f}"
            return f"{value} ({self.scope})" if self.scope else value
        return "; ".join(f"{name}: {auc:.{digits}f}" for name, auc in sorted(self.per_config.items())) or UNKNOWN


def normalise_baseline(raw, path="<manifest>", field="baseline") -> Baseline | None:
    if raw is None or raw == {}:
        return None
    if not isinstance(raw, dict):
        raise ReleaseShapeError(path, field, "expected an object or explicit null")
    references = {}
    refs = raw.get("references") or raw.get("reference_points") or {}
    if isinstance(refs, dict):
        refs = _object(refs.get("eval", refs), path, field + ".reference_points.eval")
        for name, value in refs.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                references[name] = _number(value, path, f"{field}.reference_points.{name}")
    persistence = raw.get("persistence_reference")
    if isinstance(persistence, dict):
        for key in ("persistence_prev_target_cited_eval_auc", "persistence_eval_auc"):
            if persistence.get(key) is not None:
                references[key] = _number(persistence[key], path, f"{field}.persistence_reference.{key}")
    artifact = _object(raw.get("artifact"), path, field + ".artifact")
    qualification = _object(raw.get("qualification_report"), path, field + ".qualification_report")
    identity = qualification.get("accepted_artifact_version") or artifact.get("artifact_version")
    if identity is not None and (not isinstance(identity, str) or
                                not re.fullmatch(r"[0-9a-f]{16,64}", identity)):
        raise ReleaseShapeError(path, field + ".qualification_report.accepted_artifact_version",
                                "expected a hexadecimal artifact digest or recorded prefix")
    narrative = raw.get("scope") or ""
    if not isinstance(narrative, str):
        raise ReleaseShapeError(path, field + ".scope", "expected text")
    per_config = {}
    levels = raw.get("per_config") or raw.get("levels") or artifact.get("levels") or {}
    for name, data in _object(levels, path, field + ".levels").items():
        value = data.get("eval_auc") if isinstance(data, dict) else data
        if value is not None:
            per_config[name] = _number(value, path, f"{field}.levels.{name}.eval_auc")
    summary = _object(raw.get("summary"), path, field + ".summary")
    if "eval_auc_median" in summary:
        configs = summary.get("configs")
        if configs is not None and (type(configs) is not int or configs <= 0):
            raise ReleaseShapeError(path, field + ".summary.configs", "expected a positive integer")
        return Baseline(_number(summary["eval_auc_median"], path, field + ".summary.eval_auc_median"),
                        f"median of {configs} configs" if configs else "suite median", references,
                        per_config, f"{path}:{field}.summary", identity, narrative)
    values = []
    for section, body in (("", raw), (".result", raw.get("result") or {}),
                          (".contract", raw.get("contract") or {}), (".artifact", artifact)):
        if not isinstance(body, dict):
            raise ReleaseShapeError(path, field + section, "expected an object")
        for key in AUC_KEYS:
            if body.get(key) is not None:
                values.append((_number(body[key], path, field + section + "." + key), section + "." + key))
    if values:
        if any(not math.isclose(v, values[0][0], abs_tol=0.00005, rel_tol=0) for v, _ in values):
            raise ReleaseShapeError(path, field, "conflicting evaluation AUCs: " + ", ".join(k for _, k in values))
        return Baseline(values[0][0], raw.get("aggregation_scope"), references, per_config,
                        f"{path}:{field}{values[0][1]}", identity, narrative)
    if per_config:
        # No max/mean/median invented by a consumer. A single measured config is labelled as such.
        if len(per_config) == 1:
            name, value = next(iter(per_config.items()))
            return Baseline(value, f"config {name}", references, per_config,
                            f"{path}:{field}.artifact.levels.{name}", identity, narrative)
        return Baseline(None, "per-config results", references, per_config,
                        f"{path}:{field}.artifact.levels", identity, narrative)
    return None


@dataclass(frozen=True)
class Destination:
    kind: str
    locator: str | None
    private: bool | None
    verified_at: str | None
    verified: bool = False
    revision: str | None = None
    files_verified: tuple[str, ...] = ()
    evidence: str = ""


def normalise_destinations(raw, path="<destinations>") -> dict[str, Destination]:
    entries = dict(_object(_object(raw, path, "$").get("destinations"), path, "destinations"))
    # Historical site receipts predate the unified destination map. Never invent a URL.
    publication = _object(raw.get("publication"), path, "publication")
    site = _object(publication.get("site"), path, "publication.site")
    if "site" not in entries and site:
        entries["site"] = {"url": site.get("version_page") or site.get("page"),
                           "verified": site.get("status") == "verified",
                           "private": False if site.get("status") == "verified" else None,
                           "verified_at": site.get("verified_at")}
    if not isinstance(entries, dict):
        raise ReleaseShapeError(path, "destinations", "expected an object")
    result = {}
    for kind, item in entries.items():
        key = "destinations." + kind
        if not isinstance(item, dict):
            raise ReleaseShapeError(path, key, "expected an object")
        for flag in ("private", "verified"):
            if item.get(flag) is not None and type(item[flag]) is not bool:
                raise ReleaseShapeError(path, key + "." + flag, "expected a boolean")
        stamp = item.get("verified_at")
        if stamp:
            try:
                datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                raise ReleaseShapeError(path, key + ".verified_at", "expected an ISO timestamp") from None
        locator = item.get("url") if kind == "site" else item.get("repo")
        if locator is not None and (not isinstance(locator, str) or not locator.strip()):
            raise ReleaseShapeError(path, key + ".locator", "expected a nonempty string")
        files = item.get("files_verified") or []
        if not isinstance(files, list) or any(not isinstance(f, str) for f in files):
            raise ReleaseShapeError(path, key + ".files_verified", "expected a list of paths")
        result[kind] = Destination(kind, item.get("url") if kind == "site" else item.get("repo"),
                                   item.get("private"), stamp, item.get("verified") is True,
                                   item.get("revision") or item.get("release_tag"),
                                   tuple(item.get("files_verified") or ()), f"{path}:{key}")
    return result


def combined_artifact_version(levels):
    joined = "\n".join(f"{name}:{data['artifact_version']}" for name, data in sorted(levels.items()))
    return hashlib.sha256(joined.encode()).hexdigest()


@dataclass(frozen=True)
class Release:
    dataset: str
    artifact_id: str | None
    tag: str | None
    splits: dict[str, Split]
    baseline: Baseline | None
    destinations: dict[str, Destination]
    licences: dict
    published: bool = False
    baseline_reason: str | None = None
    configs: dict[str, tuple[str, ...]] = field(default_factory=dict)
    disposition: str | None = None
    problems: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict, repr=False)

    @property
    def rows(self):
        return sum(s.rows for s in self.splits.values()) if self.splits else None

    @property
    def baseline_current(self):
        identity = self.baseline.artifact_id if self.baseline else None
        return not identity or bool(self.artifact_id and self.artifact_id.startswith(identity))

    @property
    def baseline_display(self):
        if not self.baseline:
            return self.baseline_reason or UNKNOWN
        text = self.baseline.display()
        return text if self.baseline_current else text + " (historical artifact; not this release)"

    def split_counts(self):
        return {name: split.counts() for name, split in self.splits.items()}

    def destination(self, kind):
        try:
            return self.destinations[kind]
        except KeyError:
            raise ReleaseShapeError(self.metadata.get("_path", "<manifest>"),
                                    "destinations." + kind, "destination not recorded") from None


def from_manifest(data, *, path="<manifest>", destinations=None, split_sources=(),
                  baseline_source=None, candidate=None, strict=True) -> Release:
    """Normalize once. Diagnostic mode retains draft facts and reports every missing prerequisite.

    Diagnostic mode is only for observation. Writers and operations use strict mode.
    Ancillary manifest fields remain available as metadata until their contracts migrate.
    """
    if not isinstance(data, dict):
        raise ReleaseShapeError(path, "$", "expected an object")
    problems = []

    def problem(key, reason):
        error = ReleaseShapeError(path, key, reason)
        if strict:
            raise error
        problems.append(str(error))

    name = data.get("dataset")
    if not isinstance(name, str) or not name:
        problem("dataset", "missing dataset name")
        name = Path(path).parent.name
    qualification = _object(data.get("qualification"), path, "qualification")
    identity = qualification.get("artifact_version") or data.get("artifact_version")
    if not isinstance(identity, str) or not SHA256.fullmatch(identity):
        problem("qualification.artifact_version", "missing SHA-256 artifact identity")
    tag = data.get("release_tag")
    if not isinstance(tag, str) or not tag:
        problem("release_tag", "missing version tag")
    splits = {}
    for raw, source, key in [(data.get("splits"), path, "splits"), *split_sources]:
        if raw is None or raw == {}:
            continue
        # A quality descriptor's path map declares layout, not row counts.
        if isinstance(raw, dict) and all(isinstance(v, str) for v in raw.values()):
            continue
        splits = normalise_splits(raw, source, key)
        if splits:
            break
    if not splits:
        problem("splits", "no recorded split row counts")
    baseline = normalise_baseline(data.get("baseline"), path)
    if baseline is None and baseline_source and "baseline" not in data:
        baseline = normalise_baseline(baseline_source[0], baseline_source[1])
    elif baseline is None and data.get("baseline") == {} and baseline_source:
        baseline = normalise_baseline(baseline_source[0], baseline_source[1])
    reason = data.get("baseline_reason")
    if baseline is None and not ("baseline" in data and data["baseline"] is None
                                 and isinstance(reason, str) and reason.strip()):
        problem("baseline", "missing evaluation result; explicit null requires baseline_reason")
    terms = data.get("licenses")
    if not isinstance(terms, dict) or not terms:
        problem("licenses", "missing licence declarations")
        terms = {}
    dest = normalise_destinations(destinations or {}, str(Path(path).with_name("DESTINATIONS.json")))
    # Some historical Hub verification records name logical artifact paths. Translate only
    # paths explicitly present in this manifest's asset map; remote checks still hash the bytes.
    if "huggingface" in dest:
        assets = _object(data.get("assets"), path, "assets")
        hub_paths = _object(data.get("hub_paths"), path, "hub_paths")
        verified = []
        for logical in dest["huggingface"].files_verified:
            asset = assets.get(logical)
            if isinstance(asset, dict) and asset.get("asset_name"):
                target = hub_paths.get(logical) or (
                    "data/" + asset["asset_name"] if logical.endswith(".csv") else asset["asset_name"])
                verified.append(target)
            else:
                verified.append(logical)
        dest["huggingface"] = replace(dest["huggingface"], files_verified=tuple(verified))
    levels = _object(data.get("levels"), path, "levels")
    if data.get("artifact_version") and qualification.get("artifact_version") and data["artifact_version"] != identity:
        problem("qualification.artifact_version", "differs from manifest artifact_version")
    names = sorted(levels or {s.config for s in splits.values() if s.config})
    configs = {n: tuple(sorted(s.name for s in splits.values() if s.config in (None, n)))
               for n in names} if names else {"default": tuple(sorted(s.name for s in splits.values()))}
    published = data.get("published", False)
    if type(published) is not bool:
        problem("published", "expected a boolean")
        published = False
    # Publication state is read from recorded evidence, never a regenerated assertion. A
    # package flipped public after its manifest froze keeps the frozen bytes (the generator
    # refuses to rewrite a published manifest), so the frozen "published" field stays False
    # forever while DESTINATIONS.json - written after anonymous verification - records that
    # every destination is verified and public. That recorded state IS publication: deriving
    # it here keeps generated documents (card, LOADING, site) from re-asserting "private"
    # for a release that is already public. The evidence must be complete - verified,
    # timestamped and located, exactly what the published validation below demands - or the
    # package stays unpublished: a bare private:false flag is not publication.
    if not published and dest and all(
            d.verified and d.verified_at and d.locator is not None and d.private is False
            for d in dest.values()):
        published = True
    if published and baseline and baseline.artifact_id and not identity.startswith(baseline.artifact_id):
        problem("baseline", "evaluation belongs to a different artifact")
    if published and not any(d.verified and d.verified_at and d.locator for d in dest.values()):
        problem("destinations", "published release has no recorded verified destination")
    return Release(name, identity, tag, splits, baseline, dest, terms, published, reason, configs,
                   (candidate or {}).get("status"), tuple(problems), {**data, "_path": str(path)})


def load_release(path, *, strict=True) -> Release:
    path = Path(path)
    manifest_path = path / "MANIFEST.json" if path.is_dir() else path
    folder = manifest_path.parent
    data = read_object(manifest_path)
    candidate_dir = folder.parent.parent / "candidates" / folder.name
    candidate_path = candidate_dir / "record.json"
    candidate = read_object(candidate_path) if candidate_path.is_file() else {}
    sources = []
    for filename, keys in (("quality.json", ("split_stats", "splits")), ("summary.json", ("splits",))):
        source = folder / filename
        if source.is_file():
            body = read_object(source)
            sources.extend((body.get(k), source, k) for k in keys)
    sources.append((_object(candidate.get("construction_output"), candidate_path, "construction_output").get("splits"), candidate_path,
                    "construction_output.splits"))
    baseline_path = candidate_dir / "baseline" / "baseline_result.json"
    baseline_source = (read_object(baseline_path), baseline_path) if baseline_path.is_file() else None
    dest_path = folder / "DESTINATIONS.json"
    dest = read_object(dest_path) if dest_path.is_file() else {}
    return from_manifest(data, path=manifest_path, destinations=dest, split_sources=sources,
                         baseline_source=baseline_source, candidate=candidate, strict=strict)
