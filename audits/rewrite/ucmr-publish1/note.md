UCMR publish-1 outcome (collected 2026-11-08T20:47:02Z, deleted
20:47:12Z). FAILED at stage release_publish: "UploadError", exit 1,
199 s, after: GitHub target release 438510985 created in
earino/factory-ucmr5-first-sample-pfas with assets transferred from
staging 438502804 (LICENSE-EVIDENCE.json 725 B sha256 99fbc3dc... et
al.), and Hugging Face uploads to earino/factory-ucmr5-first-sample-
pfas begun (LICENSE-EVIDENCE.json, LICENSE.md, ...). uploaded=true;
skipped_empty=[container.log]; host cleanup complete.

Tick routed to retry: "Publication incomplete; retry reconciles
destination files and tags" - the publisher's designed resume path
(reconciles destination files/tags, then version-tag binding,
visibility change, anonymous consumer verification on both
platforms). No manual intervention; the normal controller owns the
retry. Job record exported verbatim.
