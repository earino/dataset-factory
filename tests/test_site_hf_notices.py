"""Current Hub editorial updates leave immutable revisions untouched."""
import hashlib
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class HubNoticeTest(unittest.TestCase):
    def test_bulk_is_never_downloaded_and_editorial_identity_is_explicit(self):
        execute = runpy.run_path(str(ROOT/'scripts/site-hf.py'))['execute']
        read_paths=[]
        files={'README.md':b'NOTICE', 'MANIFEST.json':b'{}', 'data/test.csv':b'id,target\na,1\n'}
        changed_current_blob = False
        def info(repo,revision,**kwargs):
            return NS(private=False,sha='frozen' if revision=='v1' else 'current',siblings=[
                NS(rfilename=k,size=len(v),blob_id=('changed' if changed_current_blob and revision=='main'
                   and k.endswith('.csv') else hashlib.sha1(v).hexdigest()),lfs=None)
                for k,v in files.items()])
        with tempfile.TemporaryDirectory() as tmp:
            def download(repo,filename,revision,**kwargs):
                self.assertFalse(filename.endswith('.csv'),'bulk must never reach the coordinator')
                read_paths.append(filename);path=Path(tmp)/filename;path.write_bytes(files[filename]);return str(path)
            sdk=NS(HfApi=lambda **kwargs:NS(dataset_info=info),hf_hub_download=download,
                   CommitOperationAdd=lambda **kwargs:NS(**kwargs))
            payload={'action':'read','public':True,'record':{'dataset':'example','hf_repository':'owner/data',
                'release_tag':'v1','artifact_version':'exact','assets':{'test.csv':{
                    'hf_path':'data/test.csv','bytes':len(files['data/test.csv']),
                    'sha256':hashlib.sha256(files['data/test.csv']).hexdigest()}}}}
            with patch.dict('sys.modules',{'huggingface_hub':sdk}), patch.dict(execute.__globals__,{
                'secret':lambda name:'test-only','from_manifest':lambda x,**kw:NS(tag='v1',artifact_id='exact'),
                'check_manifest':lambda *args:None,'linked_readme':lambda t,r:t,
                'worker_evidence':lambda *args:None,'prior_editorial_identity':lambda *args:False}):
                with self.assertRaisesRegex(Exception,'requires collected worker'):
                    execute(payload)
                with patch.dict(execute.__globals__,{'prior_editorial_identity':lambda *args:True}):
                    result=execute(payload)
                    self.assertEqual(result['verification_basis'],'prior_verified_immutable_release')
                    self.assertEqual(result['inherited_non_lfs_assets'],['test.csv'])
                    self.assertEqual(result['bulk_downloads'],0)
                    changed_current_blob = True
                    with self.assertRaisesRegex(Exception,'current data blob differs'):
                        execute(payload)

    def test_continuity_baseline_binds_commit_and_artifact(self):
        fn=runpy.run_path(str(ROOT/'scripts/site-hf.py'))['prior_editorial_identity']
        prior=json.loads((ROOT/'config/editorial-release-baselines.json').read_text())['releases'][0]
        record={**prior,'hf_repository':prior['repository']}
        self.assertTrue(fn(record,prior['hf_commit']))
        self.assertFalse(fn(record,'different-commit'))
        self.assertFalse(fn({**record,'artifact_version':'different-artifact'},prior['hf_commit']))

    def test_all_current_docs_updated_atomically_and_idempotently(self):
        module = runpy.run_path(str(ROOT/'scripts/site-hf.py'))
        execute = module['execute']
        docs = {'README.md': b'---\nlicense: cc0-1.0\n---\nOld card',
                'LOADING.md': b'Old loading', 'DATA_DICTIONARY.md': b'Old dictionary'}
        manifest = {'release_tag':'v1','artifact_version':'exact','package_files':
                    {k:hashlib.sha256(v).hexdigest() for k,v in docs.items() if k!='README.md'}}
        docs['MANIFEST.json'] = json.dumps(manifest).encode()
        frozen = dict(docs)
        commits = []
        def info(repo, revision, **kwargs):
            files = frozen if revision == 'v1' else docs
            return NS(private=False,sha=revision,siblings=[NS(rfilename=k,size=len(v)) for k,v in files.items()])
        def commit(**kwargs):
            self.assertEqual(kwargs['revision'], 'main')
            commits.append(kwargs)
            docs.update({o.path_in_repo:o.path_or_fileobj for o in kwargs['operations']})
            return NS(oid='new-main')
        with tempfile.TemporaryDirectory() as tmp:
            def download(repo, filename, revision, **kwargs):
                dest=Path(tmp)/filename
                dest.write_bytes((frozen if revision=='v1' else docs)[filename])
                return str(dest)
            sdk=NS(HfApi=lambda **kwargs:NS(dataset_info=info,create_commit=commit),
                   hf_hub_download=download,CommitOperationAdd=lambda **kwargs:NS(**kwargs))
            def linked(text,record):
                return text if text.startswith('NOTICE\n') else 'NOTICE\n'+text
            with patch.dict('sys.modules', {'huggingface_hub':sdk}), patch.dict(execute.__globals__, {
                'secret':lambda name:'test-only', 'from_manifest':lambda x,**kw:NS(tag='v1',artifact_id='exact'),
                'check_manifest':lambda *args:None, 'linked_readme':linked}):
                payload={'action':'link','public':True,'record':{'hf_repository':'owner/data',
                         'release_tag':'v1','artifact_version':'exact','assets':{},'suitability':{'review':True}}}
                self.assertTrue(execute(payload)['links_present'])
                self.assertEqual(len(commits),1)
                self.assertEqual(set(o.path_in_repo for o in commits[0]['operations']),set(docs))
                self.assertTrue(docs['LOADING.md'].startswith(b'NOTICE'))
                self.assertEqual(frozen['LOADING.md'],b'Old loading')
                self.assertTrue(execute({**payload,'action':'read'})['links_present'])
                execute(payload)
                self.assertEqual(len(commits),1)
