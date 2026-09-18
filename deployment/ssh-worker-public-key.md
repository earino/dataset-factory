# Worker SSH public key for Hetzner registration

Generated on the hosted Scout instance, 2026-09-18, as authorized ordinary setup.
No prior key existed; nothing was overwritten.

- Private key (stays on Scout, mode 0600): `/opt/data/.ssh/scout_worker_ed25519`
- Public key file: `/opt/data/.ssh/scout_worker_ed25519.pub`
- Fingerprint: `SHA256:k4Uk+aJCEV28M7xvwsIzE3v0agPBXNrPXN/GGRFusms`
- Comment: `scout-dataset-factory-worker`

Public key text, to register in the dedicated Hetzner Cloud project:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPUjUlWiQKP7rne3yQhQs+g97MNUUgT1AL3Qaakn/iCJ scout-dataset-factory-worker
```

**Registered 2026-09-18** in the dedicated Hetzner project as:

| Field | Value |
|---|---|
| Name | `scout-worker` |
| ID | `130171155` |
| Fingerprint | `9d:80:95:90:cc:4c:c8:65:83:59:9f:8c:2b:d6:ae:30` |
| Result | public key read back from the API matches this local pair |

The project had no SSH keys before this registration. `config/local.json` carries
the matching policy values: `ssh_key_name` = `scout-worker`, `ssh_private_key` =
`/opt/data/.ssh/scout_worker_ed25519`. Worker launches remain disabled.

A public key is not a secret and may be shared; the private key must never leave
Scout or be committed.
