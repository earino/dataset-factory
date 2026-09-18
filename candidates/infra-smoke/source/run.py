"""Infrastructure fixture only. Not a dataset qualification test."""
import hashlib
import json
from pathlib import Path

out = Path("/output")
payload = b"row,value\n1,42\n2,17\n"
(out / "example.csv").write_bytes(payload)
(out / "summary.json").write_text(json.dumps({
    "purpose": "Verify Docker execution and artifact transport, not task quality",
    "rows": 2, "sha256": hashlib.sha256(payload).hexdigest(),
}))
print("Infrastructure fixture complete")
