"""Transport/binding unit tests, not historical dataset acceptance measurements."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


archive=script('prepare-frozen-audit')
audit=script('historical-recovery-audit')


class FrozenAuditTests(unittest.TestCase):
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
