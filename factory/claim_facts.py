"""Worker-side measurements for package claims; full rows, compact facts, no examples.

This does not infer semantics from prose. It always measures core population,
domains, declared grain and named min/max invariants. Explicit claim assertions
may add checks, but cannot disable those automatic checks.
"""
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re

from .asset_integrity import safe_path, sha256

VERSION = '1.0.0'
DOMAIN_LIMIT = 128
MISSING = {'', 'NA', 'N/A', 'null', 'None', 'nan'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def minmax_pairs(columns):
    pairs = set()
    for column in columns:
        for low, high in (('_min', '_max'), ('min_', 'max_'), ('minimum', 'maximum')):
            if low in column:
                other = column.replace(low, high)
                if other in columns:
                    pairs.add((column, other))
    return sorted(pairs)


def measure(root, *, grain_keys=()):
    root = Path(root)
    quality_path, meta_path = safe_path(root, 'quality.json'), safe_path(root, 'meta.json')
    quality, meta = json.loads(quality_path.read_text()), json.loads(meta_path.read_text())
    target, ids = quality['target'], meta['id_columns']
    entity_ids = (quality.get('id_columns_are_entity_keys') is True
                  and quality.get('expected_duplicate_ids') is True)
    if len(grain_keys)>16 or any(not key or not isinstance(key,list) for key in grain_keys):
        raise ValueError('at most 16 explicit nonempty grain key lists are supported')
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
        raise ValueError('claims require nonempty distinct declared id columns')
    inputs = {'quality.json': sha256(quality_path), 'meta.json': sha256(meta_path)}
    results, problems, seen_all = {}, [], set()
    for split in ('train', 'eval', 'holdout'):
        relative = quality['splits'][split]
        path = safe_path(root, relative)
        inputs[relative] = sha256(path)
        with path.open(newline='', encoding='utf-8') as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames
            if not columns or len(columns) > 128 or len(columns) != len(set(columns)):
                raise ValueError('claims require a bounded nonduplicated schema')
            if target not in columns or any(c not in columns for c in ids):
                raise ValueError('target or declared id column missing')
            domains = {c: set() for c in columns}
            numeric = {c: {'count': 0, 'min': None, 'max': None} for c in columns}
            years = {c: set() for c in columns if re.search(r'date|year|instant|time|month', c, re.I)}
            year_unparsed = Counter()
            pairs = minmax_pairs(columns)
            if any(c not in columns for key in grain_keys for c in key):
                raise ValueError('claimed grain column missing')
            grain_sets = {','.join(key): set() for key in grain_keys}
            violations = Counter()
            rows = positives = duplicate = shared = 0
            seen = set()
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError('ragged CSV in claims input')
                label = number(row[target])
                if label not in (0, 1):
                    raise ValueError('claims population needs binary labels')
                rows += 1; positives += int(label)
                key = tuple(row[c] for c in ids)
                duplicate += key in seen
                shared += key in seen_all
                seen.add(key)
                for fields in grain_keys:
                    grain_sets[','.join(fields)].add(tuple(row[c] for c in fields))
                for c, value in row.items():
                    if len(domains[c]) <= DOMAIN_LIMIT:
                        domains[c].add(value)
                    n = number(value)
                    if n is not None:
                        s = numeric[c]; s['count'] += 1
                        s['min'] = n if s['min'] is None else min(n, s['min'])
                        s['max'] = n if s['max'] is None else max(n, s['max'])
                    if c in years and re.match(r'^(?:19|20)\d{2}(?:$|[-/ T])', value):
                        years[c].add(int(value[:4]))
                    elif c in years and value not in MISSING:
                        year_unparsed[c] += 1
                for low, high in pairs:
                    if row[low] in MISSING or row[high] in MISSING:
                        continue
                    a, b = number(row[low]), number(row[high])
                    if a is None or b is None:
                        violations['unparseable:'+low+','+high] += 1
                    if a is not None and b is not None and a > b:
                        violations[low + '<=' + high] += 1
            seen_all.update(seen)
        if not rows:
            raise ValueError('empty claims input split')
        if (duplicate or shared) and not entity_ids:
            problems.append({'rule': 'declared_grain_unique', 'split': split,
                             'duplicate_rows': duplicate, 'shared_prior_split_ids': shared})
        for pair, count in sorted(violations.items()):
            problems.append({'rule': 'min_le_max', 'split': split, 'columns': pair, 'violations': count})
        results[split] = {'rows': rows, 'positives': positives, 'positive_rate': positives/rows,
                          'id_columns': ids, 'duplicate_rows': duplicate, 'shared_prior_split_ids': shared,
                          'id_role': 'declared_repeated_entity' if entity_ids else 'unique_row',
                          'grains': {name: {'distinct':len(keys),'duplicate_rows':rows-len(keys)}
                                     for name,keys in grain_sets.items()},
                          'columns': {c: {'numeric': numeric[c],
                              'values': sorted(domains[c]) if len(domains[c]) <= DOMAIN_LIMIT else [],
                              'values_truncated': len(domains[c]) > DOMAIN_LIMIT,
                              **({'years': sorted(years[c]),'year_unparsed':year_unparsed[c]}
                                 if c in years else {})} for c in columns}}
    if entity_ids and not any(s['duplicate_rows'] or s['shared_prior_split_ids'] for s in results.values()):
        problems.append({'rule':'claimed_nonunique_ids','detail':'Repeated entity identifiers claimed but none observed'})
    for name in ('summary.json',):
        path = safe_path(root, name)
        if path.is_file():
            inputs[name] = sha256(path)
    for name, expected in inputs.items():
        if sha256(safe_path(root, name)) != expected:
            raise ValueError('claims input changed during measurement')
    return {'version': VERSION, 'code_sha256': sha256(Path(__file__)), 'inputs': inputs,
            'input_digest': hashlib.sha256(canonical(inputs)).hexdigest(), 'splits': results,
            'time_column':quality.get('time_column'),
            'problems': problems, 'ok': not problems,
            'scope': 'full shipped rows; bounded domains; no row examples or source-semantic guarantee'}


def population_claims(document, facts):
    """Check conventional metadata/measurement split fields without builder opt-in."""
    findings = []
    def compare(path, split, field, value):
        actual = facts['splits'][split][field]
        n = number(value)
        if n is None:
            return
        if field == 'positive_rate':
            literal = str(value).lower()
            decimals = len(literal.split('.')[1]) if '.' in literal and 'e' not in literal else 12
            tolerance = max(1e-12, .5 * 10**(-decimals))
        else:
            tolerance = 0
        if abs(n-actual) > tolerance:
            findings.append({'rule': 'population_claim', 'path': path, 'claimed': value, 'observed': actual})
    def visit(obj, path):
        if isinstance(obj, dict):
            for field in ('rows', 'positives', 'positive_rate'):
                value = obj.get(field)
                if isinstance(value, dict):
                    for split in ('train', 'eval', 'holdout'):
                        if split in value:
                            compare(path+'/'+field+'/'+split, split, field, value[split])
            splits = obj.get('splits')
            if isinstance(splits, dict):
                for split in ('train', 'eval', 'holdout'):
                    if isinstance(splits.get(split), dict):
                        for field in ('rows', 'positives', 'positive_rate'):
                            if field in splits[split]:
                                compare(path+'/splits/'+split+'/'+field, split, field, splits[split][field])
            for key, value in obj.items():
                visit(value, path+'/'+key)
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                visit(value, path+'/'+str(i))
    visit(document, '')
    return findings
