UCMR5 fresh semantic review (rw-2ce60e8ae8f7-evaluate-2, completed ~18:39Z;
observed under 7b77595 deploy at 18:43:22Z - scheduling correction:
admitted attempts first, then publication > review > construction >
discovery, oldest-first; 19:07 cutoff cron f0852e8c6392 preserved).

Review outcome: verdict "repair" with material improvement - the reason
opens by affirming the source, target direction/units, half-open split
windows, one-row-per-PWS selection, prior UCMR3 join and EPA public-domain
basis as SOUND, and confirms the previous empty-ADE-feature defect is
FIXED. Five new findings are check-quality/semantic refinements:
0. "Frozen label rule recomputed" check is tautological and cannot fail.
1. prior_ucmr3_max_pfoa_pfos feature text does not match the code for
   systems with only non-detect UCMR3 rows.
2. Stated population broader than the code's effective population
   (earliest sample selected before window assignment; 234 systems).
3. "UCMR 5 entry-point samples retained" check does not verify non-EP
   rows are excluded.
4. "PFOA and PFOS analytes recognized" check does not verify the negative
   part (unrelated analytes not captured).
Usage: 6 calls, 203,582 in / 53,875 out, 7 web tool results, 356.4 s.
The corrected routing returned the candidate to build with findings
retained - build-7 repair pending.

Also: CMS build-5's documentation-URL 403 failure (staging 438439314,
operator-verified) exhausted its 5-attempt allowance -> CMS source-000012
DEFERRED at 18:44. ClinicalTrials source-000014 remains stuck behind the
reconcile guard since its successful construction at 18:21Z with no
worker launch record by 18:44Z - flagged for the owner as a possible
reconcile defect. No queue edits or extra calls made.
