# Source-owned licence evidence at packaging

New releases require readable captured source terms, an exact quotation declaration,
generated licence documents and a reproducible receipt. A claim in a candidate's
old `license.json` cannot substitute for this evidence. The previous record remains
historical research; new `MANIFEST.json` terms come from the captured-source contract.

## Capture before preparing a package

Capture both the source catalogue's designation and the applicable terms. A page
that contains both may serve both roles. Every capture records the requested URL,
final URL, source owner hosts, HTTP status, full extracted text, licence metadata,
links, channel, timestamp, raw response hash and inspection result. Captures are
immutable directories: failed requests are retained, and another attempt uses a
new directory. Each file is bounded to 240 KiB; incomplete/truncated evidence fails.

```bash
python3 scripts/license-evidence.py fetch https://publisher.example/terms \
  preparation/licensing/terms --owner-host publisher.example
python3 scripts/license-evidence.py verify-capture preparation/licensing/terms
```

An HTTP challenge or unreadable page is a refusal, not a licence finding. Use the
existing native browser capability when available; do not install a browser stack
or bypass a challenge. Export its actually observed page as a bounded JSON object:

```json
{
  "requested_url": "https://publisher.example/terms",
  "final_url": "https://publisher.example/terms",
  "status": 200,
  "complete": true,
  "provider": "name of the native browser tool used",
  "text": "The complete readable text actually observed, including the footer",
  "metadata": [{"key": "license", "value": "the actual metadata value"}],
  "links": ["https://publisher.example/the-actual-linked-terms"]
}
```

`complete` must be false when the browser cannot expose the full text, metadata or
footer. Never manufacture a successful observation from old notes. The browser
capture import preserves the original export and rechecks it with the same rules:

```bash
python3 scripts/license-evidence.py import-browser browser-capture.json \
  preparation/licensing/terms-browser --owner-host publisher.example
```

The hosted native browser is the fallback capability; this is not an automated
CAPTCHA solver. If it is unavailable or cannot read the page, packaging remains
refused while other independent work continues.

## Declare exact quotations, then generate

Place `LICENSE-EVIDENCE.json` in the new package preparation directory. Each source
has a distinct id, evidence-directory list, catalogue and terms roles, source
identifier and references to exact text. Attribution and suggested citation, when
provided by the source, must be preserved verbatim. The complete captured text is
also included in LICENSE.md, so selecting a short quotation does not discard the
rest of the terms.

```json
{
  "version": 1,
  "sources": [{
    "id": "publisher",
    "spdx": "CC-BY-4.0",
    "evidence": ["licensing/catalogue", "licensing/terms"],
    "catalogue": "licensing/catalogue",
    "terms": "licensing/terms",
    "designation": {"evidence": "licensing/catalogue", "quote": "exact designation"},
    "grant": {"evidence": "licensing/terms", "quote": "exact grant text"},
    "attribution": {"evidence": "licensing/terms", "quote": "exact attribution"},
    "citation": {"evidence": "licensing/catalogue", "quote": "exact suggested citation"}
  }]
}
```

Unknown/custom instruments use `LicenseRef-...` and retain their verbatim designation.
Known Creative Commons identifiers must agree with the captured family/version.
Conflicting families or versions in text, metadata or links fail, both within a
page and across the catalogue/terms pages. There is no dataset-over-footer override.
The parser recognizes a finite set of CC spellings; it is not a general legal
interpreter. Source scope, missing attribution/citation selections and compatibility
remain explicit duties of the independent adversarial audit.

The card template must contain `{LICENSE_METADATA}` in its frontmatter and exactly
one `{LICENSE_BLOCK}` in its body. Remove handwritten licence claims from the card;
the validator refuses them outside the generated block. Prepare the policy-named
MIT and compilation licence files, then run:

```bash
python3 scripts/license-evidence.py generate preparation \
  --card-template candidates/example/card.md
python3 scripts/license-evidence.py check preparation
```

Generation requires captures from the last 24 hours and exclusively creates
LICENSE.md, card.md and license-receipt.json. It will not overwrite an existing
package. The receipt binds source files, selected quotations, own-term files,
policy and implementation. Own compilation terms cover only our contribution;
the generated card uses `license: other` with a link to the preserved source terms,
never a blanket CC0 designation for upstream data.

`release-manifest.py` requires the same fresh evidence and exact generated documents
before its first write. `check-package.py` revalidates the stored capture, receipt,
manifest and generated documents without expiring a historical capture. Claims
validation excludes a licence block from numeric prose checks only after verifying
the complete licence contract. Hugging Face preparation validates the contract and
copies the captured evidence and receipt alongside the generated card. GitHub's
package inventory includes the same files.

## Historical evidence and acceptance

Existing public releases remain frozen. An exact frozen manifest plus its pinned
licence files can be inspected with an explicit historical-evidence-gap warning;
it does not receive a new captured-source receipt or new-release clearance. Changes
to those files lose that allowance. Blocked private packages have no exemption.

The captured Alberta response in `audits/resilience/licensing-2026-11-07/` is HTTP
403 and fails readability. The SINASC response is readable but contains CC-BY
metadata together with CC-BY-ND 3.0 footer terms; it fails consistency. These
preserved responses prove those refusals, not a legal conclusion about either source.
Synthetic transport tests verify changed bytes, invented OGL same-licence text,
cross-page conflicts, stale captures and handwritten card/manifest drift. They do
not replace A3/A4 runs on the original blocked packages.
