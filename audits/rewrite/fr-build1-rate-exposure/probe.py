"""Read-only bounded leakage audit; never an artifact qualification or model score."""
import csv
from datetime import date, timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import sys
from collections import defaultdict


def probe(path):
    root = Path(__file__).parent
    manifest = json.loads((root / 'staging-manifest.json').read_text())
    asset = next(a for a in manifest['assets'] if a['file'] == 'output/extract/private/holdout.csv')
    if Path(path).stat().st_size > 256 * 1024:
        raise ValueError('This audit only reads its bounded retained split sample')
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != asset['sha256']:
        raise ValueError('Input is not the retained failed-artifact split')
    target = json.loads((root / 'quality.json').read_text())['target']
    groups = defaultdict(list)
    for row in csv.DictReader(io.StringIO(raw.decode())):
        try:
            row['_date'] = date.fromisoformat(row['publication_date'])
            row['_rate'] = float(row['agency_prior_finalization_rate'])
        except ValueError:
            continue
        if math.isfinite(row['_rate']) and row['top_level_agency']:
            groups[row['top_level_agency']].append(row)
    predictions = {}
    for rows in groups.values():
        rows.sort(key=lambda r: (r['_date'], r['rin']))
        for left, right in zip(rows, rows[1:]):
            # Every pre-holdout 1096-day outcome window is now closed.
            if left['_date'] < date(2021, 1, 2):
                continue
            matured = [r for r in rows if left['_date'] <=
                       r['_date'] + timedelta(days=1096) < right['_date']]
            delta = right['_rate'] - left['_rate']
            if len(matured) == 1 and abs(delta) >= 1e-12:
                row = matured[0]
                predictions[row['rin']] = (int(delta > 0), int(row[target]))
    return {'scope': 'Bounded leakage diagnostic; not qualification or benchmark performance',
            'input_sha256': asset['sha256'], 'covered_targets': len(predictions),
            'mismatches': sum(p != y for p, y in predictions.values()),
            'label_use': 'Comparison only; predictions use agency, date, and rate features'}


if __name__ == '__main__':
    print(json.dumps(probe(sys.argv[1]), indent=2))
