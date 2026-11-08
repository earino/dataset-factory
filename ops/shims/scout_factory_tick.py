#!/usr/bin/env python3
"""Script-only scheduler entrypoint; no wrapper model or routine chat messages."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/opt/data/dataset-factory')


def main():
    started = time.time()
    result = subprocess.run(['sh', str(ROOT / 'scripts/scout-factory'), 'run', '--once'],
                            cwd=ROOT, env={**os.environ, 'HERMES_HOME': '/opt/data'},
                            capture_output=True, text=True, timeout=1200)
    try:
        outcome = json.loads(result.stdout)
    except ValueError:
        outcome = {'status': 'error', 'exit_code': result.returncode,
                   'reason': result.stderr[-2000:]}
    folder = ROOT / '.factory'
    folder.mkdir(exist_ok=True)
    pending = folder / 'last-tick.json.part'
    pending.write_text(json.dumps({'started': started, 'finished': time.time(),
                                  'exit_code': result.returncode, 'outcome': outcome}, indent=2) + '\n')
    pending.replace(folder / 'last-tick.json')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
