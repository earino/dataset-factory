from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from factory.license_contract import build, validate, check_card
from factory.license_evidence import canonical, import_browser
from tests.license_fixture import prepare, TEMPLATE
from unittest.mock import patch
import importlib.util


class LicenseContractTests(unittest.TestCase):
    def test_one_source_generates_all_terms_and_preserves_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);generated=prepare(root)
            self.assertEqual(generated,validate(root,manifest={'licenses':generated['manifest']}))
            self.assertIn('Only our contribution',generated['license'])
            self.assertIn('Credit Example Source.',generated['card'])
            self.assertIn('CC-BY-4.0',generated['manifest']['source_data']['spdx'])

    def test_invented_ogl_same_licence_sentence_cannot_be_a_source_quote(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prepare(root)
            p=root/'LICENSE-EVIDENCE.json';plan=json.loads(p.read_text())
            plan['sources'][0]['grant']['quote']='You must redistribute under the same licence.'
            p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'exact quotation'):
                build(root)

    def test_handwritten_license_or_card_statement_and_manifest_drift_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);generated=prepare(root)
            p=root/'LICENSE.md';original=p.read_text();p.write_text(original+'All source data is CC0.\n')
            with self.assertRaisesRegex(ValueError,'LICENSE.md differs'):validate(root)
            p.write_text(original)
            with self.assertRaisesRegex(ValueError,'ungenerated'):
                check_card(TEMPLATE+'The upstream terms are CC0.\n',generated['card'],template=True)
            manifest={'licenses':dict(generated['manifest'])};manifest['licenses']['source_data']={}
            with self.assertRaisesRegex(ValueError,'manifest licences'):validate(root,manifest=manifest)

    def test_old_capture_can_be_audited_but_not_used_for_new_packaging(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prepare(root)
            build(root)
            with self.assertRaisesRegex(ValueError,'new source fetch'):
                build(root,fresh=True,now=datetime.now(timezone.utc)+timedelta(days=2))

    def test_contradictory_pages_do_not_get_a_precedence_interpretation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prepare(root)
            capture={'requested_url':'https://source.example/catalogue','final_url':'https://source.example/catalogue',
                     'status':200,'complete':True,'provider':'synthetic browser fixture',
                     'text':'Creative Commons Attribution-NoDerivatives 3.0. '+('Source terms are preserved. '*7),
                     'metadata':[],'links':['https://creativecommons.org/licenses/by-nd/3.0/']}
            export=root/'second.json';export.write_bytes(canonical(capture))
            import_browser(export,root/'licensing/catalogue',owner_hosts=['source.example'])
            p=root/'LICENSE-EVIDENCE.json';plan=json.loads(p.read_text())
            plan['sources'][0]['evidence'].append('licensing/catalogue');p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'conflicting'):build(root)

    def test_changed_source_bytes_and_false_cc_identifier_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prepare(root)
            p=root/'LICENSE-EVIDENCE.json';plan=json.loads(p.read_text());plan['sources'][0]['spdx']='CC0-1.0'
            p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'identifier differs'):build(root)
            plan['sources'][0]['spdx']='CC-BY-4.0';p.write_text(json.dumps(plan))
            p=root/'licensing/source/source-response.txt';p.write_bytes(p.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'changed'):build(root)

    def test_catalogue_cannot_be_left_out_of_terms_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);prepare(root)
            p=root/'LICENSE-EVIDENCE.json';plan=json.loads(p.read_text())
            del plan['sources'][0]['catalogue'];p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'catalogue and terms'):build(root)

    def test_hub_preparation_copies_the_same_evidence_and_refuses_a_missing_receipt(self):
        spec=importlib.util.spec_from_file_location('license_hub',Path(__file__).resolve().parents[1]/'scripts/hf-publish.py')
        hub=importlib.util.module_from_spec(spec);spec.loader.exec_module(hub)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);package=root/'release/example';generated=prepare(package)
            candidate=root/'candidates/example';candidate.mkdir(parents=True)
            (candidate/'card.md').write_text(TEMPLATE)
            manifest={'licenses':generated['manifest'],'dataset':'example','release_tag':'v1',
                      'artifact_version':'a'*64,'published':False,'splits':{}}
            hub.REPO_ROOT=root;hub.PACKAGE=package;hub.CANDIDATE='example';hub.BUILD=root/'hub'
            with patch.object(hub,'navigation_record',return_value=None):
                files=hub.build_package(manifest,'owner/example')
                for name in generated['receipt']['inputs']:
                    if name.startswith('licensing/'):
                        self.assertIn(name,files)
                        self.assertEqual((package/name).read_bytes(),(hub.BUILD/name).read_bytes())
                self.assertIn(generated['card'],(hub.BUILD/'README.md').read_text())
                (package/'license-receipt.json').unlink()
                with self.assertRaises(FileNotFoundError):hub.build_package(manifest,'owner/example')


if __name__=='__main__':
    unittest.main()
