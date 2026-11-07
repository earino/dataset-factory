"""Repository-owned remediation admission; cleanup and read-only checks stay available."""
import json
import re
from pathlib import Path

from .common import FactoryError


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def policy(root):
    path = Path(root) / "config" / "admission.json"
    try:
        if path.is_symlink() or path.stat().st_size > 65536:
            raise ValueError("invalid policy file")
        value = json.loads(path.read_text(), object_pairs_hook=_unique)
        if (not isinstance(value, dict) or value.get("version") != 1
                or type(value.get("hold")) is not bool
                or not isinstance(value.get("reason"), str) or not value["reason"].strip()
                or not isinstance(value.get("allowed_worker_bundles"), dict)):
            raise ValueError("invalid policy")
        for job, digest in value["allowed_worker_bundles"].items():
            if (not isinstance(job, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", job)
                    or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                raise ValueError("invalid worker pin")
        return value
    except (OSError, ValueError, TypeError):
        raise FactoryError("Admission policy missing or invalid: config/admission.json; refusing new work") from None


def hold_reason(root):
    value = policy(root)
    return "Factory remediation hold: " + value["reason"] if value["hold"] else None


def require(root, operation, *, job_id=None, bundle_sha256=None):
    value = policy(root)
    if not value["hold"]:
        return
    # Neither a release flag nor a candidate status may bypass the hold. Remediation
    # runs require an exact source-bundle pin, including their job specification.
    if (operation == "worker" and job_id in value["allowed_worker_bundles"]
            and value["allowed_worker_bundles"][job_id] == bundle_sha256):
        return
    raise FactoryError(f"Factory remediation hold blocks {operation}: {value['reason']}")
