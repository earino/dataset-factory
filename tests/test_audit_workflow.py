"""Worker/control integration on tiny unit fixtures, never real acceptance evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from factory import audit_workflow as workflow
from factory import release_audit as audit
from factory import adversarial_execution as execution
from factory import audit_model_session
from factory.leakage_battery import digest
from tests import test_artifact_checks as artifact_fixtures
from tests.suitability_fixture import prepare as review_fixture
from tests.test_adversarial_programs import attack, const

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_audit_worker_test',ROOT/'scripts/audit-release-worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        for name in audit.implementation(ROOT):
            dest=self.root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
        self.package=self.root/'release/example';self.package.mkdir(parents=True)
        helper=artifact_fixtures.PackageCheckTests();self.addCleanup(helper.doCleanups)
        helper._build(self.package)
        manifest=json.loads((self.package/'MANIFEST.json').read_text())
        review_fixture(self.root,manifest)
        (self.package/'DESTINATIONS.json').write_text(json.dumps({
            'artifact_version':manifest['artifact_version'],'release_tag':'v1','destinations':{
                'github':{'repo':'owner/example','release_id':1,'release_tag':'v1','target_commit':'a'*40,
                          'private':True,'verified':True,'verified_at':'2026-11-07T00:00:00Z'},
                'huggingface':{'repo':'owner/example','revision':'v1','commit':'b'*40,
                          'private':True,'verified':True,'verified_at':'2026-11-07T00:00:00Z'}}}))
        self.value=audit.capsule(self.root,'example')
        self.response={'version':audit.VERSION,'binding_digest':digest(self.value['binding']),
            'verdict':'pass','reviewed_files':{n:v['sha256'] for n,v in self.value['documents'].items()},
            'coverage':{n:'This is a unit-test model contract only. It does not represent an actual model '
                          'review or an acceptance result on a real dataset.' for n in audit.CATEGORIES},
            'findings':[],'programs':[attack(const(.5))]}
        self.capsule=self.root/'capsule.json';self.capsule.write_text(json.dumps(self.value))
        self.response_path=self.root/'response.json';self.response_path.write_text(json.dumps(self.response))

    def test_full_worker_checks_and_both_batteries_run_without_mutation(self):
        before=execution.artifact_identity(self.package)
        result=worker.run(self.root,self.capsule,self.response_path,self.package,self.root/'out')
        self.assertTrue(result['ok'],result)
        self.assertTrue(result['completed']);self.assertFalse(result['release_authorized'])
        self.assertEqual(before,execution.artifact_identity(self.package))
        names={p.name for p in (self.root/'out').iterdir()}
        self.assertTrue({'battery.json','model-attacks.json','model-freeze.json','autonomous-audit.json'}<=names)
        self.assertTrue(any(n.startswith('results-') for n in names))
        self.assertFalse(any(n.endswith('.zip') for n in names))

    def test_mutated_row_file_fails_before_any_attack(self):
        path=self.package/'public/eval.csv';path.write_text(path.read_text()+'\n')
        with patch.object(execution,'freeze') as freeze:
            with self.assertRaisesRegex(ValueError,'fetched data differs'):
                worker.run(self.root,self.capsule,self.response_path,self.package,self.root/'out')
            freeze.assert_not_called()

    def test_changed_code_or_model_binding_cannot_reuse_capsule(self):
        path=self.root/'factory/adversarial_programs.py';path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'implementation differs'):
            worker.run(self.root,self.capsule,self.response_path,self.package,self.root/'out')
        self.response['binding_digest']='d'*64;self.response_path.write_text(json.dumps(self.response))
        with self.assertRaisesRegex(ValueError,'contract/binding'):
            worker.run(self.root,self.capsule,self.response_path,self.package,self.root/'other')

    def test_unsafe_staging_or_review_cannot_reach_model_context(self):
        p=self.package/'DESTINATIONS.json';dest=json.loads(p.read_text());dest['destinations']['github']['private']=False
        p.write_text(json.dumps(dest))
        with self.assertRaisesRegex(ValueError,'private staging'):
            audit.capsule(self.root,'example')
        dest['destinations']['github']['private']=True;p.write_text(json.dumps(dest))
        review=self.root/'suitability/example.json';value=json.loads(review.read_text())
        value['cross_row_audit']['status']='recovery_demonstrated';review.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'exact label recovery'):
            audit.capsule(self.root,'example')

    def test_candidate_queue_fields_do_not_make_review_evidence_self_referential(self):
        folder=self.root/'candidates/example';folder.mkdir(parents=True)
        path=folder/'record.json';path.write_text(json.dumps({'id':'example','measurement':'fixed','awaiting_operator':False}))
        first=audit.review_input(self.root,'example','candidates/example/record.json')
        path.write_text(json.dumps({'id':'example','measurement':'fixed','awaiting_operator':True,
                                    'autonomous_audit':{'directory':'new'},'next_action':'review'}))
        self.assertEqual(first,audit.review_input(self.root,'example','candidates/example/record.json'))
        path.write_text(json.dumps({'id':'example','measurement':'changed'}))
        self.assertNotEqual(first,audit.review_input(self.root,'example','candidates/example/record.json'))

    def test_bare_or_forged_operator_queue_claim_is_false(self):
        record={'id':'example','status':'packaged','awaiting_operator':True}
        self.assertFalse(workflow.queue_ready(self.root,record))
        record['autonomous_audit']={'directory':'../outside','sha256':'a'*64}
        self.assertFalse(workflow.queue_ready(self.root,record))

    def model_directory(self, directory):
        directory.mkdir(parents=True)
        policy={'version':1,'reviewed':True,
                'source_sha256':{name:'d'*64 for name in audit_model_session.RUNTIME_FILES}}
        path=self.root/'config/adversarial-runtime.json';path.write_text(json.dumps(policy))
        for name,value in (('capsule',self.value),('response',self.response),
                           ('proposal',audit.validate_response(self.value,self.response)),
                           ('usage',{'session_id':'unit-session','source':'oneshot','executed_tools':0,
                                     'attempted_tool_calls':0,'tokens':100})):
            (directory/(name+'.json')).write_text(json.dumps(value))
        (directory/'prompt.txt').write_text(audit.prompt(self.value))
        binding=self.value['binding']
        session={'version':audit.VERSION,'status':'completed','binding_digest':digest(binding),
                 'source':'oneshot','session_id':'unit-session','verdict':'pass',
                 'runtime':{'source_sha256':policy['source_sha256'],
                            'policy_sha256':audit.sha256(path),'preflight_empty_definitions':True},
                 'staging_readback':{'destinations_sha256':binding['destinations_sha256'],
                                    'github_commit':'a'*40,'huggingface_commit':'b'*40,'both_private':True},
                 'prompt_sha256':audit.sha256(directory/'prompt.txt')}
        for name in ('capsule','response','usage','proposal'):
            session[name+'_sha256']=audit.sha256(directory/(name+'.json'))
        (directory/'session.json').write_text(json.dumps(session))
        (directory/'attempt.json').write_text(json.dumps({'status':'pending'}))
        return directory

    def test_model_evidence_cannot_substitute_prompt_program_or_runtime(self):
        directory=self.model_directory(self.root/'model')
        audit.model_evidence(self.root,directory)
        for name in ('prompt.txt','proposal.json','response.json','usage.json'):
            path=directory/name;original=path.read_bytes();path.write_bytes(original+b'\n')
            with self.subTest(name=name),self.assertRaises(ValueError):audit.model_evidence(self.root,directory)
            path.write_bytes(original)
        p=self.root/'config/adversarial-runtime.json';p.write_text(json.dumps({'version':1,'reviewed':False}))
        with self.assertRaisesRegex(ValueError,'unreviewed'):audit.model_evidence(self.root,directory)

    def fake_api(self):
        manifest=json.loads((self.package/'MANIFEST.json').read_text())
        class API:
            def request(_self,method,path,*args,**kwargs):
                if method!='GET':raise AssertionError('audit preparation must not mutate provider')
                if path=='repos/owner/example':return {'private':True,'default_branch':'main'}
                if '/commits/' in path:return {'sha':'a'*40}
                if '/releases/tags/' in path:return {'id':1}
                if '/assets?' in path:
                    return [{'id':i+1,'name':v['asset_name'],'size':v['bytes'],'digest':'sha256:'+v['sha256']}
                            for i,v in enumerate(manifest['assets'].values())]
                raise AssertionError(path)
        return API()

    def test_worker_preparation_reuses_the_standard_assembler_and_pins_all_splits(self):
        directory=self.model_directory(self.root/'model')
        # All factory files are canonical source; the worker bundle never carries credentials.
        for p in (ROOT/'factory').glob('*.py'):
            shutil.copyfile(p,self.root/'factory'/p.name)
        read_hub=lambda *args:{'private':True,'commit':'b'*40,'main':'b'*40,'tag':'b'*40}
        result=workflow.worker_plan(self.root,directory,api=self.fake_api(),hub_reader=read_hub)
        declaration=json.loads((self.root/result['declaration']).read_text())
        folder=(self.root/result['declaration']).parent
        job=json.loads((folder/'job.json').read_text())
        self.assertEqual(3,len(job['fetch']['assets']))
        self.assertEqual({'public/train.csv','public/eval.csv','private/holdout.csv'},
                         {a['dest'] for a in job['fetch']['assets']})
        # Exercise actual assembly, including its all-file answer-artifact scan.
        assembly_spec=importlib.util.spec_from_file_location('audit_test_assembler',ROOT/'scripts/assemble-job.py')
        assembler=importlib.util.module_from_spec(assembly_spec);assembly_spec.loader.exec_module(assembler)
        target=self.root/'assembled';target.mkdir()
        with patch.object(assembler,'ROOT',self.root):
            _,_,size=assembler.assemble(declaration,job,target)
        self.assertLess(size,2*1024*1024)
        self.assertEqual(result,workflow.worker_plan(self.root,directory,api=self.fake_api(),hub_reader=read_hub))

    def test_live_hub_drift_refuses_before_creating_a_worker_declaration(self):
        directory=self.model_directory(self.root/'model')
        read_hub=lambda *args:{'private':False,'commit':'b'*40,'main':'b'*40,'tag':'b'*40}
        with self.assertRaisesRegex(ValueError,'privacy or commits changed'):
            workflow.worker_plan(self.root,directory,api=self.fake_api(),hub_reader=read_hub)
        self.assertFalse((self.root/'candidates').exists())

    def test_complete_receipt_chain_and_tamper_refusal_at_queue_boundary(self):
        directory=self.root/'candidates/example/autonomous-audit/unit';self.model_directory(directory/'model')
        worker.run(self.root,directory/'model/capsule.json',directory/'model/response.json',
                   self.package,directory/'worker')
        outputs=directory/'worker';names=('autonomous-audit.json','battery.json','model-attacks.json','model-freeze.json')
        entries=[{'file':'output/'+n,'name':f'file-{i}','id':i+1,'offset':0,
                  'sha256':audit.sha256(outputs/n),'size':(outputs/n).stat().st_size} for i,n in enumerate(names)]
        raw={'job':{'id':'audit-unit'},'assets':entries}
        (outputs/'staging-manifest.json').write_text(json.dumps(raw))
        raw_entry={'name':'manifest.json','id':99,'sha256':audit.sha256(outputs/'staging-manifest.json'),
                   'size':(outputs/'staging-manifest.json').stat().st_size}
        pins={**self.value['binding']['implementation'],
              'capsule.json':audit.sha256(directory/'model/capsule.json'),
              'response.json':audit.sha256(directory/'model/response.json')}
        record={'source_sha256':'f'*64,'status':'deleted',
                'job':{'candidate':'example','command':['python3','-B','/workspace/scripts/audit-release-worker.py'],
                       'source_files':[{'bundled_as':n,'sha256':v} for n,v in pins.items()]},
                'result':{'exit_code':0,'status':'succeeded','assets':entries+[raw_entry]}}
        collection={'job_id':'audit-unit','source_sha256':'f'*64,'ledger_sha256':'e'*64,
                    'raw_manifest_sha256':raw_entry['sha256'],
                    'files':[{'file':n,'sha256':entries[i]['sha256'],'asset_id':i+1} for i,n in enumerate(names)]}
        (outputs/'collection.json').write_text(json.dumps(collection))
        (outputs/'staging-readback.json').write_text(json.dumps({
            'destinations_sha256':self.value['binding']['destinations_sha256'],
            'github_commit':'a'*40,'huggingface_commit':'b'*40,'both_private':True}))
        with patch.object(workflow,'committed_record',return_value=(record,'e'*64,'a'*40)):
            verdict=workflow.check(self.root,'example',directory)
            (directory/'verdict.json').write_text(json.dumps(verdict))
            candidate={'id':'example','status':'packaged','awaiting_operator':True,
                       'autonomous_audit':{'directory':directory.relative_to(self.root).as_posix(),
                                           'sha256':audit.sha256(directory/'verdict.json')}}
            self.assertTrue(workflow.queue_ready(self.root,candidate))
            p=outputs/'battery.json';p.write_text(p.read_text()+'\n')
            self.assertFalse(workflow.queue_ready(self.root,candidate))


if __name__=='__main__':unittest.main()
