#!/usr/bin/env python3
"""Verify the Hugging Face publishing identity and what the write token may actually do.

Never prints a credential and never writes one anywhere: the token is read from the environment
variable named on the command line (default `HF_TOKEN_WRITE`), used in-process, and reported only
as length/prefix plus the permission facts the API returns about it.

The point of this step is that "a token exists" is not "a token may push to this repository".
The inference token is a different credential and is not touched here.

    python3 scripts/hf-identity.py
    python3 scripts/hf-identity.py --namespace earino --repo austin-911-response
"""

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_VENV_PYTHON = "/opt/data/.venvs/hf/bin/python"


def reexec_in_venv():
    """huggingface_hub lives in a purpose-built venv; re-exec there if it is not importable.

    Deliberately not a path comparison: a uv venv's `bin/python` is a symlink to the system
    interpreter, so resolved paths compare equal and a path check silently does nothing. Test the
    thing that actually matters - can we import the client - and treat a missing venv as a clear
    message rather than a traceback.
    """
    if os.environ.get("HF_IDENTITY_VENV") == "1":
        return
    try:
        import huggingface_hub  # noqa: F401
        return
    except ImportError:
        pass
    target = Path(DEFAULT_VENV_PYTHON)
    if not target.is_file():
        print(json.dumps({"ok": False, "error": "huggingface_hub is not importable and the venv "
                                                f"at {target} does not exist; create it with "
                                                "'uv venv --python 3.13 " + str(target.parent.parent)
                                                + " && uv pip install huggingface_hub'"}, indent=2))
        raise SystemExit(2)
    os.environ["HF_IDENTITY_VENV"] = "1"
    os.execv(str(target), [str(target), *sys.argv])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-var", default="HF_TOKEN_WRITE")
    parser.add_argument("--namespace", default=None,
                        help="candidate namespace to report access for")
    parser.add_argument("--repo", default=None, help="candidate dataset repository name")
    args = parser.parse_args(argv)

    reexec_in_venv()
    from huggingface_hub import HfApi  # imported after the re-exec
    from huggingface_hub.utils import HfHubHTTPError

    token = os.environ.get(args.token_var)
    if not token:
        print(json.dumps({"ok": False, "error": f"{args.token_var} is not visible in this "
                                                "process environment"}, indent=2))
        return 2

    api = HfApi(token=token)
    report = {"token_var": args.token_var, "token_length": len(token),
              "token_prefix": token[:3]}

    try:
        who = api.whoami()
    except HfHubHTTPError as exc:
        report.update({"ok": False, "error": f"whoami failed: {exc}"})
        print(json.dumps(report, indent=2))
        return 1

    report["ok"] = True
    report["account"] = who.get("name")
    report["account_type"] = who.get("type")
    report["organizations"] = sorted(
        org.get("name") for org in (who.get("orgs") or []) if org.get("name"))
    auth = who.get("auth") or {}
    access = auth.get("accessToken") or {}
    report["auth_type"] = auth.get("type")
    # Role and scopes only: neither reveals the credential.
    report["token_role"] = access.get("role")
    report["token_scopes"] = sorted(access.get("scopes") or []) or None
    report["token_permissions"] = sorted(
        (access.get("permissions") or []))[:20] or None
    report["inference_credentials_untouched"] = [
        name for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN")
        if os.environ.get(name)
    ] or "none visible in this process environment"

    if args.namespace:
        for label, authorized in (("whoami_is_namespace", report["account"] == args.namespace),
                                  ("namespace_is_an_org", args.namespace in
                                   report["organizations"])):
            report[label] = authorized
        if args.repo and args.namespace:
            candidate = f"{args.namespace}/{args.repo}"
            try:
                info = api.repo_info(candidate, repo_type="dataset")
                report["existing_repo"] = {
                    "id": info.id, "private": info.private,
                    "files": sorted((info.siblings or []) and
                                    [s.rfilename for s in info.siblings] or []),
                }
            except HfHubHTTPError as exc:
                response = getattr(exc, "response", None)
                report["existing_repo"] = {
                    "id": candidate,
                    "status_code": getattr(response, "status_code", None),
                    "note": "absent, or not visible to this token",
                }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
