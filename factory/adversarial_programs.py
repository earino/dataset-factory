"""Bounded, data-only attack expressions; no Python evaluation or filesystem access.

An auditor can compose unfamiliar hypotheses from feature columns, unique joins,
group aggregates, arithmetic and text operations. The interpreter receives only a
Panel, never a dataset path or labels. A successful hypothesis remains a finding
requiring semantic review, not a proof that a lucky prediction is an identity.
"""
from __future__ import annotations

from datetime import date
import math
import re

from .recovery_recipes import day, number, integer_product

VERSION = '1.0.0'
MAX_PROGRAMS, MAX_NODES, MAX_DEPTH = 16, 96, 12
MAX_CELL_OPERATIONS = 80_000_000
MAX_STRING = 4096
UNARY = {'number', 'date', 'length', 'lower', 'abs', 'not', 'missing'}
BINARY = {'add', 'sub', 'mul', 'div', 'mod', 'eq', 'lt', 'le', 'gt', 'ge',
          'and', 'or', 'contains', 'coalesce'}


def finite(value):
    return type(value) in (float, int) and math.isfinite(value)


def validate(programs, columns, target):
    """Reject unknown keys, target references and unbounded programs before execution."""
    if not isinstance(programs, list) or not 1 <= len(programs) <= MAX_PROGRAMS:
        raise ValueError('auditor must supply 1..16 attack programs')
    columns = set(columns)
    if target in columns:
        raise ValueError('target entered feature schema')
    names, total = set(), 0

    def column(name):
        if not isinstance(name, str) or name not in columns or name == target:
            raise ValueError('attack references unavailable or target column')

    def node(expr, depth=0):
        nonlocal total
        total += 1
        if depth > MAX_DEPTH or not isinstance(expr, dict):
            raise ValueError('invalid or excessively deep attack expression')
        op = expr.get('op')
        if op == 'column':
            keys = {'op', 'name'}; column(expr.get('name'))
        elif op == 'constant':
            keys = {'op', 'value'}; v = expr.get('value')
            if not (v is None or finite(v) or isinstance(v, str) and len(v) <= 256):
                raise ValueError('invalid attack constant')
        elif op in UNARY | BINARY | {'if', 'rounded_count'}:
            keys = {'op', 'args'}
            arity = 1 if op in UNARY else 3 if op in {'if', 'rounded_count'} else 2
            args = expr.get('args')
            if not isinstance(args, list) or len(args) != arity:
                raise ValueError('invalid attack operator arity')
            for arg in args: node(arg, depth+1)
        elif op == 'slice':
            keys = {'op', 'value', 'start', 'stop'}
            if any(type(expr.get(k)) is not int or abs(expr[k]) > MAX_STRING
                   for k in ('start', 'stop')):
                raise ValueError('invalid string slice bounds')
            node(expr.get('value'), depth+1)
        elif op in {'join', 'group'}:
            keys = {'op', 'keys', 'value'}
            entity = expr.get('keys')
            if not isinstance(entity, list) or not 1 <= len(entity) <= 4:
                raise ValueError('attack join/group needs 1..4 feature keys')
            for name in entity: column(name)
            if len(set(entity)) != len(entity):
                raise ValueError('duplicate entity key')
            node(expr.get('value'), depth+1)
            if op == 'join':
                keys |= {'time', 'offset', 'unit'}
                column(expr.get('time'))
                if expr.get('unit') not in ('days', 'months', 'years'):
                    raise ValueError('invalid join offset unit')
                node(expr.get('offset'), depth+1)
            else:
                keys.add('aggregate')
                if expr.get('aggregate') not in ('count', 'sum', 'min', 'max', 'unique'):
                    raise ValueError('invalid group aggregate')
        else:
            raise ValueError('unknown attack operator')
        if set(expr) != keys:
            raise ValueError('unexpected or missing attack expression keys')

    for program in programs:
        if not isinstance(program, dict) or set(program) != {'name', 'rationale', 'expression'}:
            raise ValueError('invalid attack program record')
        name = program['name']
        if not isinstance(name, str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}', name) or name in names:
            raise ValueError('invalid or duplicate attack name')
        names.add(name)
        if not isinstance(program['rationale'], str) or not 40 <= len(program['rationale']) <= 3000:
            raise ValueError('attack requires a bounded semantic rationale')
        before = total; node(program['expression'])
        if total-before > MAX_NODES:
            raise ValueError('attack expression node limit exceeded')
    return total


def shifted(ordinal, amount, unit):
    if ordinal is None or not finite(amount) or amount != int(amount) or abs(amount) > 36600:
        return None
    try:
        d = date.fromordinal(ordinal)
        if unit == 'days': return date.fromordinal(ordinal+int(amount)).toordinal()
        months = int(amount) * (12 if unit == 'years' else 1)
        year, month = divmod(d.year*12+d.month-1+months, 12)
        return d.replace(year=year, month=month+1).toordinal()
    except (ValueError, OverflowError):
        return None


