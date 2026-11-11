#!/usr/bin/env python3
"""Resume automatic modern websites once; never changes dataset candidate state."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory.site_sync import run
from factory.http import secret

if __name__ == '__main__':
    try:
        hosted = Path('/opt/data/.secrets/github-publish.token')
        if not os.environ.get('FACTORY_PUBLISH_TOKEN_FILE') and hosted.is_file():
            os.environ['FACTORY_PUBLISH_TOKEN_FILE'] = str(hosted)
        if os.environ.get('FACTORY_PUBLISH_TOKEN_FILE') or os.environ.get('FACTORY_PUBLISH_TOKEN'):
            os.environ['GH_TOKEN'] = secret('FACTORY_PUBLISH_TOKEN')
            os.environ.pop('GITHUB_TOKEN', None)
        result = run()
    except Exception as exc:
        result = {'status': 'failed', 'error': type(exc).__name__}
    print(json.dumps(result))
    raise SystemExit(1 if result['status'] == 'failed' else 0)
