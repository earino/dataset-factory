#!/usr/bin/env python3
"""Offline CI previews, including explicit refusal evidence for rejected fixtures."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory.common import FactoryError
from factory.release_schema import load_release
from factory.site_pipeline import prepare

# Regression expectations for retained private artifacts, never publication exemptions.
# Both must still fail: an unexpected pass requires review/removal of this expectation.
EXPECTED_REFUSALS = {
    'cqc-care-home-deregistration': 'fixture_answers',
    'unhcr-refugee-data-finder': 'fixture_answers',
}


def preview_all(root, out):
    config = json.loads((root / 'config/sites.json').read_text())
    results = {}
    for editorial in sorted((root / 'sites').glob('*.json')):
        name = editorial.stem
        package = root / 'release' / name
        if not package.is_dir():
            continue
        expected = EXPECTED_REFUSALS.get(name)
        if expected and load_release(package).published:
            raise FactoryError(f'{name}: expected-refusal fixture must remain private')
        try:
            prepare(package, json.loads(editorial.read_text()), config, out / name)
        except FactoryError as exc:
            if not expected or expected not in str(exc):
                raise
            results[name] = {'status': 'refused', 'reason': str(exc)}
        else:
            if expected:
                raise FactoryError(f'{name}: unexpected pass of rejected artifact')
            results[name] = {'status': 'prepared'}
    out.mkdir(parents=True, exist_ok=True)
    (out / 'preview-results.json').write_text(json.dumps(results, indent=2) + '\n')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preview_all(ROOT, args.out.resolve()), indent=2))
