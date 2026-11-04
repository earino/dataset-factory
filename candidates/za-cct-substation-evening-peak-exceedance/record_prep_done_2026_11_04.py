#!/usr/bin/env python3
"""Mark this session's za-cct packaging-prep steps done in next_action (2026-11-04)."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORD = ROOT / "candidates" / "za-cct-substation-evening-peak-exceedance" / "record.json"

OLD_II = ("(ii) candidates/za-cct-substation-evening-peak-exceedance/license.json (class A, "
          "City of Cape Town Open Data portal terms + Open Data Policy 27781, evidence already "
          "in record.license_evidence; follow the cqc license.json shape) and release.json "
          "(construction commit + build/script digests from the za-cct-001 bundle-owner "
          "record at .factory/za-cct-001/, staging release 432591871; commands gate/baseline/"
          "get_dataset; layout public/train.csv, public/eval.csv, private/holdout.csv, "
          "meta.json, quality.json); ")

NEW_II = ("(ii) DONE 2026-11-04 (this session): suitability/za-cct-substation-evening-peak-"
          "exceedance.json written for artifact 9f2e10ce... with planned release_tag v2026.11 "
          "(validated clean against factory.suitability.validate; update it in the same change "
          "if the tag differs); candidates/za-cct-substation-evening-peak-exceedance/license.json "
          "written (LicenseRef-CityOfCapeTown-OpenDataTerms for the source, MIT code, CC0-1.0 "
          "compilation, evidence from record.license_evidence); release.json written "
          "(construction commit c57e3711fe6f9e9db8f58d1a5f01f5b64a3ba4b5 with build.py/run.sh/"
          "score.py digests verified against that commit, source pins, commands, layout, and the "
          "decision-(a) note with the full comparison ladder); ")

OLD_I = ("(i) suitability record "
         "suitability/za-cct-substation-evening-peak-exceedance.json written this session for "
         "artifact 9f2e10ce485635f65e695072e2bbd904024ebf58b1465d12fb969f8bb0692180 with "
         "planned release_tag v2026.11 (update it in the same change if the tag differs); ")

NEW_I = ("(i) DONE 2026-11-04 (this session): suitability record "
         "suitability/za-cct-substation-evening-peak-exceedance.json written for "
         "artifact 9f2e10ce485635f65e695072e2bbd904024ebf58b1465d12fb969f8bb0692180 with "
         "planned release_tag v2026.11 (validated clean against factory.suitability.validate); ")


def main() -> int:
    record = json.loads(RECORD.read_text())
    na = record["next_action"]
    assert OLD_I in na and OLD_II in na, "expected pipeline steps not found in next_action"
    na = na.replace(OLD_I, NEW_I).replace(OLD_II, NEW_II)
    record["next_action"] = na
    record["updated_at"] = "2026-11-04T14:40:00Z"
    RECORD.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print("next_action updated: (i) and (ii) marked DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
