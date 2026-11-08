"""Run the installed Hermes quiet CLI with an explicit empty tool selection.

The installed argv parser maps an empty -t value to profile defaults. Its Python
constructor preserves [], including the ordinary gateway policy and time limit.
This adapter changes that argument boundary, not the agent runtime.
"""
import argparse
import atexit
import os
from pathlib import Path
import sys


def run(args):
    os.environ['HERMES_IGNORE_RULES'] = '1'
    os.environ['HERMES_SESSION_SOURCE'] = 'oneshot'
    os.environ['HERMES_SESSION_SOURCE_EXPLICIT'] = '1'
    # Direct script execution adds factory/ to the import path. Its http.py
    # must not shadow the stdlib package used by Hermes and its HTTP clients.
    script_directory = Path(__file__).resolve().parent
    sys.path[:] = [entry for entry in sys.path if Path(entry).resolve() != script_directory]
    sys.path.insert(0, str(args.hermes_root))
    from cli import HermesCLI, _install_single_query_signal_handlers, _run_single_query_mode, _run_cleanup
    client = HermesCLI(model=args.model, provider=args.provider, toolsets=[],
                       max_turns=args.max_turns, run_budget=args.run_budget, ignore_rules=True)
    if (client.enabled_toolsets != [] or client._explicit_toolsets is not True
            or client.run_budget_seconds != args.run_budget or client.max_turns != args.max_turns):
        raise RuntimeError('Installed Hermes did not preserve the bounded write-only policy')
    atexit.register(_run_cleanup)
    _install_single_query_signal_handlers(client)
    _run_single_query_mode(client, args.query_file.read_text(), None, True, True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-root', type=Path, required=True)
    parser.add_argument('--query-file', type=Path, required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--provider')
    parser.add_argument('--max-turns', type=int, required=True)
    parser.add_argument('--run-budget', type=int, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
