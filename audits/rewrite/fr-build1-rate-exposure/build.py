import json
import re
import time
from bisect import bisect_right
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd

from source_io import fetch

API_BASE = 'https://www.federalregister.gov/api/v1/documents.json'
FIELDS = [
    'document_number', 'title', 'type', 'publication_date',
    'regulation_id_numbers', 'agencies', 'cfr_references',
    'comments_close_on', 'start_page', 'end_page', 'abstract',
    'docket_ids', 'html_url',
]
RIN_RE = re.compile(r'^[0-9]{4}-[A-Z]{2}[0-9]{2}$')
EXCLUDE_RE = re.compile(
    r'\b(extension of comment period|extension of the comment period|'
    r'comment period extension|reopening of comment period|correction|'
    r'correcting|withdrawal|withdrawn|withdrawing)\b',
    re.IGNORECASE,
)
TARGET = 'finalized_within_36_months'
FEATURES = [
    'top_level_agency',
    'agency_is_subagency',
    'cfr_part_count',
    'cfr_title_count',
    'page_span',
    'abstract_char_count',
    'comment_period_days',
    'docket_id_count',
    'joint_issuance',
    'publication_month',
    'agency_prior_finalization_rate',
]
COLUMNS = ['rin', 'publication_date', TARGET] + FEATURES
HORIZON_DAYS = 1096
ARCHIVE_MEMBER = 'Federal Register API v1 pages for PRORULE 1994-2022-06-30 and RULE 1994-2026-11-07'


