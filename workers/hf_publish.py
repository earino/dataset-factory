"""Upload already-built release assets to Hugging Face from a worker.

Deliberately stdlib-only at this level, for three reasons that matter here:

* the token never enters a container - this runs on the worker host, and the Hugging Face client
  lives in a venv created beside the job, so no dataset-job input mount can carry the credential;
* the bulk bytes never touch the coordinator: each asset is downloaded straight from the GitHub
  release to the worker, verified against its manifest digest, pushed, verified again, and deleted;
* it is the same shape as the existing transfer/fetch jobs, so it reuses the worker, ledger,
  cleanup and budget mechanisms rather than adding a parallel system.

Bounded retries only: three attempts with exponential backoff per asset, then the asset is
reported as failed and the job continues with the rest. Re-running is safe - an asset already on
the Hub with a matching digest is skipped, so a resumed job does not re-send 131 MB.
"""

import json
import os
import shutil
import subprocess
import sys
import time

try:
    from .upload import GitHub, UploadError, digest
except ImportError:  # the worker loads this file directly
    from upload import GitHub, UploadError, digest

ATTEMPTS = 3
BACKOFF_SECONDS = 5
# Written beside the job, never inside the job's input mounts.
VENV = ".hf-venv"

UPLOAD_HELPER = '''\
"""Push one file to a Hugging Face dataset repo, called by the worker with its venv python.

Arguments: repo id, local path, path in repo, revision. The token arrives in the environment and
is never an argument, never logged and never written to disk.
"""
import os
import sys

from huggingface_hub import HfApi

repo_id, local_path, target, revision = sys.argv[1:5]
token = os.environ["HF_WRITE_TOKEN"]
api = HfApi(token=token)
info = api.upload_file(
    path_or_fileobj=local_path, path_in_repo=target, repo_id=repo_id, repo_type="dataset",
    revision=revision,
    commit_message=f"Publish {target} from the accepted artifact manifest",
)
print(info.oid or "", flush=True)
'''

VERIFY_HELPER = '''\
"""Exercise the documented loading path against the uploaded bytes.

Checks the split names, row counts, schema and the label values against what the accepted
artifact declares, so "it uploaded" is not mistaken for "it loads".
"""
import json
import sys

from datasets import load_dataset

repo_id, revision, expected_path = sys.argv[1:4]
expected = json.load(open(expected_path))
ds = load_dataset(repo_id, revision=revision)
report = {"splits": list(ds.keys()), "checked": {}}
problems = []
for split, want in sorted(expected["splits"].items()):
    if split not in ds:
        problems.append(f"split {split} missing from load_dataset output")
        continue
    data = ds[split]
    columns = sorted(data.column_names)
    report["checked"][split] = {"rows": len(data), "columns": columns}
    if len(data) != want["rows"]:
        problems.append(f"{split}: {len(data)} rows, manifest says {want['rows']}")
    if expected["columns"] and columns != sorted(expected["columns"]):
        problems.append(f"{split}: columns {columns} != manifest {sorted(expected['columns'])}")
    label = data.features.get(expected["label"]) if hasattr(data, "features") else None
    if label is not None and expected.get("label_values"):
        if sorted(str(v) for v in getattr(label, "names", []) or []) != sorted(
                str(v) for v in expected["label_values"]):
            problems.append(f"{split}: label values differ from the manifest")
        else:
            report["checked"][split]["label_values"] = list(expected["label_values"])
report["problems"] = problems
report["ok"] = not problems
print(json.dumps(report, indent=2))
'''


