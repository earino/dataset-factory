import copy
import json
import unittest
from pathlib import Path
from factory.suitability import validate, public_projection, markdown

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
