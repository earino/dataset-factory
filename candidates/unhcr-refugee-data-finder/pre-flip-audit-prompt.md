INDEPENDENT PRE-PUBLICATION RE-AUDIT — UNHCR Asylum Corridor Application Doubling
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.
This is the second audit of this package: your 2026-10-28 verdict was DO NOT
PUBLISH in its present form as a benchmark with an "enforced isolated-rows"
protocol. The publisher accepted the verdict, recorded the operator's directive
that the benchmark framing is illustrative (never an enforced protocol), and
corrected the package. Your job now: verify the corrections are real, complete
and honest, and re-attack the same bytes.

WHERE THE DATA IS
Private repository: https://github.com/earino/unhcr-refugee-data-finder
Release tag: v2026.10. Five release assets (flat names):
  public-train.csv      343359 bytes  sha256 c7ebd552f1158bd5f470c495b027…
  public-eval.csv       195252 bytes  sha256 4b7f06c3afd9eec286652383d957…
  private-holdout.csv   202783 bytes  sha256 54decaaaf74eac1ea362bf1acf71…
  meta.json               1404 bytes  sha256 6620bdc91fdbc71b2d3fad6fb879…
  quality.json           19904 bytes  sha256 df419622d98ef2c8d084cb8c62a0…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: 6bd0c307d15d750085a77d4d…). All three CSVs are labeled;
the holdout file ships by design. The three CSVs are byte-identical to the
bytes you audited on 2026-10-28 (digests unchanged); meta.json and quality.json
changed. Download them; work locally.

WHAT THE PUBLISHER NOW CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per asylum corridor-year (country of origin O, country of asylum H, target year D+1), eligible at the instant by >= 500 government-procedure applications in year D and a published year-D-1 corridor value. 16 columns:
  `row_id`, `origin`, `asylum`, `target_year`, `apps_d`, `apps_d1`, `log_growth_d`, `surged_recently`, `host_apps_d`, `host_growth_d`, `origin_apps_d`, `origin_growth_d`, `corridor_age`, `target_date`, `surge_cluster`, `doubled`.
  Rows 3363 train / 1887 eval / 1962 holdout;
  positives 283 / 165 / 227; shipped label years train 2002-2016 (window start
  2001; label-year 2001 contributes no rows), eval 2017-2021, holdout 2022-2025.
- Prediction instant: the publication of the HDX refresh carrying complete year-D data (observed 2026-08-20 carrying complete data through 2025); every shipped feature reads published years <= D. `target_date` is a December-31 calendar identifier of the label year, NOT a publication timestamp.
- Isolated rows: a REQUIREMENT for honest evaluation, explicitly NOT enforced by
  the shipped illustrative runner, which passes the whole eval feature table to
  the predictor. The publisher quotes your own measured consequences (eval AUC
  0.975325 from eval features alone; holdout AUC 0.983034; 0.996970 across all
  splits; exact count recovery from next-year apps_d / two-years-later apps_d1)
  in quality.json, VERIFICATION.md, README.md, RELEASE_NOTES.md and the Hub
  card, and states that scores under unrestricted access are meaningless.
- Corrections you required, now claimed applied: missing-history exclusions
  377 (314 train / 31 eval / 32 holdout), not 386; all 14 runner inputs
  declared in the feature inventory (target_date and surge_cluster added);
  target_date documented as a calendar identifier; shipped label years
  corrected; the builder's own copy corrected so a rebuild reproduces the
  corrections.
- The stock XGBoost baseline is presented as ILLUSTRATIVE: eval AUC 0.5393
  (Brier 0.085099), trailing both persistence references (momentum 0.574165,
  surge flag 0.585619) with every paired interval containing zero - no
  demonstrated headroom, honestly disclosed.

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT doubled to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout: the panel
   property is unchanged BY DESIGN and is now disclosed - so verify the
   DISCLOSURE, not the absence, and hunt for anything NOT disclosed:
   - reproduce your 2026-10-28 frozen attacks on these bytes (donor join on
     (origin, asylum) at T -> T+1 copying surged_recently, with the
     missing-successor rule; count recovery from next-year apps_d / two-years
     later apps_d1) and check every published number that describes them is
     the number you measure;
   - then search for exposures BEYOND the disclosed ones: joins on row_id or
     other keys, duplicate/lookup tables across any column pair, free-text
     n-grams, date/order arithmetic, single-column dominance (flag any AUC in
     {0, 1} or > 0.95 on eval or holdout).
B. Reproduce the reference figures exactly from the shipped bytes: stock
   XGBoost eval AUC 0.5393 / Brier 0.085099; momentum 0.574165; surge flag
   0.585619; calendar/identity prior 0.540927; majority-class accuracy
   0.91256; the four paired row-bootstrap intervals.
C. Contract honesty of the CORRECTED package:
   - reconstruct the exclusion count from source: 377 (314/31/32), not 386;
   - all 7,212 target_date values are December 31 of the label year, and every
     document describes them as calendar identifiers;
   - the runner consumes exactly the 14 declared inputs (plus row_id handling
     and the target);
   - shipped train label years are 2002-2016;
   - NO residual enforcement claim anywhere in the package: search meta.json,
     quality.json, VERIFICATION.md, README.md, RELEASE_NOTES.md, the card and
     code/build.py for any remaining statement that isolation is enforced,
     guaranteed, or delivered by the shipped contract;
   - the corrected builder (code/build.py) reproduces the corrected strings, so
     a rebuild cannot resurrect the false claims.

REPORT
Verdict first: PUBLISH / DO NOT PUBLISH / PUBLISH WITH CONDITIONS.
Then: exact numbers for every check, freeze hashes, digest results, and an
explicit NOT COVERED section (what you did not try). Use PASS / FAIL / NOT
VERIFIED per finding; FAIL means observed contradiction, NOT VERIFIED means
you could not check. Sign and date it. Read-only audit: change no repository
content, publish nothing, repair nothing.