def scalar(op, args):
    """Missing, non-finite, invalid and ambiguous operands propagate abstention."""
    if op == 'missing': return float(args[0] is None or args[0] == '')
    if op == 'coalesce': return args[1] if args[0] is None else args[0]
    if op == 'if':
        return args[1] if args[0] == 1 else args[2] if args[0] == 0 else None
    if any(a is None for a in args): return None
    if op == 'number':
        result = number(args[0]); return result if finite(result) else None
    if op == 'date': return day(args[0])
    if op in {'length', 'lower'}:
        if not isinstance(args[0], str): return None
        return len(args[0]) if op == 'length' else args[0].lower()
    if op == 'contains':
        return float(args[1] in args[0]) if all(isinstance(a, str) for a in args) else None
    if op == 'eq':
        same_type = type(args[0]) == type(args[1]) or all(finite(a) for a in args)
        return float(same_type and args[0] == args[1])
    if not all(finite(a) for a in args): return None
    a = args[0]; b = args[1] if len(args) > 1 else None
    if op in {'and', 'or', 'not'}:
        if any(v not in (0, 1) for v in args): return None
        return float(not a) if op == 'not' else float(a and b) if op == 'and' else float(a or b)
    if op == 'rounded_count':
        if args[2] != int(args[2]) or not 0 <= args[2] <= 12: return None
        return integer_product(str(a), str(b), int(args[2]))
    try:
        if op == 'abs': result = abs(a)
        elif op == 'add': result = a+b
        elif op == 'sub': result = a-b
        elif op == 'mul': result = a*b
        elif op == 'div': result = a/b
        elif op == 'mod': result = a%b
        elif op == 'lt': result = float(a < b)
        elif op == 'le': result = float(a <= b)
        elif op == 'gt': result = float(a > b)
        elif op == 'ge': result = float(a >= b)
        else: raise ValueError('unknown scalar operation')
    except (ZeroDivisionError, OverflowError):
        return None
    return result if finite(result) else None


def evaluate(panel, expression, donors):
    """Evaluate a validated expression in linear work per node; joins are unique-only."""
    n, cols = panel.n, panel.cols
    def run(expr):
        op = expr['op']
        if op == 'column': return cols[expr['name']]
        if op == 'constant': return [expr['value']] * n
        if op == 'slice':
            return [v[expr['start']:expr['stop']] if isinstance(v, str) else None
                    for v in run(expr['value'])]
        if op in {'join', 'group'}:
            values = run(expr['value'])
            def key(i):
                parts = tuple(cols[c][i] for c in expr['keys'])
                return parts if all(v not in (None, '') for v in parts) else None
            if op == 'join':
                offsets = run(expr['offset']); days = [day(v) for v in cols[expr['time']]]
                index = {}
                for j in donors:
                    k = key(j)
                    if k is None or days[j] is None: continue
                    k = (k, days[j]); index[k] = None if k in index else j
                output = []
                for i in range(n):
                    j = index.get((key(i), shifted(days[i], offsets[i], expr['unit'])))
                    output.append(values[j] if j is not None else None)
                return output
            aggregates = {}; invalid = set(); kind = expr['aggregate']
            for j in donors:
                k = key(j)
                if k is None: continue
                v = values[j]
                if v is None or kind in {'sum','min','max'} and not finite(v):
                    invalid.add(k); continue
                if kind == 'count': aggregates[k] = aggregates.get(k, 0)+1
                elif k not in aggregates: aggregates[k] = v
                elif kind == 'sum': aggregates[k] += v
                elif kind == 'min': aggregates[k] = min(aggregates[k], v)
                elif kind == 'max': aggregates[k] = max(aggregates[k], v)
                elif kind == 'unique' and aggregates[k] != v: invalid.add(k)
            return [aggregates.get(key(i)) if key(i) not in invalid else None for i in range(n)]
        return [scalar(op, args) for args in zip(*(run(arg) for arg in expr['args']))]
    return run(expression)


def predictions(panel, programs):
    nodes = validate(programs, panel.cols, panel.target)
    if panel.n * nodes * 4 > MAX_CELL_OPERATIONS:
        raise ValueError('attack work limit exceeded; split programs into bounded worker jobs')
    if any(not isinstance(v, str) or len(v) > MAX_STRING for values in panel.cols.values() for v in values):
        raise ValueError('attack feature string limit exceeded; inspection incomplete')
    for scope, split, rows, donors in panel.scopes():
        for program in programs:
            values = evaluate(panel, program['expression'], donors)
            yield {'name':program['name'], 'scope':scope, 'split':split}, [
                float(values[i]) if finite(values[i]) else float('nan') for i in rows]
