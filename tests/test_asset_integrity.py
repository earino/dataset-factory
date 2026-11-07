from pathlib import Path
import tempfile
import unittest

from factory.asset_integrity import check, sha256


class AssetIntegrityTests(unittest.TestCase):
    def make(self, root):
        (root/'public').mkdir()
        (root/'public/eval.csv').write_text('id,target\na,0\nb,1\n')
        entry = {'sha256': sha256(root/'public/eval.csv'), 'bytes': (root/'public/eval.csv').stat().st_size}
        asset = dict(entry, asset_name='eval.csv')
        manifest = {'release_tag': 'v1', 'assets': {'public/eval.csv': asset},
                    'files': {'public/eval.csv': dict(entry)}, 'package_files': {}}
        (root/'SHA256SUMS').write_text(entry['sha256']+'  public/eval.csv\n')
        (root/'get_dataset.py').write_text('TAG="v1"\nLAYOUT={"eval.csv":"public/eval.csv"}\nEXPECTED='+
                                         repr({'eval.csv': entry})+'\nraise RuntimeError("never execute")\n')
        return manifest

    def test_present_asset_checked_even_when_package_inventory_omits_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); manifest=self.make(root)
            self.assertEqual([],check(root,manifest)[0])
            (root/'public/eval.csv').write_text('id,target\na,1\nb,0\n')
            for external in (False,True):
                problems,_=check(root,manifest,external_assets=external)
                self.assertTrue(any('actual release asset bytes' in p for p in problems),problems)

    def test_external_mode_is_explicit_and_reports_only_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); manifest=self.make(root)
            (root/'public/eval.csv').unlink()
            self.assertTrue(any('absent' in p for p in check(root,manifest)[0]))
            problems,notes=check(root,manifest,external_assets=True)
            self.assertEqual([],problems)
            self.assertTrue(any('NOT verified' in note for note in notes))
            manifest['files']['public/eval.csv']['bytes']+=1
            self.assertTrue(check(root,manifest,external_assets=True)[0])

    def test_stale_loader_fails_even_when_all_other_digests_are_correct(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=self.make(root)
            path=root/'get_dataset.py'
            text=path.read_text().replace(manifest['assets']['public/eval.csv']['sha256'],'0'*64)
            path.write_text(text)
            self.assertTrue(any('EXPECTED' in p for p in check(root,manifest)[0]))

    def test_checksum_omission_duplication_and_alias_duplication_refuse(self):
        for mode in ('missing','duplicate','alias','bad'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);manifest=self.make(root);p=root/'SHA256SUMS';text=p.read_text()
                p.write_text({'missing':'','duplicate':text+text,
                              'alias':text+text.replace('public/eval.csv','eval.csv'),
                              'bad':'xyz  public/eval.csv\n'}[mode])
                self.assertTrue(check(root,manifest)[0])

    def test_symlink_and_parent_traversal_refuse_before_hashing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=self.make(root)
            (root/'public/eval.csv').unlink();(root/'public/eval.csv').symlink_to(root/'get_dataset.py')
            self.assertTrue(any('symlink' in p for p in check(root,manifest)[0]))
            manifest['assets']['../outside.csv']=manifest['assets'].pop('public/eval.csv')
            self.assertTrue(any('unsafe' in p for p in check(root,manifest)[0]))


if __name__ == '__main__':
    unittest.main()
