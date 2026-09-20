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
import urllib.error
import urllib.request

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
import os
import sys

from datasets import load_dataset

repo_id, revision, expected_path = sys.argv[1:4]
expected = json.load(open(expected_path))
# The write credential is passed explicitly: this private dataset cannot be read without it,
# and `datasets` would otherwise look for HF_TOKEN, which this child deliberately does not have.
configs = expected.get("configs")
if configs:
    # Several configs: each is a task instance of its own, so each is loaded and checked by name
    # rather than one standing in for the others.
    report = {"configs": {}, "checked": {}, "ok": None}
    problems = []
    for name, want in sorted(configs.items()):
        loaded = load_dataset(repo_id, name, revision=revision, token=os.environ["HF_WRITE_TOKEN"])
        report["configs"][name] = {"splits": list(loaded.keys())}
        for split, expected_split in sorted(want["splits"].items()):
            if split not in loaded:
                problems.append(f"{name}/{split} missing from load_dataset output")
                continue
            frame = loaded[split]
            if frame.num_rows != expected_split["rows"]:
                problems.append(f"{name}/{split}: {frame.num_rows} rows != {expected_split['rows']}")
            positives = int(sum(frame[want["label"]]))
            if positives != expected_split["positives"]:
                problems.append(f"{name}/{split}: {positives} positives != {expected_split['positives']}")
            columns = sorted(frame.column_names)
            if want["columns"] and columns != sorted(want["columns"]):
                problems.append(f"{name}/{split}: columns differ from the manifest")
            report["checked"][f"{name}/{split}"] = {"rows": frame.num_rows, "positives": positives}
    report["problems"] = problems
    report["ok"] = not problems
else:
    ds = load_dataset(repo_id, revision=revision, token=os.environ["HF_WRITE_TOKEN"])
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
    # Read the label's values out of the data, not out of the feature's type: a CSV gives an
    # integer column with no `names`, so a ClassLabel-style comparison reports a mismatch on a
    # perfect dataset. The positive count then proves the values mean what the manifest says.
    label = expected["label"]
    if label in data.column_names:
        observed = sorted(str(value) for value in data.unique(label))
        wanted = sorted(str(value) for value in (expected.get("label_values") or []))
        if wanted and observed != wanted:
            problems.append(f"{split}: label values {observed} != manifest {wanted}")
        else:
            report["checked"][split]["label_values"] = wanted
        if want.get("positives") is not None:
            positives = int(sum(1 for value in data[label] if value in (1, True, "1")))
            report["checked"][split]["positives"] = positives
            if positives != want["positives"]:
                problems.append(f"{split}: {positives} positives, manifest says {want['positives']}")
    else:
        problems.append(f"{split}: label column {label!r} is absent")
