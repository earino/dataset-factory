"""Frozen defect shapes and false-positive boundary; never download dataset rows."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from factory.artifact_scrub import scan_text, scan_tree
from tests.test_artifact_checks import package_check, ROOT


class ScrubTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_fixture_answers_and_salt_are_not_hidden_by_filename(self):
        (self.root / 'notes.txt').write_text('SALT = "example-pseudonym-salt"\n'
            'FIXTURES = {"event-123456": {"label": 1}}\n')
        result = scan_tree(self.root)
        self.assertFalse(result['ok'])
        self.assertTrue({'embedded_salt', 'fixture_answers'} <= {f['rule'] for f in result['findings']})
        self.assertNotIn('example-pseudonym-salt', json.dumps(result))

    def test_counts_exclusions_and_training_examples_are_allowed(self):
        text = 'FIXTURE_COUNTS = {"excluded": 3, "rows": 100}\nassert counts["excluded"] == 3\n'
        self.assertEqual([], scan_text(text, 'build.py'))
        self.assertEqual([], scan_text('Training example event-123456: label 1 on 2020-01-01.',
            'README.md', scored_ids={'event-987654'}, windows=[('2024-01-01', '2025-01-01')]))

    def test_scored_example_across_wrapped_lines_is_refused(self):
        text = 'Example event-987654, 2024-06-01:\nmeasured future value > threshold\nlabel 1.\n'
        rules = {f['rule'] for f in scan_text(text, 'README.md', scored_ids={'event-987654'},
                                           windows=[('2024-01-01', '2025-01-01')])}
        self.assertIn('scored_row_answer', rules)
        self.assertIn('scored_window_example', rules)

    def test_split_target_columns_are_intentional_and_not_scanned_as_scaffolding(self):
        quality = {'target':'label', 'id_columns':['id'],
                   'splits': {'eval':'eval.csv'},
                   'split_windows': {'eval': {'start':'2024-01-01', 'end':'2025-01-01'}}}
        (self.root/'quality.json').write_text(json.dumps(quality))
        (self.root/'eval.csv').write_text('id,label\nevent-987654,1\n')
        result = scan_tree(self.root, dataset=self.root)
        self.assertTrue(result['ok'], result['findings'])
        self.assertEqual(1, result['scope']['identifier_count'])
        (self.root/'README.md').write_text('event-987654 has label 1')
        self.assertFalse(scan_tree(self.root, dataset=self.root)['ok'])

    def test_unknown_files_are_scanned_and_containers_do_not_silently_pass(self):
        (self.root/'extra.bin').write_bytes(b'@@UNRESOLVED@@')
        (self.root/'hidden.zip').write_bytes(b'PK\x03\x04fake archive')
        result = scan_tree(self.root)
        self.assertEqual({'extra.bin','hidden.zip'}, set(result['files']))
        self.assertEqual({'unresolved_placeholder','uninspected_container'},
                         {f['rule'] for f in result['findings']})

    def test_binary_and_malformed_json_refuse_but_markdown_links_are_text(self):
        self.assertEqual([], scan_text('[Documentation](https://example.test)', 'README.md'))
        self.assertEqual('unreadable_json', scan_text('[broken', 'quality.json')[0]['rule'])
        (self.root/'opaque.dat').write_bytes(b'\xff\x00hidden')
        self.assertEqual('uninspected_binary', scan_tree(self.root)['findings'][0]['rule'])

    def test_json_lines_fixture_tables_are_scanned_structurally(self):
        text='{"counts": 4}\n{"fixtures": {"event-123456": {"label": 1}}}\n'
        self.assertIn('fixture_answers',{r['rule'] for r in scan_text(text,'notes.jsonl')})

    def test_symlink_is_refused_without_following_it(self):
        (self.root/'escape').symlink_to('/not-a-package-file')
        self.assertEqual('unsafe_path', scan_tree(self.root)['findings'][0]['rule'])

    def test_scrubber_never_executes_source(self):
        (self.root/'build.py').write_text('raise RuntimeError("must never execute")\n')
        self.assertTrue(scan_tree(self.root)['ok'])

    def test_scan_is_deterministic_and_bound_to_every_file(self):
        (self.root/'README.md').write_text('clean')
        before = scan_tree(self.root)
        self.assertEqual(before, scan_tree(self.root))
        (self.root/'README.md').write_text('changed')
        self.assertNotEqual(before['tree_digest'], scan_tree(self.root)['tree_digest'])

    def test_real_staged_scaffolds_are_refused_without_modifying_them(self):
        expected = {
            'ab-wildfire-ia-escape': {'fixture_answers', 'unresolved_placeholder'},
            'cqc-care-home-deregistration': {'fixture_answers', 'embedded_salt'},
            'za-cct-substation-evening-peak-exceedance': {'scored_window_example'},
        }
        for name, rules in expected.items():
            root = ROOT/'release'/name
            before = scan_tree(root, dataset=root)
            with self.subTest(name=name):
                self.assertTrue(rules <= {f['rule'] for f in before['findings']})
                problems, _ = package_check.check_package(root)
                self.assertTrue(any(any(rule in p for rule in rules) for p in problems))
                self.assertEqual(before, scan_tree(root, dataset=root))

    def test_frozen_manifest_does_not_exempt_added_or_changed_answers(self):
        package = self.root/'package'
        shutil.copytree(ROOT/'release/austin-911-response', package)
        (package/'new_answers.py').write_text('FIXTURES = {"event-123456": {"label": 1}}')
        problems, _ = package_check.check_package(package)
        self.assertTrue(any('new_answers.py' in p and 'fixture_answers' in p for p in problems))

    def test_self_asserted_publication_cannot_waive_scrubber(self):
        package = self.root/'package'
        shutil.copytree(ROOT/'release/cqc-care-home-deregistration', package)
        path = package/'MANIFEST.json'
        manifest = json.loads(path.read_text()); manifest['published'] = True
        path.write_text(json.dumps(manifest))
        problems, _ = package_check.check_package(package)
        self.assertTrue(any('embedded_salt' in p for p in problems))
