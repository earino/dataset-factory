import argparse
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from factory.hermes_write_task import run


class HermesWriteTaskTests(unittest.TestCase):
    def test_empty_selection_and_bounds_reach_native_single_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompt = Path(tmp) / 'prompt'; prompt.write_text('write the builder')
            args = argparse.Namespace(hermes_root=Path(tmp), query_file=prompt, model='requested',
                                      provider='nous', max_turns=6, run_budget=300)
            client = SimpleNamespace(enabled_toolsets=[], _explicit_toolsets=True,
                                     max_turns=6, run_budget_seconds=300)
            native = SimpleNamespace(HermesCLI=Mock(return_value=client),
                                     _run_single_query_mode=Mock(), _run_cleanup=Mock(),
                                     _install_single_query_signal_handlers=Mock())
            with patch.dict(sys.modules, {'cli': native}), patch.dict(os.environ), \
                    patch.object(sys, 'path', list(sys.path)), patch('atexit.register'):
                run(args)
                native.HermesCLI.assert_called_once_with(model='requested', provider='nous', toolsets=[],
                    max_turns=6, run_budget=300, ignore_rules=True)
                native._run_single_query_mode.assert_called_once_with(client, 'write the builder', None, True, True)
                self.assertEqual('oneshot', os.environ['HERMES_SESSION_SOURCE'])
                # A changed runtime must fail before inference, not silently
                # substitute profile tools or drop the native time bound.
                native._run_single_query_mode.reset_mock()
                for field, value in [('enabled_toolsets', ['web']), ('_explicit_toolsets', False),
                                     ('run_budget_seconds', None), ('max_turns', 120)]:
                    old = getattr(client, field); setattr(client, field, value)
                    with self.assertRaises(RuntimeError): run(args)
                    setattr(client, field, old)
                native._run_single_query_mode.assert_not_called()


if __name__ == '__main__': unittest.main()
