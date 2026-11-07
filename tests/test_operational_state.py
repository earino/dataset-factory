import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from factory.operational_state import append, archive, events, render, verify_archive

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('state_cli', ROOT / 'scripts/operational-state.py')
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)


class OperationalStateTests(unittest.TestCase):
    def base(self, root):
        (root / 'evidence.json').write_text('{"observed":true}\n')
        (root / 'STATE.md').write_bytes(b'Unheaded old prose\r\n\n## 2026-11-02\nNewest\n\n## 2026-10-19\nOlder\n\n## 2026-11-01\nOut of order\n')
        (root / 'config').mkdir(); (root / 'config/admission.json').write_text(json.dumps({'hold': True, 'reason': 'Remediation'}))
        return {'id': 'unit-observation', 'actor': 'Codex', 'time': '2026-11-07T19:57:20Z',
                'candidate': None, 'job': None, 'kind': 'test', 'outcome': 'Measured unit observation',
                'commit': 'a' * 40, 'evidence': [{'path': 'evidence.json',
                  'sha256': hashlib.sha256((root / 'evidence.json').read_bytes()).hexdigest()}]}

    def test_archive_reconstructs_exact_mixed_newline_and_out_of_order_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.base(root); original = (root / 'STATE.md').read_bytes()
            result = archive(root)
            self.assertEqual(result['sha256'], hashlib.sha256(original).hexdigest())
            self.assertEqual(result, verify_archive(root))
            self.assertEqual({'undated.md', '2026-10.md', '2026-11.md'}, set(result['files']))
            self.assertEqual(original, (root / 'STATE.md').read_bytes())
            with self.assertRaises(FileExistsError): archive(root)
            p = root / 'docs/state-archive/2026-10.md'; p.write_bytes(p.read_bytes() + b'edited')
            with self.assertRaisesRegex(ValueError, 'changed'): verify_archive(root)

    def test_events_idempotent_bounded_ordered_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); event = self.base(root)
            self.assertTrue(append(root, event)); self.assertFalse(append(root, event))
            with self.assertRaisesRegex(ValueError, 'different observation'): append(root, dict(event, outcome='Changed'))
            with self.assertRaisesRegex(ValueError, 'backdated'): append(root, dict(event, id='older', time='2026-11-01T00:00:00Z'))
            (root / 'evidence.json').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'changed'): append(root, dict(event, id='next'))
            # An old observation remains historically verifiable after its referenced file advances.
            self.assertEqual([event], events(root)[0])
            path = root / 'events/2026-11.jsonl'; path.write_bytes(path.read_bytes().replace(b'Measured', b'Invented'))
            with self.assertRaisesRegex(ValueError, 'chain'): events(root)

    def test_state_is_deterministic_small_and_responds_to_authoritative_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); event = self.base(root); archive(root); append(root, event)
            for i in range(40):
                p = root / f'candidates/candidate-{i}/record.json'; p.parent.mkdir(parents=True)
                p.write_text(json.dumps({'status': 'packaged', 'awaiting_operator': i < 15, 'next_action': 'x' * 2000}))
            (root / 'jobs').mkdir()
            for i in range(30):
                (root / f'jobs/job-{i}.json').write_text(json.dumps({'status': 'running', 'expires': '2026-11-08T00:00:00Z'}))
            first = render(root); self.assertEqual(first, render(root)); self.assertLess(len(first), 20000)
            self.assertIn(b'Ledger entries not marked deleted: 30', first)
            self.assertIn(b'15 records request operator action', first)
            (root / 'jobs/job-0.json').write_text('{"status":"deleted"}')
            self.assertNotEqual(first, render(root))
            self.assertIn(b'Ledger entries not marked deleted: 29', render(root))

    def test_missing_evidence_symlinks_and_partial_log_lines_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); event = self.base(root)
            event['evidence'][0]['path'] = '../evidence.json'
            with self.assertRaises(ValueError): append(root, event)
            event['evidence'][0]['path'] = 'link.json'; (root / 'link.json').symlink_to(root / 'evidence.json')
            with self.assertRaisesRegex(ValueError, 'symlink'): append(root, event)
            event['evidence'][0]['path'] = 'evidence.json'; append(root, event)
            p = root / 'events/2026-11.jsonl'; p.write_bytes(p.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, 'incomplete'): events(root)

    def test_ci_detects_rechained_event_rewrites_and_archive_removal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); event = self.base(root); archive(root); append(root, event)
            def git(*args): return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
            git('init'); git('add', 'events', 'docs/state-archive')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'Original evidence')
            base = git('rev-parse', 'HEAD'); cli.immutable_history(root, base)
            p = root / 'events/2026-11.jsonl'; original = p.read_bytes(); p.write_bytes(original + b'\n')
            cli.immutable_history(root, base)  # Prefix intact, full chain validator separately rejects bad appended rows.
            p.write_bytes(b'changed\n')
            with self.assertRaisesRegex(ValueError, 'rewritten'): cli.immutable_history(root, base)
            p.write_bytes(original); (root / 'docs/state-archive/2026-10.md').unlink()
            with self.assertRaisesRegex(ValueError, 'removed'): cli.immutable_history(root, base)


if __name__ == '__main__': unittest.main()
