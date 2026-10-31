# ea-permit-compliance-breach — discovery notes (closed at licence triage)

Probed 2026-10-31 (scheduled discovery session, UK regional focus). Publisher:
Environment Agency (England, GB). This lead was closed by the cheapest veto, before
any schema or volume probe was spent — the order of work the discovery skill
requires.

## The lead

Defra Data Services Platform dataset "Compliance Classification Scheme"
(https://environment.data.gov.uk/dataset/5f2149c0-d465-11e4-b632-f0def148f590):
yearly ZIPs 2014-2024 of condition breaches on Environmental Permitting Regulations
(2010) waste and installation permits. The candidate task idea: predict which
permitted sites will incur a recorded breach next year from permit/site features and
prior history — the same regulatory-inspection-targeting utility pattern the US EPA
already operates (RCRA violation-forecasting model with UChicago E&E Lab, scores
published on ECHO), which supported usefulness, not mirroring.

## The veto (read 2026-10-31, quoted verbatim in record.json license_evidence)

The dataset page's Licence section names the "Environment Agency Conditional
Licence", attribution "© Environment Agency copyright and/or database right 2025.
All rights reserved", with special conditions: use "for your internal or personal
purposes", sublicensing only "under a written licence", and "The period of permitted
use is one year." Derived rows cannot be published under that instrument. The same
page also shows the trap that makes triage necessary: "There are no public access
constraints to this data" — open access, closed redistribution.

licence_class D on the publisher's own instrument.

## Scope of the rejection

This rejection is for THIS dataset/instrument only. It does not generalize to the
Environment Agency's other products: the EA's bathing-water, flood-warning and
river-level products are published under OGL and remain viable sources (two EA
candidates are already investigating in the queue). Every EA dataset must be triaged
on its own page, because the Agency mixes OGL and Conditional licences across its
catalogue.

## Reopen condition

EA relicensing this dataset (or a successor compliance product) under OGL, or a
candidate-specific operator decision to seek written permission — a class C enquiry
this project does not send unsolicited under the standing policy.
