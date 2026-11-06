#!/usr/bin/env python3
"""GitHub private staging for ab-wildfire-ia-escape (dataset-release skill).

Creates the private repository earino/ab-wildfire-ia-escape, pushes the
package files from release/ab-wildfire-ia-escape/ as the initial commit, and
creates release v2026.11 non-draft at main. The five bulk assets are NOT
uploaded here - they move worker-side in the transfer job. The publish token is
read from its file at the point of use and never printed or exported; the push
URL embedding it lives only inside the temporary clone's git config, which is
removed afterwards.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
REL = ROOT / "release" / "ab-wildfire-ia-escape"
REPO = "earino/ab-wildfire-ia-escape"
TAG = "v2026.11"
TOKEN_FILE = Path("/opt/data/.secrets/github-publish.token")


def run(args, cwd=None, check=True, secret=False):
    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and done.returncode:
        err = done.stderr[:400]
        raise SystemExit(f"failed ({' '.join(args[:3])}...): {err}")
    return done.stdout if not secret else "<redacted>"


def main() -> int:
    # 0. refuse to touch an existing repo: re-running must reconcile, not overwrite
    lookup = subprocess.run(
        ["gh", "api", f"repos/{REPO}"], capture_output=True, text=True)
    if lookup.returncode == 0:
        info = json.loads(lookup.stdout)
        raise SystemExit(
            f"{REPO} already exists (private={info.get('private')}) - "
            "reconcile the existing repository instead of recreating it")

    # 1. create the private repository
    run(["gh", "api", "-X", "POST", "/user/repos",
         "-f", "name=ab-wildfire-ia-escape", "-F", "private=true",
         "-F", "description=Alberta wildfire initial-attack escape prediction task "
                "(derived research dataset, not a Government of Alberta product)"])
    created = json.loads(run(["gh", "api", f"repos/{REPO}"]))
    assert created["private"] is True, "the repository must be private"
    print(f"created private {REPO} (id {created['id']})")

    # 2. push the package files as the initial commit
    token = TOKEN_FILE.read_text().strip()
    with tempfile.TemporaryDirectory(prefix="abwildfire-stage-") as tmp:
        work = Path(tmp) / "repo"
        work.mkdir()
        files = sorted(p for p in REL.rglob("*") if p.is_file())
        for path in files:
            dest = work / path.relative_to(REL)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
        run(["git", "init", "-q", "-b", "main"], cwd=work)
        run(["git", "add", "-A"], cwd=work)
        run(["git", "-c", "user.name=Scout (Hermes)",
             "-c", "user.email=scout@users.noreply.github.com",
             "commit", "-q", "-m",
             "ab-wildfire-ia-escape v2026.11 package (artifact c2c8ceb5): docs, "
             "construction/qualification/references code, runner files, "
             "MANIFEST + SHA256SUMS; bulk data assets arrive via the transfer job"],
            cwd=work)
        run(["git", "remote", "add", "origin",
             f"https://x-access-token:{token}@github.com/{REPO}.git"], cwd=work)
        run(["git", "push", "-q", "origin", "main"], cwd=work, secret=True)
        head = run(["git", "rev-parse", "HEAD"], cwd=work).strip()
        shutil.rmtree(work / ".git" / "config", ignore_errors=True)
    print(f"pushed {len(files)} package files as initial commit {head[:12]}")

    # 3. create the release non-draft at main
    release = json.loads(run([
        "gh", "api", "-X", "POST", f"repos/{REPO}/releases",
        "-f", f"tag_name={TAG}", "-f", "name=ab-wildfire-ia-escape v2026.11",
        "-f", "target_commitish=main", "-F", "draft=false",
        "-F", "prerelease=false",
        "-f", "body=Private staging release of artifact "
              "c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2 "
              "(gate 1.5.0, 45 checks, failed_checks empty, exact-byte accepted). "
              "The five data assets are attached by the worker-side transfer job; "
              "digests in MANIFEST.json / SHA256SUMS. Nothing here is public."]))
    assert release["draft"] is False
    print(f"created release {release['id']} ({TAG}) non-draft at {head[:12]}")

    # 4. verify from the API: repo private, file list, release state, anonymous 404
    again = json.loads(run(["gh", "api", f"repos/{REPO}"]))
    assert again["private"] is True
    tree = json.loads(run(["gh", "api", f"repos/{REPO}/git/trees/main?recursive=1"]))
    pushed = {e["path"] for e in tree["tree"] if e["type"] == "blob"}
    expected = {p.relative_to(REL).as_posix() for p in files}
    assert pushed == expected, f"pushed {len(pushed)} != expected {len(expected)}"
    anon = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         f"https://api.github.com/repos/{REPO}"], capture_output=True, text=True)
    print(f"verified: repo private, {len(pushed)} files on main, release "
          f"{release['id']} non-draft; anonymous API status {anon.stdout.strip()} "
          "(404 expected while private)")
    print(json.dumps({"repo": REPO, "release_id": release["id"], "tag": TAG,
                      "commit": head, "files": len(pushed)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
