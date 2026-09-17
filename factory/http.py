"""Bounded JSON requests; tokens come from environment or a private file."""
from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from .common import FactoryError


def secret(name):
    value = os.environ.get(name, "").strip()
    if not value and os.environ.get(name + "_FILE"):
        path = Path(os.environ[name + "_FILE"]).expanduser()
        if path.stat().st_mode & 0o077:
            raise FactoryError(f"{name}_FILE must have permissions 0600")
        value = path.read_text().strip()
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
