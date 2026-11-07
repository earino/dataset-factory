"""Validate historical approval citations without converting history into authority."""
import json
from pathlib import Path

from .asset_integrity import safe_path, sha256
from .publication import require


def check(root):
    root = Path(root)
    registry = json.loads((root/'config/frozen-releases.json').read_text())['releases']
    for frozen in registry:
        dataset = frozen['dataset']
        path = safe_path(root, f'candidates/{dataset}/approval-history/{frozen["release_tag"]}.json')
        value = json.loads(path.read_text())
        require(value['schema_version'] == 1 and value['kind'] == 'historical_publication_record'
                and value['authorizes_new_publication'] is False and value['approved_at'] is None
                and value['waived_rules'] == [], 'history cannot grant publication authority')
        for key in ('dataset', 'release_tag', 'artifact_version', 'manifest_sha256'):
            require(value[key] == frozen[key], 'historical identity differs from frozen release')
        require(sha256(root/f'release/{dataset}/MANIFEST.json') == frozen['manifest_sha256'],
                'historical manifest changed')
        snapshot = value['source_snapshot']; source = safe_path(root, snapshot['path'])
        require(source.stat().st_size < 256*1024 and sha256(source) == snapshot['sha256'], 'historical source snapshot changed')
        require(snapshot['record_key'] == dataset and dataset in json.loads(source.read_text())['records'],
                'historical source identifies another dataset')
        quotes = []
        for citation in value['citations']:
            source = safe_path(root, citation['path'])
            require(source.stat().st_size <= 2*1024*1024 and sha256(source) == citation['sha256'], 'archived history changed')
            lines = source.read_text().splitlines(); quote = citation['quote']
            require(quote and '\n'.join(lines[citation['start_line']-1:]).startswith(quote), 'historical quotation differs')
            quotes.append(quote)
        words = value['recorded_operator_words']; status = value['evidence_status']
        if status in ('recorded_quote', 'ratified_after_the_act_reported'):
            require(isinstance(words, str) and words and any(words in q for q in quotes), 'operator words are not in cited history')
        else:
            require(status in ('reported_only', 'relayed_audit_only', 'gap') and words is None,
                    'unrecorded operator words must remain null')
    return {'ok': True, 'historical_releases': len(registry), 'authorizes_new_publication': False}
