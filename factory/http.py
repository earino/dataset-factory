"""Bounded JSON requests; tokens come from environment or a private file."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import urllib.error
import urllib.request

from .common import FactoryError


def _secret_file(path):
    """Return a bounded value and a safe status, never a path-bearing exception."""
    try:
        path = Path(path).expanduser()
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            return "not_regular", None
        if metadata.st_mode & 0o077:
            return "insecure_permissions", None
        with path.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            return "too_large", None
        value = raw.decode("utf-8").strip()
        return ("ready", value) if value else ("empty", None)
    except FileNotFoundError:
        return "missing", None
    except UnicodeError:
        return "invalid_text", None
    except (OSError, ValueError, RuntimeError):
        return "unreadable", None


def credential_status(name):
    """Offline diagnostics: no credential values, paths, hashes or API calls."""
    env_present = bool(os.environ.get(name, "").strip())
    file_path = os.environ.get(name + "_FILE", "").strip()
    file_status, _ = _secret_file(file_path) if file_path else ("unset", None)
    source = "environment" if env_present else "file" if file_status == "ready" else None
    return {"environment_present": env_present, "file_variable_present": bool(file_path),
            "file_status": file_status, "source": source, "ready": source is not None}


def secret(name):
    value = os.environ.get(name, "").strip()
    file_path = os.environ.get(name + "_FILE", "").strip()
    if not value and file_path:
        status, value = _secret_file(file_path)
        if status != "ready":
            raise FactoryError(f"{name}_FILE: {status}; provide a readable, nonempty private token file (0600)")
    if not value:
        raise FactoryError(f"Set {name} or {name}_FILE; never put credentials in Git")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class API:
    def __init__(self, base, token):
        self.base, self.token = base.rstrip("/"), token

    def request(self, method, path, body=None, missing_ok=False):
        request = urllib.request.Request(
            self.base + "/" + path.lstrip("/"),
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
                     "Accept": "application/json", "User-Agent": "dataset-factory-scout"},
            method=method,
        )
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=45) as response:
                data = response.read(4 * 1024 * 1024 + 1)
                if len(data) > 4 * 1024 * 1024:
                    raise FactoryError("API response exceeds the 4 MiB metadata limit")
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            raise FactoryError(f"API {method} {path.split('?')[0]} returned HTTP {exc.code}") from None
        except (OSError, ValueError) as exc:
            raise FactoryError(f"API request failed ({type(exc).__name__}); reconcile before retrying mutations") from None