def _as_date(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _valid_rins(document):
    values = document.get('regulation_id_numbers') or []
    if not isinstance(values, list):
        values = [values]
    result = []
    for value in values:
        text = str(value).strip()
        if RIN_RE.match(text):
            result.append(text)
    return result


def _document_url(doc_type, start, end, page):
    params = [
        ('conditions[type][]', doc_type),
        ('conditions[publication_date][gte]', start),
        ('conditions[publication_date][lte]', end),
        ('per_page', '1000'),
        ('page', str(page)),
    ]
    for field in FIELDS:
        params.append(('fields[]', field))
    return API_BASE + '?' + urlencode(params)


def _load_page(url, cache, name):
    path = fetch(url, cache, name)
    with open(path, 'r', encoding='utf-8') as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or 'results' not in payload:
        keys = list(payload.keys())[:40] if isinstance(payload, dict) else type(payload).__name__
        message = (
            'Unexpected Federal Register API payload. selected archive member '
            + ARCHIVE_MEMBER
            + '; response keys '
            + str(keys)
        )[:4000]
        raise AssertionError(message)
    return payload


def _iter_documents(doc_type, first_year, last_year, last_month=12, last_day=31, cache=None):
    for year in range(first_year, last_year + 1):
        start = f'{year}-01-01'
        if year == last_year:
            end = f'{year}-{last_month:02d}-{last_day:02d}'
        else:
            end = f'{year}-12-31'
        page = 1
        while True:
            url = _document_url(doc_type, start, end, page)
            name = f'fr_{doc_type.lower()}_{year}_{page:05d}.json'
            payload = _load_page(url, cache, name)
            results = payload.get('results') or []
            if not results:
                break
            for item in results:
                yield item
            total = int(payload.get('count') or 0)
            if page * 1000 >= total:
                break
            page += 1
            time.sleep(0.1)


def _agency_fields(agencies):
    if not isinstance(agencies, list) or not agencies:
        return '', 0
    first = agencies[0] if isinstance(agencies[0], dict) else {}
    is_subagency = 0 if first.get('parent_id') is None else 1
    top = None
    for agency in agencies:
        if isinstance(agency, dict) and agency.get('parent_id') is None:
            top = agency
            break
    if top is None:
        top = first
    slug = top.get('slug') if isinstance(top, dict) else None
    if not slug and isinstance(top, dict):
        slug = top.get('name')
    return (str(slug) if slug else ''), is_subagency


def _make_row(rin, publication_date, document):
    agencies = document.get('agencies') or []
    top_level_agency, agency_is_subagency = _agency_fields(agencies)
    references = document.get('cfr_references') or []
    if not isinstance(references, list):
        references = []
    cfr_part_count = len(references)
    titles = set()
    for reference in references:
        if isinstance(reference, dict) and reference.get('title') is not None:
            titles.add(str(reference.get('title')))
    cfr_title_count = len(titles)

    page_span = np.nan
    start_page = document.get('start_page')
    end_page = document.get('end_page')
    try:
        if start_page is not None and end_page is not None:
            span = int(end_page) - int(start_page) + 1
            if span > 0:
                page_span = span
    except (TypeError, ValueError):
        pass

    abstract = document.get('abstract')
    abstract_char_count = len(abstract) if isinstance(abstract, str) else 0

    comment_period_days = np.nan
    comments_close_on = _as_date(document.get('comments_close_on'))
    if comments_close_on is not None:
        comment_period_days = (comments_close_on - publication_date).days

    docket_ids = document.get('docket_ids') or []
    docket_id_count = len(docket_ids) if isinstance(docket_ids, list) else 0
    joint_issuance = 1 if isinstance(agencies, list) and len(agencies) > 1 else 0

    return {
        'rin': rin,
        'publication_date': publication_date.isoformat(),
        TARGET: 0,
        'top_level_agency': top_level_agency,
        'agency_is_subagency': int(agency_is_subagency),
        'cfr_part_count': int(cfr_part_count),
        'cfr_title_count': int(cfr_title_count),
        'page_span': page_span,
        'abstract_char_count': int(abstract_char_count),
        'comment_period_days': comment_period_days,
        'docket_id_count': int(docket_id_count),
        'joint_issuance': int(joint_issuance),
        'publication_month': publication_date.month,
        'agency_prior_finalization_rate': np.nan,
        '_document_number': str(document.get('document_number') or ''),
        '_first_rule_after': None,
    }


def _split_name(publication_date):
    if date(1995, 1, 1) <= publication_date < date(2013, 1, 1):
        return 'train'
    if date(2013, 1, 1) <= publication_date < date(2018, 1, 1):
        return 'eval'
    if date(2018, 1, 1) <= publication_date < date(2022, 7, 1):
        return 'holdout'
    return None


def _record(checks, check, observed, expected, passed, kind=None):
    item = {
        'check': check,
        'observed': str(observed)[:4000],
        'expected': str(expected)[:4000],
        'passed': bool(passed),
    }
    if kind is not None:
        item['kind'] = kind
    checks.append(item)
    if not passed:
        message = (
            check
            + '. observed '
            + str(observed)[:1500]
            + '. expected '
            + str(expected)[:1500]
            + '. selected archive member '
            + ARCHIVE_MEMBER
        )[:4000]
        raise AssertionError(message)


def _csv_header(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.readline().strip().split(',')


def build(output: Path, cache: Path):
    output = Path(output)
    cache = Path(cache)
    public = output / 'public'
    private = output / 'private'
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)

    nprm_by_rin = {}
    for document in _iter_documents('PRORULE', 1994, 2022, 6, 30, cache):
        doc_type = str(document.get('type') or '')
        if doc_type and doc_type not in ('Proposed Rule', 'PRORULE'):
            continue
        publication_date = _as_date(document.get('publication_date'))
        if publication_date is None:
            continue
        if publication_date < date(1994, 1, 1) or publication_date > date(2022, 6, 30):
            continue
        rins = _valid_rins(document)
        if len(rins) != 1:
            continue
        if EXCLUDE_RE.search(str(document.get('title') or '')):
            continue
        row = _make_row(rins[0], publication_date, document)
        previous = nprm_by_rin.get(rins[0])
        if previous is None:
            nprm_by_rin[rins[0]] = row
        else:
            old_key = (previous['publication_date'], previous['_document_number'])
            new_key = (row['publication_date'], row['_document_number'])
            if new_key < old_key:
                nprm_by_rin[rins[0]] = row

    rules_by_rin = defaultdict(set)
    for document in _iter_documents('RULE', 1994, 2026, 11, 7, cache):
        publication_date = _as_date(document.get('publication_date'))
        if publication_date is None:
            continue
        for rin in _valid_rins(document):
            rules_by_rin[rin].add(publication_date)
    rules_by_rin = {rin: sorted(values) for rin, values in rules_by_rin.items()}

    for rin, row in nprm_by_rin.items():
        publication_date = _as_date(row['publication_date'])
        window_end = publication_date + timedelta(days=HORIZON_DAYS)
        dates = rules_by_rin.get(rin, [])
        index = bisect_right(dates, publication_date)
        row[TARGET] = 0
        row['_first_rule_after'] = None
        if index < len(dates) and dates[index] <= window_end:
            row[TARGET] = 1
            row['_first_rule_after'] = dates[index]

    rows = sorted(nprm_by_rin.values(), key=lambda item: (item['publication_date'], item['rin']))
    agency_state = defaultdict(lambda: {'items': [], 'pointer': 0, 'positives': 0, 'count': 0})
    for row in rows:
        publication_date = _as_date(row['publication_date'])
        agency = row.get('top_level_agency') or ''
        if not agency:
            row['agency_prior_finalization_rate'] = np.nan
        else:
            state = agency_state[agency]
            while state['pointer'] < len(state['items']) and state['items'][state['pointer']][0] < publication_date:
                state['positives'] += state['items'][state['pointer']][1]
                state['count'] += 1
                state['pointer'] += 1
            count = state['count']
            positives = state['positives']
            if count == 0:
                rate = 0.5
            elif count < 3:
                rate = (positives + 0.5) / (count + 1.0)
            else:
                rate = positives / float(count)
            row['agency_prior_finalization_rate'] = float(rate)
        if agency:
            agency_state[agency]['items'].append(
                (publication_date + timedelta(days=HORIZON_DAYS), row[TARGET])
            )

    split_records = {'train': [], 'eval': [], 'holdout': []}
    for row in rows:
        publication_date = _as_date(row['publication_date'])
        split = _split_name(publication_date)
        if split is None:
            continue
        split_records[split].append({column: row.get(column) for column in COLUMNS})

    train_frame = pd.DataFrame(split_records['train'], columns=COLUMNS)
    eval_frame = pd.DataFrame(split_records['eval'], columns=COLUMNS)
    holdout_frame = pd.DataFrame(split_records['holdout'], columns=COLUMNS)
    for frame in (train_frame, eval_frame, holdout_frame):
        if not frame.empty:
            frame.sort_values(['publication_date', 'rin'], kind='mergesort', inplace=True)
            frame.reset_index(drop=True, inplace=True)

    train_frame.to_csv(public / 'train.csv', index=False)
    eval_frame.to_csv(public / 'eval.csv', index=False)
    holdout_frame.to_csv(private / 'holdout.csv', index=False)

    checks = []
    _record(checks, 'eligible NPRM rows', len(nprm_by_rin), 'at least one row', len(nprm_by_rin) > 0)
    _record(checks, 'RIN-bearing Rule dates', len(rules_by_rin), 'at least one RIN', len(rules_by_rin) > 0)
    known_rin = '1400-AD82'
    known_dates = rules_by_rin.get(known_rin, [])
    known_observed = [value.isoformat() for value in known_dates[:10]]
    _record(
        checks,
        'known NPRM-to-final-rule link RIN 1400-AD82',
        known_observed,
        'Rule publication on 2015-08-19',
        date(2015, 8, 19) in known_dates,
    )

    expected_headers = COLUMNS
    for label, frame, path in (
        ('train', train_frame, public / 'train.csv'),
        ('eval', eval_frame, public / 'eval.csv'),
        ('holdout', holdout_frame, private / 'holdout.csv'),
    ):
        observed_headers = _csv_header(path)
        missing = [column for column in expected_headers if column not in observed_headers]
        _record(
            checks,
            f'{label} CSV header',
            {'headers': observed_headers, 'missing_names': missing},
            expected_headers,
            observed_headers == expected_headers and not missing,
        )

    frames = {'train': train_frame, 'eval': eval_frame, 'holdout': holdout_frame}
    for label, frame in frames.items():
        values = sorted(set(frame[TARGET].dropna().astype(int).tolist())) if not frame.empty else []
        nulls = int(frame[TARGET].isna().sum()) if not frame.empty else 0
        _record(
            checks,
            f'{label} target values',
            {'values': values, 'nulls': nulls},
            'only 0 and 1, no nulls',
            bool(values) and set(values).issubset({0, 1}) and nulls == 0,
        )

    all_frame = pd.concat([train_frame, eval_frame, holdout_frame], ignore_index=True)
    _record(
        checks,
        'shipped rows',
        len(all_frame),
        'at least one row in each split',
        len(train_frame) > 0 and len(eval_frame) > 0 and len(holdout_frame) > 0,
    )
    duplicate_mask = all_frame['rin'].duplicated(keep=False)
    duplicates = sorted(all_frame.loc[duplicate_mask, 'rin'].astype(str).unique().tolist())[:20]
    _record(
        checks,
        'join key rin uniqueness',
        {'duplicate_ids': duplicates, 'duplicate_rows': int(duplicate_mask.sum()), 'headers': list(all_frame.columns)},
        'no duplicate rin values',
        not duplicate_mask.any(),
    )

    for column in FEATURES:
        series = all_frame[column]
        if column == 'top_level_agency':
            passed = bool((series.fillna('').astype(str).str.len() > 0).any())
            observed = int((series.fillna('').astype(str).str.len() > 0).sum())
        elif column in ('cfr_part_count', 'cfr_title_count', 'docket_id_count', 'abstract_char_count'):
            numeric = pd.to_numeric(series, errors='coerce').fillna(0)
            passed = bool((numeric > 0).any())
            observed = int((numeric > 0).sum())
        else:
            passed = bool(series.notna().any())
            observed = int(series.notna().sum())
        missing = [name for name in FEATURES if name not in all_frame.columns]
        _record(
            checks,
            f'feature coverage {column}',
            {'nonempty_or_nonnull': observed, 'headers': list(all_frame.columns), 'missing_names': missing},
            'at least one evidence-bearing value, not an empty column',
            passed and not missing,
        )

    for column in ('agency_is_subagency', 'joint_issuance'):
        values = sorted(set(all_frame[column].dropna().astype(int).tolist()))
        _record(
            checks,
            f'boolean values {column}',
            values,
            'only 0 and 1',
            bool(values) and set(values).issubset({0, 1}),
        )
    month_values = sorted(set(all_frame['publication_month'].dropna().astype(int).tolist()))
    _record(
        checks,
        'publication month range',
        month_values,
        'months 1 through 12',
        bool(month_values) and min(month_values) >= 1 and max(month_values) <= 12,
    )

    prior = pd.to_numeric(all_frame['agency_prior_finalization_rate'], errors='coerce')
    _record(
        checks,
        'agency prior finalization rate range',
        {'min': float(prior.min()) if prior.notna().any() else None, 'max': float(prior.max()) if prior.notna().any() else None, 'nulls': int(prior.isna().sum())},
        'values between 0 and 1 inclusive',
        bool(prior.notna().any()) and float(prior.min()) >= 0.0 and float(prior.max()) <= 1.0,
    )

    positive_rows = int((all_frame[TARGET] == 1).sum())
    negative_rows = int((all_frame[TARGET] == 0).sum())
    _record(
        checks,
        'target non-vacuous',
        {'positives': positive_rows, 'negatives': negative_rows},
        'both positive and negative labels present',
        positive_rows > 0 and negative_rows > 0,
    )

    lags = []
    for row in rows:
        if row[TARGET] == 1 and row['_first_rule_after'] is not None:
            lags.append((row['_first_rule_after'] - _as_date(row['publication_date'])).days)
    _record(
        checks,
        'outcome horizon unit and frame',
        {'positive_lags': len(lags), 'min_lag_days': min(lags) if lags else None, 'max_lag_days': max(lags) if lags else None},
        'positive Rule lag is greater than 0 and no more than 1096 days',
        bool(lags) and min(lags) > 0 and max(lags) <= HORIZON_DAYS,
        kind='unit',
    )

    split_bounds = {
        'train': ('1995-01-01', '2013-01-01'),
        'eval': ('2013-01-01', '2018-01-01'),
        'holdout': ('2018-01-01', '2022-07-01'),
    }
    for label, frame in frames.items():
        start_text, end_text = split_bounds[label]
        dates = pd.to_datetime(frame['publication_date'], errors='coerce')
        passed = len(frame) > 0 and dates.notna().all() and (dates >= pd.Timestamp(start_text)).all() and (dates < pd.Timestamp(end_text)).all()
        observed = {
            'rows': len(frame),
            'min': str(dates.min()) if len(frame) else None,
            'max': str(dates.max()) if len(frame) else None,
        }
        _record(
            checks,
            f'{label} split window',
            observed,
            f'nonempty rows in [{start_text}, {end_text})',
            passed,
        )

    train_max = pd.to_datetime(train_frame['publication_date']).max()
    eval_min = pd.to_datetime(eval_frame['publication_date']).min()
    eval_max = pd.to_datetime(eval_frame['publication_date']).max()
    holdout_min = pd.to_datetime(holdout_frame['publication_date']).min()
    _record(
        checks,
        'chronological split order',
        {'train_max': str(train_max), 'eval_min': str(eval_min), 'eval_max': str(eval_max), 'holdout_min': str(holdout_min)},
        'train before eval and eval before holdout',
        train_max < eval_min and eval_max < holdout_min,
    )

    bad_rins = [str(value) for value in all_frame['rin'].tolist() if not RIN_RE.match(str(value))]
    _record(
        checks,
        'RIN format',
        bad_rins[:20],
        'all ids match four digits, a hyphen, two letters, two digits',
        len(bad_rins) == 0,
    )

    return checks
