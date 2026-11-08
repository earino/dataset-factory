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
    from .pipeline import enabled
    if enabled(root):
        # The operator's replacement policy supersedes the old remediation hold,
        # but only the transactional controller may originate replacement jobs.
        if operation == 'worker' and job_id and (Path(root) / '.factory/pipeline.sqlite3').is_file():
            from .state import Store
            with Store(root).connect() as db:
                row = db.execute("SELECT stage FROM attempts WHERE id=? AND status='running'", (job_id,)).fetchone()
            if row and row['stage'] in ('build', 'publish'):
                return
        raise FactoryError('Replacement controller owns admission; superseded launch paths are disabled')
    value = policy(root)
    if not value["hold"]:
        return
    # Neither a release flag nor a candidate status may bypass the hold. Remediation
    # runs require an exact source-bundle pin, including their job specification.
    if (operation == "worker" and job_id in value["allowed_worker_bundles"]
            and value["allowed_worker_bundles"][job_id] == bundle_sha256):
        return
    raise FactoryError(f"Factory remediation hold blocks {operation}: {value['reason']}")
