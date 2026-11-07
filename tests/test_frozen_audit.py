"""Transport/binding unit tests, not historical dataset acceptance measurements."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import io

ROOT=Path(__file__).resolve().parents[1]


def script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


archive=script('prepare-frozen-audit')
audit=script('historical-recovery-audit')


class FrozenAuditTests(unittest.TestCase):
    def test_every_published_level_has_exact_frozen_inputs_in_one_batch(self):
        registry=json.loads((ROOT/'config/frozen-releases.json').read_text())
        expected=set();seen=[]
        for record in registry['releases']:
            m=json.loads((ROOT/'release'/record['dataset']/'MANIFEST.json').read_text())
            expected.update((record['dataset'],level or None) for level in (m.get('levels') or {'':m}))
        for plan in ROOT.glob('candidates/*/resilience-a2/*/cases.json'):
            job=json.loads(plan.with_name('job.json').read_text())
            fetch={a['dest']:a for a in job['fetch']['assets']}
            for case in json.loads(plan.read_text())['cases']:
                binding=case['published_binding'];key=(binding['dataset'],binding['level']);seen.append(key)
                m=json.loads((ROOT/'release'/key[0]/'MANIFEST.json').read_text())
                self.assertEqual('published_comparison',case['mode'])
                components={}
                entries=list(case['files'])
                for archive in case['archives']:
                    actual=fetch[archive['fetch_dest']]
                    self.assertEqual((archive['size'],archive['sha256']),(actual['size'],actual['sha256']))
                    entries+=archive['members']
                for entry in entries:
                    name=entry['path']
                    if name not in ('public/train.csv','public/eval.csv','private/holdout.csv','meta.json','quality.json'):
                        continue
                    self.assertNotIn(name,components)
                    relative=(key[1]+'/' if key[1] else '')+name
                    self.assertEqual((entry['size'],entry['sha256']),
                                     (m['assets'][relative]['bytes'],m['assets'][relative]['sha256']))
                    components[name]=entry['sha256']
                    if 'fetch_dest' in entry:
                        actual=fetch[entry['fetch_dest']]
                        self.assertEqual((entry['size'],entry['sha256']),(actual['size'],actual['sha256']))
                    if 'url' in entry:
                        self.assertEqual('my-pricecatcher-weekly-increase',key[0])
                        self.assertIn('--public-fetch',job['command'])
                self.assertEqual(5,len(components))
                names={'public/train.csv':'train','public/eval.csv':'eval','private/holdout.csv':'holdout'}
                identity=hashlib.sha256(''.join(sorted(names.get(k,k)+':'+v for k,v in components.items())).encode()).hexdigest()
                self.assertEqual(case['artifact_version'],identity)
        self.assertEqual(expected,set(seen));self.assertEqual(len(seen),len(expected))

    def test_public_fallback_is_explicit_bounded_and_hash_verified(self):
        payload=b'unit transport fixture only'
        url='https://github.com/example/example/releases/download/v1/example.txt'
        entry={'path':'example.txt','url':url,'size':len(payload),
               'sha256':hashlib.sha256(payload).hexdigest()}
        class Response(io.BytesIO):
            status=200
            def geturl(self):return url
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaisesRegex(ValueError,'explicit worker-only'):
                audit.prepare({'files':[entry]},root,root/'artifact')
            audit.public_download(entry,root/'ok',opener=lambda *a,**k:Response(payload))
            self.assertEqual(payload,(root/'ok').read_bytes())
            with self.assertRaisesRegex(ValueError,'exceeds pinned size'):
                audit.public_download(entry,root/'large',opener=lambda *a,**k:Response(payload+b'x'))
            with self.assertRaisesRegex(ValueError,'digest/size mismatch'):
                audit.public_download(entry,root/'changed',opener=lambda *a,**k:Response(b'x'*len(payload)))
            with self.assertRaisesRegex(ValueError,'HTTPS GitHub'):
                audit.public_download(dict(entry,url='https://unrelated.example/data'),root/'other')

    def source(self,root):
        package=root/'release/example';package.mkdir(parents=True)
        manifest={'dataset':'example','artifact_version':'a'*64,'release_tag':'v2026.10',
                  'levels':{'one':{'artifact_version':'b'*64}}}
        (package/'MANIFEST.json').write_text(json.dumps(manifest))
        (package/'README.md').write_text('Original frozen text.\n')
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in package.iterdir()}
        registry={'releases':[{'dataset':'example','artifact_version':'a'*64,
                    'release_tag':'v2026.10','manifest_sha256':files['MANIFEST.json'],
                    'editorial_files':files}]}
        (root/'config').mkdir();(root/'config/frozen-releases.json').write_text(json.dumps(registry))
        return package,registry

    def test_archive_is_deterministic_and_cannot_overwrite_or_change_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);package,registry=self.source(root)
            first=archive.prepare(root,root/'one');second=archive.prepare(root,root/'two')
            self.assertEqual(first,second)
            with tarfile.open(root/'one/example.tar') as tar:
                self.assertEqual(['package/MANIFEST.json','package/README.md'],tar.getnames())
            with self.assertRaises(FileExistsError):archive.prepare(root,root/'one')
            (package/'README.md').write_text('changed')
            with self.assertRaisesRegex(ValueError,'frozen file changed'):archive.prepare(root,root/'three')

    def test_bulk_and_escaped_registry_paths_are_refused(self):
        for name in ('public/train.csv','../outside.txt'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);package,registry=self.source(root)
                registry['releases'][0]['editorial_files']={name:'c'*64}
                (root/'config/frozen-releases.json').write_text(json.dumps(registry))
                with self.assertRaises(ValueError):archive.prepare(root,root/'out')

    def test_comparison_requires_exact_frozen_manifest_level_and_editorial_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);package,registry=self.source(root)
            entry=archive.prepare(root,root/'data')['datasets'][0]
            case={'files':[],'archives':[{'fetch_dest':entry['archive'],'size':entry['size'],
                  'sha256':entry['sha256'],'members':entry['members']}],
                  'artifact_version':'b'*64,'published_binding':{'dataset':'example','level':'one',
                    'manifest_sha256':entry['manifest_sha256']}}
            artifact=root/'artifact';audit.prepare(case,root/'data',artifact)
            self.assertIn('never new-release',audit.published_binding(case,artifact,registry)['disposition'])
            case['artifact_version']='c'*64
            with self.assertRaisesRegex(ValueError,'artifact/level'):audit.published_binding(case,artifact,registry)
            case['artifact_version']='b'*64
            (artifact/'package/README.md').write_text('changed')
            with self.assertRaisesRegex(ValueError,'editorial bytes'):audit.published_binding(case,artifact,registry)


if __name__=='__main__':unittest.main()
