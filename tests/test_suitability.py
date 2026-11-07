import copy
import json
import unittest
import tempfile
from pathlib import Path
from factory.suitability import validate, public_projection, markdown, publication_check

ROOT=Path(__file__).resolve().parents[1]
class SuitabilityTests(unittest.TestCase):
    def setUp(self):
        self.record=json.loads((ROOT/'suitability/austin-911-response.json').read_text())
        self.manifest=json.loads((ROOT/'release/austin-911-response/MANIFEST.json').read_text())

    def test_wrong_artifact_cannot_borrow_a_review(self):
        self.record['artifact_version']='0'*64
        self.assertTrue(validate(self.record,self.manifest,ROOT))

    def test_bounded_pass_does_not_certify_forecasting(self):
        self.record['decision']='retain'
        self.assertTrue(validate(self.record,self.manifest,ROOT))

    def test_missing_evidence_is_rejected(self):
        self.record['evidence']=[]
        self.assertTrue(validate(self.record,self.manifest,ROOT))

    def test_public_projection_excludes_private_evidence_and_operations(self):
        value=public_projection(self.record)
        self.assertNotIn('evidence',value)
        self.assertNotIn('required_actions',value)
        self.assertNotIn('evidence',value['cross_row_audit'])
        self.assertIn('development/validation',markdown(value))
        self.assertNotIn('issue #17',markdown(value))

    def test_current_cpcb_recovery_blocks_regardless_of_scope_or_waiver(self):
        manifest=json.loads((ROOT/'release/cpcb-aqi-exceedance/MANIFEST.json').read_text())
        record=json.loads((ROOT/'suitability/cpcb-aqi-exceedance.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'suitability').mkdir()
            record['evidence']=[{'claim':'test','source':'https://example.org/test','detail':'test'}]
            for access in ('isolated_rows','chronological','common_cutoff_batch'):
                for decision in ('retain_restricted','rebuild_before_use','retire'):
                    record.update(evaluation_access=access,decision=decision,
                                  operator_waiver={'artifact_version':manifest['artifact_version'],'approved':True})
                    (root/'suitability/cpcb-aqi-exceedance.json').write_text(json.dumps(record))
                    errors,_=publication_check(root,manifest)
                    self.assertTrue(errors,(access,decision))

    def test_frozen_diagnostics_are_not_new_publication_permission(self):
        package=ROOT/'release/abs-visitor-arrivals-direction'
        manifest=json.loads((package/'MANIFEST.json').read_text())
        errors,notes=publication_check(ROOT,manifest,package=package)
        self.assertFalse(errors,errors)
        self.assertTrue(any('not new-release clearance' in n for n in notes),notes)
        self.assertTrue(publication_check(ROOT,manifest)[0])
        cpcb=json.loads((ROOT/'release/cpcb-aqi-exceedance/MANIFEST.json').read_text())
        self.assertTrue(publication_check(ROOT,cpcb,package=package)[0])

    def test_missing_or_stale_review_cannot_clear_publication(self):
        from tests.suitability_fixture import prepare
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.assertTrue(publication_check(root,self.manifest)[0])
            record=prepare(root,self.manifest)
            self.assertFalse(publication_check(root,self.manifest)[0])
            record['artifact_version']='0'*64
            (root/'suitability/austin-911-response.json').write_text(json.dumps(record))
            self.assertTrue(publication_check(root,self.manifest)[0])
