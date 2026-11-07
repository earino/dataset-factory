#!/usr/bin/env python3
"""Check every release has a version-bound, evidence-backed suitability review."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory.suitability import validate, publication_check


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publication', help='Strict new-publication admission for this dataset; no historical exception')
    args = parser.parse_args()
    if args.publication:
        import re
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.publication):
            parser.error('invalid dataset identifier')
        try:
            manifest = json.loads((root/'release'/args.publication/'MANIFEST.json').read_text())
            errors, _ = publication_check(root, manifest)
        except (OSError, ValueError, TypeError) as exc:
            errors = [str(exc)]
        print('\n'.join(errors) if errors else 'OK: current suitability allows new-publication admission; other gates still required')
        return int(bool(errors))
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
