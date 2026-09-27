#!/usr/bin/env python3
"""Sync release/<id>/ to the public repository's default branch and push.

Docs-only update: the release assets and the v2026.09 tag are not touched.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
CANDIDATE = "chicago-doah-adjudication"
REPO = "earino/chicago-doah-adjudication"
WORK = Path("/opt/data/cache/scratch/release-repo-sync")
TOKEN = Path("/opt/data/.secrets/github-publish.token").read_text().strip()


def run(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write("FAILED: %s\n%s\n%s\n" % (" ".join(args[:3]), p.stdout[-2000:], p.stderr[-2000:]))
        raise SystemExit(1)
    return p.stdout


if WORK.exists():
    subprocess.run(["rm", "-rf", str(WORK)], check=True)
url = f"https://x-access-token:{TOKEN}@github.com/{REPO}.git"
run(["git", "clone", "--quiet", url, str(WORK)])

src = ROOT / "release" / CANDIDATE
for path in sorted(src.rglob("*")):
    if path.is_file():
        rel = path.relative_to(src)
        dest = WORK / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())

run(["git", "add", "-A"], cwd=WORK)
status = run(["git", "status", "--short"], cwd=WORK)
print("changed files:\n" + (status or "(none)"))
if not status.strip():
    print("nothing to commit")
    raise SystemExit(0)

msg = ("Name the source's dropped text fields in the data dictionary\n\n"
       "DATA_DICTIONARY.md said only that 'all other source columns are absent by construction'.\n"
       "The source table does carry prose (violation_description, respondents, address text,\n"
       "nov_number, location), so the dictionary now names each one and separates the reasons:\n"
       "the description is a fixed rendering of violation_code (1,260 codes, 1,266 pairs), the\n"
       "party text is withheld as a redistribution decision rather than dismissed as\n"
       "uninformative, and the address/identifier fields restate what the shipped columns carry.\n"
       "It also records the refreshed Hub revision. No data file, checksum or release asset\n"
       "changes; artifact_version is unchanged.")
run(["git", "-c", "user.name=scout-factory", "-c", "user.email=factory@earino.invalid",
     "commit", "--quiet", "-m", msg], cwd=WORK)
run(["git", "push", "--quiet", "origin", "HEAD:main"], cwd=WORK)
head = run(["git", "rev-parse", "HEAD"], cwd=WORK).strip()
print("pushed", head)
print(run(["git", "log", "--oneline", "-3"], cwd=WORK))
