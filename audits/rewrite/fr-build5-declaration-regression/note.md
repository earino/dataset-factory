FR build-5 ran after the additional worker allowance was authorized.
Staging release439516409, manifest asset728607727, worker343.2seconds,
failed gate1.6.1. Qualification asset728607354 and quality728607185
were inspected directly. No CSV was downloaded and no score is accepted.

The code SHA256 a3c373bd155c259d9e3ec881e49dc60c855bdf6ec70ebe3e70bd22efcb9c688e
was verified against the source.tar asset hash and worker source_files pin.
It retains train-only agency label aggregates, strict maturity cutoff, and
uses _smoothed_rate(0,0) for agencies absent from training. Existing code
also checks noninterference from flipping scored labels. This is code
inspection, not qualification acceptance or an exhaustive leakage proof.

Eight actual declaration failures remain: use/training_label_timing/vintage
moved outside evaluation_contract; features_documented_at omitted;
publication_date shipped but missing from carry declarations and wrongly
included among label-source columns; high-cardinality declarations lost;
event-time lag representation regressed to D/0. A publication date is not
itself a forbidden feature. Repair the declarations to match the actual NPRM
input and retrospective scope; do not weaken the gate or reset retry bounds.
