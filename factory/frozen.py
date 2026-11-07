"""Exact historical identities, never a caller-provided exemption from new gates."""
import json
from pathlib import Path

from .artifact_scrub import sha256

REGISTRY = Path(__file__).resolve().parents[1] / 'config/frozen-releases.json'


def historical_files(package):
    """Return pinned old file hashes only when the frozen manifest itself matches."""
    package = Path(package)
    path = package / 'MANIFEST.json'
    if not path.is_file() or path.is_symlink():
        return {}
    identity = sha256(path)
    registry = json.loads(REGISTRY.read_text())
    for entry in registry['releases']:
        if entry['manifest_sha256'] == identity:
            return entry['editorial_files']
    return {}
