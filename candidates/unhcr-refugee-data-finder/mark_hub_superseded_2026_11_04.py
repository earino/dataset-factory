#!/usr/bin/env python3
"""Mark the dropped unhcr Hub repo README with a DO NOT PUBLISH banner (2026-11-04).

Operator decision applied 2026-11-02: the v2026.10 panel package is dropped and never
to be flipped. This implements the recorded next_action's supersede marking on the
Hugging Face side: a banner on main (the tag v2026.10 stays frozen at 77aa1fad; main
advances editorially only). Small-file channel by design; no bulk data touches the
coordinator. Idempotent: a second run reports already-marked and exits 0.

Run with: /opt/data/.venvs/hf/bin/python candidates/unhcr-refugee-data-finder/mark_hub_superseded_2026_11_04.py
"""
import sys

from huggingface_hub import HfApi, hf_hub_download, upload_file

REPO = "earino/unhcr-refugee-data-finder"
TOKEN_FILE = "/opt/data/.secrets/huggingface-write.token"
FILENAME = "README.md"

BANNER = (
    "> **DROPPED - DO NOT PUBLISH.** This v2026.10 package was dropped by operator "
    "decision on 2026-11-02 and will never be published in this form: two independent "
    "audits found the panel self-answers by construction (a label-year T+1 row ships the "
    "year-T total that is the T row's label operand; frozen recoveries reached eval AUC "
    "0.975325 / holdout 0.983034). The tag `v2026.10` is preserved as historical staging "
    "evidence only. The candidate record's reopen condition (a redesigned task that keeps "
    "corridor momentum without adjacent corridor-years both shipping) is the only path to "
    "any future release."
)


def main() -> int:
    token = open(TOKEN_FILE).read().strip()
    api = HfApi(token=token)
    info = api.repo_info(REPO, repo_type="dataset")
    if not info.private:
        print("REFUSED: repository is public; expected private")
        return 1
    path = hf_hub_download(repo_id=REPO, repo_type="dataset", filename=FILENAME,
                           revision="main", token=token)
    text = open(path, encoding="utf-8").read()
    if "DROPPED - DO NOT PUBLISH" in text:
        print("already-marked: banner present on main, nothing to do")
        return 0
    if text.startswith("---\n"):
        end = text.index("\n---\n", 4) + len("\n---\n")
        new_text = text[:end] + "\n" + BANNER + "\n" + text[end:]
    else:
        new_text = BANNER + "\n\n" + text
    upload_file(repo_id=REPO, repo_type="dataset", path_or_fileobj=new_text.encode("utf-8"),
                path_in_repo=FILENAME, commit_message=(
                    "Mark v2026.10 dropped package DO NOT PUBLISH "
                    "(operator decision 2026-11-02; editorial main only, tag untouched)"),
                token=token)
    check = hf_hub_download(repo_id=REPO, repo_type="dataset", filename=FILENAME,
                            revision="main", token=token)
    check_text = open(check, encoding="utf-8").read()
    if "DROPPED - DO NOT PUBLISH" not in check_text:
        print("FAILED: banner not present after upload")
        return 1
    commits = api.list_repo_commits(repo_id=REPO, repo_type="dataset")
    tip = commits[0].commit_id
    tags = api.list_repo_refs(repo_id=REPO, repo_type="dataset").tags
    vtag = next((t for t in tags if getattr(t, "name", "") == "v2026.10"), None)
    tag_sha = getattr(vtag, "commit_sha", None) or getattr(getattr(vtag, "ref", None), "commit_sha", None)
    print("banner-verified: main tip %s, tag v2026.10 still at %s"
          % (tip[:12], (str(tag_sha)[:12] if tag_sha else "UNREADABLE")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