report["problems"] = problems
report["ok"] = not problems
print(json.dumps(report, indent=2))
'''


def _pip_works(python):
    result = subprocess.run([str(python), "-m", "pip", "--version"], capture_output=True,
                            timeout=120)
    return result.returncode == 0


def ensure_pip(python, report, timeout=900):
    """Make `python -m pip` usable in the job venv.

    A stock worker image can create a venv and still have no pip inside it: `ensurepip` is a
    separate package (`python3-venv`) on Debian derivatives, and `uv` is not installed here. The
    first version of this job assumed one of the two existed and failed in 0.2 s on a paid worker.
    So: use pip if present, else install the package that provides it, else bootstrap.
    """
    if _pip_works(python):
        return True
    routes = []
    if shutil.which("apt-get"):
        routes.append((["apt-get", "update", "-qq"], None))
        routes.append((["apt-get", "install", "-y", "-qq", "python3-venv", "python3-pip"], None))
    for command, _ in routes:
        try:
            subprocess.run(command, capture_output=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            continue
    if _pip_works(python):
        return True
    try:
        with urllib.request.urlopen("https://bootstrap.pypa.io/get-pip.py", timeout=120) as handle:
            bootstrap = handle.read()
        script = python.parent.parent / "get-pip.py"
        script.write_bytes(bootstrap)
        subprocess.run([str(python), str(script), "--quiet"], capture_output=True, timeout=timeout)
    except (OSError, urllib.error.URLError, subprocess.SubprocessError):
        pass
    report["pip_bootstrapped"] = _pip_works(python)
    return report["pip_bootstrapped"]


def ensure_client(base, report, timeout=900):
    """Create the venv the upload/verify helpers run in. Nothing is installed inside a container."""
    venv = base / VENV
    python = venv / "bin" / "python"
    report["venv"] = str(venv)
    if not python.exists():
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
    if not ensure_pip(python, report, timeout):
        raise UploadError("no pip is available in the job venv and it could not be bootstrapped")
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


def hub_state(base, index, repo, revision, target, python, hf_token):
    """What the Hub reports for one path: size, and the digest when it stores the file as LFS.

    A file pushed to the Hub is stored either as an LFS object (large files) or as a plain git
    blob (small ones). The API exposes a sha256 only for LFS objects; for a regular blob it
    exposes a git blob id, which is a SHA-1 over different bytes and never equals the manifest's
    sha256. Treating "no sha256 reported" as "digest mismatch" failed two perfectly good 2-5 KiB
    uploads on a paid worker.
    """
    script = (
        "import json,os,sys\n"
        "from huggingface_hub import HfApi\n"
        "out={'found': False}\n"
        "try:\n"
        "    info=HfApi(token=os.environ['HF_WRITE_TOKEN']).repo_info(\n"
        "        sys.argv[1], repo_type='dataset', revision=sys.argv[2], files_metadata=True)\n"
        "except Exception as exc:\n"
        "    out['error']=type(exc).__name__\n"
        "    print(json.dumps(out)); raise SystemExit(0)\n"
        "for s in info.siblings or []:\n"
        "    if s.rfilename==sys.argv[3]:\n"
        "        lfs=getattr(s,'lfs',None) or {}\n"
        "        out={'found': True, 'size': s.size, 'lfs_sha256': lfs.get('sha256')}\n"
        "        break\n"
        "print(json.dumps(out))\n")
    path = write_helper(base, f".hf-lookup-{index}.py", script)
    result = subprocess.run([str(python), str(path), repo, revision, target],
                            capture_output=True, text=True, env=hub_env(hf_token), timeout=300)
    try:
        return json.loads((result.stdout or "{}").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"found": False, "error": "unreadable lookup output"}


def hub_digest_by_download(base, index, repo, revision, target, python, hf_token):
    """Hash a small file the Hub stores as a plain blob. Bounded to small files on purpose."""
    script = (
        "import hashlib,json,os,sys\n"
        "from huggingface_hub import hf_hub_download\n"
        "path=hf_hub_download(repo_id=sys.argv[1], filename=sys.argv[3], repo_type='dataset',\n"
        "                    revision=sys.argv[2], token=os.environ['HF_WRITE_TOKEN'],\n"
        "                    cache_dir=sys.argv[4])\n"
        "h=hashlib.sha256()\n"
        "with open(path,'rb') as handle:\n"
        "    for chunk in iter(lambda: handle.read(1 << 20), b''):\n"
        "        h.update(chunk)\n"
        "print(h.hexdigest())\n")
    path = write_helper(base, f".hf-hash-{index}.py", script)
    cache = base / "hf-cache"
    result = subprocess.run([str(python), str(path), repo, revision, target, str(cache)],
                            capture_output=True, text=True, env=hub_env(hf_token), timeout=600)
    lines = [line for line in (result.stdout or "").strip().splitlines() if line]
    return lines[-1] if lines else ""


SMALL_BLOB_BYTES = 8 * 1024 * 1024


def already_published(base, index, repo, revision, target, sha256, size, python, hf_token):
    """True when the Hub already holds this path at this digest. Makes a resume cheap.

    Also the post-upload check, so "the client returned success" is never the evidence.
    """
    state = hub_state(base, index, repo, revision, target, python, hf_token)
    if not state.get("found"):
        return False
    if state.get("lfs_sha256"):
        return state["lfs_sha256"] == sha256
    if size and state.get("size") != size:
        return False
    if size and size <= SMALL_BLOB_BYTES:
        return hub_digest_by_download(base, index, repo, revision, target, python, hf_token) == sha256
    return False


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
    deadline = time.monotonic() + int(job.get("timeout_minutes", 60)) * 60
    for index, item in enumerate(spec["assets"], start=1):
        if time.monotonic() > deadline:
            failures.append({"target": item["target"],
                             "error": "runtime limit reached; nothing else attempted"})
            continue
        target = item["target"]
        local = base / "cache" / item["dest"]
        local.parent.mkdir(parents=True, exist_ok=True)
        try:
            if already_published(base, index, spec["repo"], spec["revision"], target,
                                 item["sha256"], item.get("size"), python, hf_token):
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
            if not already_published(base, index, spec["repo"], spec["revision"], target,
                                     item["sha256"], item.get("size"), python, hf_token):
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
                                    "error": (result.stderr or result.stdout).strip()[:4000]}
        if result.returncode != 0 or not report["hf_loading"].get("ok"):
            failures.append({"target": "loading-path", "error": "the documented loading path did "
                                                                "not reproduce the artifact"})
            report["hf_publish"]["failures"] = failures
    return report
