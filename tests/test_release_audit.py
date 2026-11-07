"""The model may cite evidence and propose attacks, but cannot waive gates."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from factory import release_audit as audit
from factory.leakage_battery import digest
from tests.test_adversarial_programs import attack, col


class ModelContractTests(unittest.TestCase):
    def setUp(self):
        text='This is the full supplied source evidence for reviewing the task.'
        self.value={'binding':{'artifact_digest':'a'*64},'documents':{
            'quality.json':{'sha256':'b'*64,'text':json.dumps({'target':'label'})},
            'README.md':{'sha256':'c'*64,'text':text}}}
        self.response={'version':'1.0.0','binding_digest':digest(self.value['binding']),
            'verdict':'pass','reviewed_files':{n:e['sha256'] for n,e in self.value['documents'].items()},
            'coverage':{n:'A substantive category analysis citing the available evidence and explaining '
                          'the remaining uncertainty without claiming unmeasured results.' for n in audit.CATEGORIES},
            'findings':[],'programs':[attack(col('value'))]}

    def test_programs_bind_exact_artifact_and_prompt_is_deterministic(self):
        result=audit.validate_response(self.value,self.response)
        self.assertEqual('a'*64,result['artifact_digest'])
        self.assertEqual(self.response['programs'],result['programs'])
        self.assertEqual(audit.prompt(self.value),audit.prompt(copy.deepcopy(self.value)))
        self.assertIn('BEYOND the fixed battery',audit.prompt(self.value))

    def test_missing_category_file_or_stale_binding_refuses(self):
        for kind in ('category','file','binding','target'):
            response=copy.deepcopy(self.response)
            if kind=='category':response['coverage'].pop('licensing')
            if kind=='file':response['reviewed_files'].pop('quality.json')
            if kind=='binding':response['binding_digest']='d'*64
            if kind=='target':response['programs'][0]['expression']=col('label')
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                audit.validate_response(self.value,response)

    def test_finding_must_quote_real_hash_bound_source(self):
        finding={'category':'claims','severity':'P0','explanation':'The claimed property contradicts the supplied evidence and blocks release.',
                 'evidence':{'file':'README.md','sha256':'c'*64,'quote':'full supplied source evidence'}}
        self.response.update(verdict='block',findings=[finding])
        audit.validate_response(self.value,self.response)
        for key, value in (('file','absent.md'),('sha256','e'*64),('quote','invented quotation')):
            response=copy.deepcopy(self.response);response['findings'][0]['evidence'][key]=value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,'invented source'):
                audit.validate_response(self.value,response)
        self.response['verdict']='pass'
        with self.assertRaisesRegex(ValueError,'contradicts blocking'):
            audit.validate_response(self.value,self.response)

    def test_incomplete_is_not_a_pass_and_unsupported_code_is_refused(self):
        self.response['verdict']='incomplete'
        audit.validate_response(self.value,self.response)
        self.response['programs'][0]['expression']={'op':'python','code':'print(1)'}
        with self.assertRaisesRegex(ValueError,'unknown attack'):
            audit.validate_response(self.value,self.response)

    def test_current_deterministic_refusal_precedes_model_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);package=root/'release/example';package.mkdir(parents=True)
            (package/'MANIFEST.json').write_text(json.dumps({'dataset':'example','published':False}))
            with patch.object(audit,'check_package',return_value=(['known recovery'],[])), \
                 patch.object(audit,'qualification_check',return_value=[]), \
                 patch.object(audit,'publication_check',return_value=([],[])):
                with self.assertRaisesRegex(ValueError,'known recovery'):
                    audit.capsule(root,'example')


if __name__=='__main__':unittest.main()
