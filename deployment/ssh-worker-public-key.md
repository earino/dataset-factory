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

Register it with the name **`scout-dataset-factory-worker`** so the policy value
`ssh_key_name` in `config/local.json` matches. The policy also points
`ssh_private_key` at the private key path above.

A public key is not a secret and may be shared; the private key must never leave
Scout or be committed. Registration is required before any paid launch.
