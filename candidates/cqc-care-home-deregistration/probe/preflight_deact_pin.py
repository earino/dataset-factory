"""Preflight for cqc-chd-002: verify the deactivated-file pin still holds
(the build asserts size+sha256 against the 2026-11-02 edition) before the
relaunch, so a source-drift failure is not misread as a construction defect.
Bounded: one 27.6 MB fetch into scratch, hash, discard."""
import hashlib
import importlib.util
import sys
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = (HERE.parents[2] / "candidates" /
         "cqc-care-home-deregistration" / "source" / "build.py")
spec = importlib.util.spec_from_file_location("cqc_build_pre", str(BUILD))
b = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise SystemExit("no loader")
spec.loader.exec_module(b)

req = urllib.request.Request(b.DEACT_URL, headers=b.DRIVE_UA)
with urllib.request.urlopen(req, timeout=600) as r:
    data = r.read()
digest = hashlib.sha256(data).hexdigest()
ok = len(data) == b.DEACT_SIZE and digest.startswith(b.DEACT_SHA_PREFIX)
print(f"url: {b.DEACT_URL}")
print(f"bytes: {len(data)} (pin {b.DEACT_SIZE}) -> {'MATCH' if len(data) == b.DEACT_SIZE else 'DRIFT'}")
print(f"sha256: {digest[:16]} (pin {b.DEACT_SHA_PREFIX}) -> {'MATCH' if digest.startswith(b.DEACT_SHA_PREFIX) else 'DRIFT'}")
print(f"PIN HOLDS: {ok}")
