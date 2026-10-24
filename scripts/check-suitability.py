#!/usr/bin/env python3
"""Check every release has a version-bound, evidence-backed suitability review."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory.suitability import validate


def main():
    root = Path(__file__).resolve().parents[1]
    errors = []
    manifests = sorted((root / 'release').glob('*/MANIFEST.json'))
    for path in manifests:
        review = root / 'suitability' / (path.parent.name + '.json')
        if not review.is_file():
            errors.append(f'{path.parent.name}: missing suitability review')
            continue
        try:
            errors += [f'{path.parent.name}: {error}' for error in
                       validate(json.loads(review.read_text()), json.loads(path.read_text()), root)]
        except (ValueError, TypeError) as exc:
            errors.append(f'{path.parent.name}: {exc}')
    print('\n'.join(errors) if errors else f'OK: {len(manifests)} version-bound suitability reviews')
    return int(bool(errors))

if __name__ == '__main__':
    raise SystemExit(main())
