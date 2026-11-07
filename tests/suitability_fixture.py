"""Explicit unit-test editorial review; never real artifact acceptance evidence."""
import json
from pathlib import Path


def prepare(root, manifest):
    template = Path(__file__).resolve().parents[1]/'suitability/austin-911-response.json'
    record = json.loads(template.read_text())
    record.update({key: manifest[key] for key in ('dataset', 'release_tag', 'artifact_version')})
    record['evidence'] = [{'claim':'unit fixture only', 'source':'https://example.org/unit-test',
                           'detail':'Not real data or an acceptance result'}]
    path = Path(root)/'suitability'/(manifest['dataset']+'.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))
    return record
