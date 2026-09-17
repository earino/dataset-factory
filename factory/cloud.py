"""Hetzner operations used by the coordinator and independent expiry sweeper."""
from __future__ import annotations

import time
import urllib.parse

from .common import FactoryError
from .http import API, secret


class Cloud(API):
    def __init__(self):
        super().__init__("https://api.hetzner.cloud/v1", secret("HCLOUD_TOKEN"))

    def list_resources(self, resource, project):
        items, page = [], 1
        while page:
            query = urllib.parse.urlencode({"label_selector": f"factory={project}", "per_page": 50, "page": page})
            result = self.request("GET", f"{resource}?{query}")
            items.extend(result[resource])
            page = result.get("meta", {}).get("pagination", {}).get("next_page")
        return items

    def server(self, server_id):
        result = self.request("GET", f"servers/{int(server_id)}", missing_ok=True)
        return result["server"] if result else None

    def wait_action(self, action, timeout=240):
        deadline = time.monotonic() + timeout
        while action["status"] == "running":
            if time.monotonic() >= deadline:
                raise FactoryError("Hetzner operation pending; inspect the job before retrying")
            time.sleep(3)
            action = self.request("GET", f"actions/{action['id']}")["action"]
        if action["status"] != "success":
            raise FactoryError("Hetzner operation failed; reconcile the recorded worker")

    def label_ips(self, server):
        for family in ("ipv4", "ipv6"):
            ip_id = (server.get("public_net", {}).get(family) or {}).get("id")
            if ip_id:
                ip = self.request("GET", f"primary_ips/{ip_id}")["primary_ip"]
                if ip.get("assignee_id") != server["id"]:
                    raise FactoryError("Primary IP is not assigned to this worker")
                self.request("PUT", f"primary_ips/{ip_id}", {
                    "auto_delete": True, "labels": {**ip.get("labels", {}), **server["labels"]},
                })

    def delete_owned(self, server, project, job_id):
        current = self.server(server["id"])
        if current is None:
            return
        labels = current.get("labels", {})
        if labels.get("factory") != project or labels.get("job") != job_id:
            raise FactoryError("Refusing deletion: server ownership does not match this job")
        if current.get("volumes"):
            raise FactoryError("Unexpected attached volumes; inspect before deleting")
        self.label_ips(current)
        result = self.request("DELETE", f"servers/{current['id']}", missing_ok=True)
        if result and result.get("action"):
            self.wait_action(result["action"])
        if self.server(current["id"]) is not None:
            raise FactoryError("Server deletion has not been confirmed")

    def clean_expired_ips(self, project, now):
        deleted = []
        for ip in self.list_resources("primary_ips", project):
            labels = ip.get("labels", {})
            try:
                expired = int(labels["expires"]) <= now
            except (KeyError, ValueError):
                continue
            if expired and labels.get("factory") == project and labels.get("job") and not ip.get("assignee_id"):
                self.request("DELETE", f"primary_ips/{ip['id']}", missing_ok=True)
                if self.request("GET", f"primary_ips/{ip['id']}", missing_ok=True) is not None:
                    raise FactoryError("Primary IP deletion has not been confirmed")
                deleted.append(ip["id"])
        return deleted

    def clean_job_ips(self, project, job_id):
        for ip in self.list_resources("primary_ips", project):
            labels = ip.get("labels", {})
            if labels.get("factory") != project or labels.get("job") != job_id:
                continue
            if ip.get("assignee_id"):
                raise FactoryError("Job IP still assigned; cleanup incomplete")
            self.request("DELETE", f"primary_ips/{ip['id']}", missing_ok=True)
            if self.request("GET", f"primary_ips/{ip['id']}", missing_ok=True) is not None:
                raise FactoryError("Primary IP deletion has not been confirmed")
