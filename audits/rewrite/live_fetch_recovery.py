"""Controlled transport fault, then a real HTTPS source fetch and cached replay.

This is an explicit fault-injection demonstration, not an organic outage and not
dataset qualification. Run on the deployed coordinator; only a bounded public
metadata response is retrieved, never bulk data. Output is a compact receipt.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workers'))
import source_io

URL = ('https://geospatial.sec.usace.army.mil/dls/rest/services/NID/'
       'National_Inventory_of_Dams_Public_Service/FeatureServer/0/query'
       '?where=1%3D1&returnCountOnly=true&f=json')


def main():
    original = source_io.urllib.request.urlopen
    calls = []
    def request(req, **kwargs):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 503, 'Controlled recovery demonstration', {}, None)
        return original(req, **kwargs)
    with tempfile.TemporaryDirectory(prefix='factory-fetch-recovery-') as tmp:
        with patch.object(source_io.urllib.request, 'urlopen', request), patch.object(source_io, 'MAX_BYTES', 65536):
            first = source_io.fetch(URL, tmp, 'metadata.json')
            digest = source_io.sha(first)
            replay = source_io.fetch(URL, tmp, 'metadata.json')
            record = json.loads((Path(tmp) / 'sources.json').read_text())['metadata.json']
            if (len(calls) != 2 or record['transport_attempts'] != 2 or
                    digest != source_io.sha(replay) or not isinstance(json.loads(first.read_text()).get('count'), int)):
                raise RuntimeError('Recovery/cache/source-response assertion failed')
            print(json.dumps({'ok': True, 'observed_at_unix': time.time(), 'source_url': URL,
                              'helper_sha256': hashlib.sha256(Path(source_io.__file__).read_bytes()).hexdigest(),
                              'fault': 'Explicitly injected one HTTP 503 before the real HTTPS request',
                              'transport_calls': len(calls), 'cached_replay_network_calls': 0,
                              'response_bytes': record['bytes'], 'response_sha256': digest,
                              'scope': 'Helper transport recovery; not a qualified dataset or organic outage'}, indent=2))


if __name__ == '__main__':
    main()