def ensure_client(base, report, timeout=900):
    """Create the venv the upload/verify helpers run in. Nothing is installed inside a container."""
    venv = base / VENV
    python = venv / "bin" / "python"
    if python.exists():
        return python
    report["venv"] = str(venv)
    installers = (["uv", "venv", "--python", "3.12", str(venv)],
                  [sys.executable, "-m", "venv", str(venv)])
    for command in installers:
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=300)
            break
        except (OSError, subprocess.SubprocessError):
            continue
    if not python.exists():
        raise UploadError("could not create a virtual environment for the Hugging Face client")
    install = (["uv", "pip", "install", "--python", str(python), "huggingface_hub"]
               if shutil.which("uv") else
               [str(python), "-m", "pip", "install", "--quiet", "huggingface_hub"])
    result = subprocess.run(install, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise UploadError(f"installing the Hugging Face client failed: "
                          f"{result.stderr.strip()[:300]}")
    return python


def write_helper(base, name, body):
    path = base / name
    path.write_text(body)
    return path


def hub_env(hf_token):
    env = dict(os.environ)
    env["HF_WRITE_TOKEN"] = hf_token
    # Keep any inference credential out of the child entirely: this process only publishes.
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN"):
        env.pop(name, None)
    return env


def already_published(client, repo_id, target, sha256, hf_token, python):
    """True when the Hub already holds this path at this digest. Makes a resume cheap."""
    script = base_lookup = (
        "import os,sys,json\n"
        "from huggingface_hub import HfApi\n"
        "api=HfApi(token=os.environ['HF_WRITE_TOKEN'])\n"
        "try:\n"
        "    info=api.repo_info(sys.argv[1], repo_type='dataset', revision=sys.argv[2],"
        " files_metadata=True)\n"
        "except Exception as exc:\n"
        "    print(''); raise SystemExit(0)\n"
        "for s in info.siblings or []:\n"
        "    if s.rfilename==sys.argv[3]:\n"
        "        lfs=getattr(s,'lfs',None) or {}\n"
        "        print(lfs.get('sha256') or getattr(s,'blob_id','') or ''); break\n"
        "else:\n"
        "    print('')\n")
    path = write_helper(client["base"], f".hf-lookup-{client['index']}.py", script)
    result = subprocess.run([str(python), str(path), repo_id, client["revision"], target],
                            capture_output=True, text=True, env=hub_env(hf_token), timeout=300)
    reported = (result.stdout or "").strip().splitlines()
    return bool(reported) and reported[-1] == sha256


def hf_publish(base, job, report, client=None, retrieve=None):
    """Download each named asset from the release, push it to Hugging Face, verify and delete."""
    spec = job["hf_publish"]
    credentials = json.loads((base / "credentials.json").read_text())
    hf_token = credentials.get("hf_write_token")
    if not hf_token:
        raise UploadError("no Hugging Face write credential was delivered to this worker")
    source = client or GitHub(credentials.get("publish_token") or credentials["token"],
                              spec["source_repo"])
    python = ensure_client(base, report)

    uploads, skipped, failures = [], [], []
    for index, item in enumerate(spec["assets"], start=1):
        target = item["target"]
        local = base / "cache" / item["dest"]
        local.parent.mkdir(parents=True, exist_ok=True)
        state = {"base": base, "index": index, "revision": spec["revision"]}
        try:
            if already_published(state, spec["repo"], target, item["sha256"], hf_token, python):
                skipped.append({"target": target, "reason": "already at the manifest digest"})
                continue
            client_downloaded = None
            for attempt in range(1, ATTEMPTS + 1):
                try:
                    written = source.download(item["asset_id"], local, item["sha256"],
                                              item.get("size"))
                    if digest(local) != item["sha256"]:
                        raise UploadError(f"{target}: downloaded bytes do not match the manifest")
                    client_downloaded = written
                    break
                except UploadError:
                    if attempt == ATTEMPTS:
                        raise
                    time.sleep(BACKOFF_SECONDS * attempt)
            helper = write_helper(base, f".hf-upload-{index}.py", UPLOAD_HELPER)
            result = subprocess.run([str(python), str(helper), spec["repo"], str(local), target,
                                     spec["revision"]],
                                    capture_output=True, text=True, env=hub_env(hf_token),
                                    timeout=3600)
            if result.returncode != 0:
                raise UploadError(f"{target}: upload failed: "
                                  f"{(result.stderr or result.stdout).strip()[:300]}")
            if not already_published(state, spec["repo"], target, item["sha256"], hf_token, python):
                raise UploadError(f"{target}: uploaded, but the Hub does not report the manifest "
                                  "digest")
            uploads.append({"target": target, "bytes": client_downloaded,
                            "sha256": item["sha256"]})
        except (UploadError, OSError, subprocess.SubprocessError) as exc:
            failures.append({"target": target, "error": str(exc)[:300]})
        finally:
            if local.exists():
                local.unlink()

    report["hf_publish"] = {"repo": spec["repo"], "revision": spec["revision"],
                            "uploads": uploads, "skipped": skipped, "failures": failures,
                            "bytes": sum(entry["bytes"] for entry in uploads)}

    if spec.get("verify_loading") and not failures:
        expected_path = base / "expected.json"
        expected_path.write_text(json.dumps(spec["verify_loading"], indent=2))
        helper = write_helper(base, ".hf-verify.py", VERIFY_HELPER)
        install = (["uv", "pip", "install", "--python", str(python), "datasets", "pyarrow"]
                   if shutil.which("uv") else
                   [str(python), "-m", "pip", "install", "--quiet", "datasets"])
        subprocess.run(install, capture_output=True, timeout=1800)
        result = subprocess.run([str(python), str(helper), spec["repo"], spec["revision"],
                                 str(expected_path)],
                                capture_output=True, text=True, env=hub_env(hf_token), timeout=3600)
        try:
            report["hf_loading"] = json.loads(result.stdout)
        except json.JSONDecodeError:
            report["hf_loading"] = {"ok": False,
                                    "error": (result.stderr or result.stdout).strip()[:400]}
        if result.returncode != 0 or not report["hf_loading"].get("ok"):
            failures.append({"target": "loading-path", "error": "the documented loading path did "
                                                                "not reproduce the artifact"})
            report["hf_publish"]["failures"] = failures
    return report
