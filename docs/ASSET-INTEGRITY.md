# Release asset integrity

`factory/asset_integrity.py` closes the architecture review's package-hash gap.
The old package loop hashed only entries in `package_files`; separately declared
release assets could be omitted there and escape direct hashing. Every asset now
has its actual size and SHA-256 compared with the manifest whenever it is present.
The check also requires agreement with `files`, exact checksum coverage and the
loader's static `EXPECTED`, `LAYOUT` and `TAG`. Loader code is parsed, never run.
Duplicate checksum entries, unsafe paths and links refuse inspection.

`check-package.py <package>` is full verification and refuses absent assets.
Coordinator/site preparation uses `--external-assets` (the Python API uses
`external_assets=True`) to inspect only metadata for absent data files. Output
states that those bytes were **not verified**. New releases still need their
current full-artifact qualification receipt; external mode cannot waive it.
Any locally present file is hashed in both modes.

An offline read-only comparison over all 14 frozen packages passes metadata
consistency with historical loader warnings for ABS visitor arrivals and Malaysia
PriceCatcher: their literal `EXPECTED` differs from their manifests. These findings
were discovered on committed package code, without downloading data. Frozen package
bytes, manifests and tags remain unchanged. Only exact loader hashes in the frozen
registry receive a warning; a changed loader or a new package fails.

This is the integrity portion of R3 and review item 2. It does not complete
prevalence, dictionary, interval, licence or adversarial-audit acceptance. Full
asset verification and the 14-package leakage comparison still run on workers.
