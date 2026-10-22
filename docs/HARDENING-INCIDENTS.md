# Hardening incident evidence

## 2026-10-22: automatic edits entered main during research close-out

While engineering PRs remained unmerged, main advanced from `beab726` to
`f42e5b0`. The existing watcher close-out committed the worker blob-ceiling fix
in `e219465`, together with two previously captured, unreviewed project-skill
patches. The release-skill patch said to remove a model number when a baseline
beats it. That is not acceptable scientific reporting: preserve both measured
results and narrow unsupported claims. The patches remain available in Git
history and Scout's drift captures; they are not adopted as instructions.

The new EUTL private package in `fd29c3e` is independent research work and is
preserved. Subsequent CI repairs `0ea6a0f` and `f42e5b0` rewrote four existing
manifests: absent local CSVs disappeared from `package_files`, publication notes
changed, and TSB gained explicit `hub_paths`. These are precisely the consumer
problems handled by the schema PR's offline package validation and read-time
Hub-path normalization. Correct the readers, not historical release bytes.

The corrective change restores only these six files byte-for-byte from
`beab726`, the engineering baseline, without rewriting history:

- `release/abs-visitor-arrivals-direction/MANIFEST.json`
- `release/my-pricecatcher-weekly-increase/MANIFEST.json`
- `release/nhs-ae-four-hour-decline/MANIFEST.json`
- `release/tsb-railway-occurrence-casualty/MANIFEST.json`
- `skills/dataset-qualification/SKILL.md`
- `skills/dataset-release/SKILL.md`

This is a restoration of the original records after concurrent changes, not an
edit to make an artifact fit a schema. The qualification executable is unchanged.
TSB's newly explicit candidate descriptor is retained for future construction;
the old release stays frozen. No public destination, dataset tag, CSV, worker
ledger, or newly packaged EUTL file is changed by the correction.

Anonymous bounded reads of Hugging Face's current MANIFEST.json on 2026-10-22
confirmed ABS and PriceCatcher still exactly match the original factory bytes:

- ABS: `117fc83e1f27f504568b25b1626b12bfb02b21ac9e14a2e28db3c4bb64524d9b`
- PriceCatcher: `12f43f4c7be1feb0ecb5485764c27453318bfeaab698ffcc2ec5f891576e12b7`

TSB's remote hash was
`4c37e12ed6837c47f5cb31f5fff12f904ee0c62a05ad978cc8771907b11633d2`;
its pre-existing differences from the original factory manifest are only
`publication_note`, `published`, and `visibility`. It is left untouched. The
original factory TSB hash restored here is
`400ec5cb12cdc9800c711ecbec63d8f09c3449a46529acebca6a86cc1475c85c`.
NHS's archived factory hash is
`7040d6e6a213e7485fe59caf327319b99f8a5e609dd4f81d0dd264602aaae5f0`.

Scout separately reported no public-destination uploads from these repair
commits, based on destination timestamps and session commands. Its later profile
skill edits were preserved under `/opt/data/curator-drift/2026-10-22T1915/`.
These are point-in-time observations, not a guarantee that live writers stopped.

Before correction, integration at `31b9031` ran 523 tests and failed three:
missing-CSV metadata, TSB path interpretation, and reviewed skill inventory.
No assertions or pins were weakened to accommodate those failures. Deployment
must use fresh source/live drift checks after holding the automatic writers,
and must preserve new drift before any restoration on the host. All engineering
work remains on branches pending the operator's revision of “do not merge.”

### Follow-up: candidate paths cannot override the frozen release

The newly added TSB candidate `hf_paths` mapped CSVs to logical paths such as
`public/train.csv`. Anonymous bounded Hub metadata reads on 2026-10-22 showed
both `v2026.10` (`e6fe2a2c9d629b8a9a6f1efa6c5e7158b2e4a050`) and then-current
`main` (`cc1ed9c120c405cd9da0b8ded8100d217dae18ed`) contain the original flat
`data/public-train.csv`, `data/public-eval.csv`, and `data/private-holdout.csv`.
The publication CLI had still taken target paths from the mutable candidate,
while its card used the manifest. It now takes both from the release record:
explicit manifest `hub_paths`, otherwise the original flat asset convention.
A candidate edit cannot redirect verification or publication of an existing
release. New regressions cover candidate drift and NOAA's explicit structured
layout. No artifact, destination record or remote tag is rewritten.
