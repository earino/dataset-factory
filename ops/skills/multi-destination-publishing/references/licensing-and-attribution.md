# Licensing and attribution for a published artifact

Depth for the three-field split in the skill body. Use when a release carries derived data, or when
some of the files being redistributed came from somewhere else.

## The three fields

| field | question it answers | typical answer |
| --- | --- | --- |
| code / documentation | what terms do the scripts, docs and card carry? | a permissive software licence you are entitled to grant |
| your rights in the compilation | what are you dedicating about the derived work? | a public-domain dedication or a permissive licence, scoped to your contribution |
| the source | what do the underlying data's terms say, and what must be preserved? | the source's own designation, attribution and citation, unchanged |

Never collapse these into one field. "Public domain source" does not answer the code question, and
"MIT" does not answer the source question - each is a separate claim with a separate owner.

## Declaration shape

Two files, one generated block:

- a **per-artifact declaration** next to the artifact: the chosen identifiers, the copyright line,
  any redistributed files with their source, the permission and the preserved credits, the source's
  designation with the evidence that was actually read, its attribution string and its suggested
  citation, and the scope sentence;
- a **standing policy** shared by the series: the defaults, the compatibility rule (terms follow the
  source; a permissive default is not an override), the attribution rules, and the refusal cases;
- the **generated manifest block**: the release manifest carries both, written by the manifest
  generator. Hand-editing the manifest is how the terms disappear on the next regeneration.

## What a package check should refuse

- no declared terms at all;
- a named licence file that is not shipped in the package;
- a publication claim (a published flag, a public destination) while terms are undeclared or a
  destination is unverified;
- a source entry with no designation recorded - the source's terms must be recorded, not overwritten
  by the compilation's.

## Scope wording

One sentence that does the work, in the notice and on every destination:

> The dedication covers our contribution - the selection, the derived label, the partition, the
> packaging. It does not cover or relicense the source's data, which keeps its own designation.

Then state the derived-work labelling: the artifact is derived from the source organisation's open
data, is labelled as derived, and is not an official product of it. Where a source forbids
presenting modified content as official, that constraint belongs in the notice as a release
condition, not in a footnote.

## Rendering on each destination

- The registry card carries the compilation's terms in its own licence field, and the code's terms
  in the body, both generated from the manifest.
- The source repository carries the full notice plus the canonical licence texts as files, so a
  reader can obtain the exact terms rather than a paraphrase.
- The citation and attribution strings are copied from the declaration verbatim - including any
  version or artifact identifier the citation contains - so the two destinations quote the same
  sentence.

## Corrections

Terms chosen now apply to the artifact as accepted; changing them later is a new version, not an
edit. When a licence decision is completed for an artifact that is still private, updating it in
place is legitimate - state that the data digests are unchanged, because a licence edit otherwise
looks like a content change to anyone reviewing the diff.
