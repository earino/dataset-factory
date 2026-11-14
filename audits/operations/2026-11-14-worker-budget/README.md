# Worker budget correction, 2026-11-14

Eduardo reported November Hetzner console usage of EUR16.21. Scout read back
EUR44.94 retained reservations across 292 deleted workers, zero live workers,
and EUR0.06 construction headroom under the unchanged EUR50 total / EUR5 reserve.
The dashboard estimated EUR4.94 because it prorated worker hours.

Hetzner bills each server for whole hours, rounding up, including short jobs:
https://docs.hetzner.com/cloud/billing/faq/ (checked 2026-11-14).

Admission now derives completed charges from confirmed deleted worker timestamps,
rounding up at the launch-recorded policy ceiling. Active, unidentified and
incomplete records retain their original reservation. Overruns can exceed that
reservation. Full charges remain attributed to both months for boundary jobs.
Original job records, configured allowance, reserve and expiry schedules stay intact.

Dashboard estimates use whole-hour billing at launch-recorded provider rates;
the page separately shows conservative admission accounting and construction
headroom. Neither is described as an invoice. No provider-console billing API
or invented actual-spend figure is introduced.

Validation: 78 focused worker/budget/dashboard tests passed (one skip). Full clean
checkout and CI results plus deployed readback are recorded during closeout.
