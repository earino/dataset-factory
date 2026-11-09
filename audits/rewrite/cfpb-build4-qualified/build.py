import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from source_io import fetch

TARGET = 'monetary_relief'
ID_COL = 'complaint_id'
TIME_COL = 'date_received'
PRODUCT = 'Checking or savings account'
POS = 'Closed with monetary relief'
NEG = {'Closed with non-monetary relief', 'Closed with explanation', 'Closed without relief', 'Untimely response'}
FEATURES = ['sub_product', 'issue', 'sub_issue', 'company', 'state', 'submitted_via', 'month', 'weekday']
OUT_COLS = [ID_COL, TIME_COL] + FEATURES + [TARGET]
YEAR_START = pd.Timestamp('2019-01-01', tz='UTC')
TRAIN_END = pd.Timestamp('2022-01-01', tz='UTC')
EVAL_START = TRAIN_END
EVAL_END = pd.Timestamp('2023-01-01', tz='UTC')
HOLDOUT_START = EVAL_END
DATA_END = pd.Timestamp('2024-01-01', tz='UTC')
YEARS = [2019, 2020, 2021, 2022, 2023]
CATEGORICAL = ['sub_product', 'issue', 'sub_issue', 'company', 'state', 'submitted_via']
REQUIRED = [ID_COL, TIME_COL, 'product', 'company_response'] + CATEGORICAL
BASE_URL = 'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/'
USER_AGENT = 'curl/8.5.0'
EXPORT_CAP = 100000
MIN_YEAR_ROWS = 5000
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
WINDOW_BOUNDS = {
    'train': (None, pd.Timestamp('2022-01-01T00:00:00')),
    'eval': (pd.Timestamp('2022-01-01T00:00:00'), pd.Timestamp('2023-01-01T00:00:00')),
    'holdout': (pd.Timestamp('2023-01-01T00:00:00'), None),
}
SOURCE_FIELDS = {
    'complaint_id': ('Complaint ID', 'complaint_id'),
    'date_received': ('Date received', 'date_received'),
    'product': ('Product', 'product'),
    'sub_product': ('Sub-product', 'sub_product', 'Sub product'),
    'issue': ('Issue', 'issue'),
    'sub_issue': ('Sub-issue', 'sub_issue', 'Sub issue'),
    'company': ('Company', 'company'),
    'state': ('State', 'state'),
    'submitted_via': ('Submitted via', 'submitted_via'),
    'company_response': ('Company response to consumer', 'company_response_to_consumer', 'Company response', 'company_response'),
}

def _bounded(payload):
    return json.dumps(payload, ensure_ascii=False, default=str)[:4000]

def _raise_evidence(message, headers, missing_names=None, checks=None):
    payload = {
        'message': message,
        'observed_headers': list(headers)[:200],
        'missing_names': list(missing_names or []),
        'selected_archive_member': 'not applicable; direct CFPB search API CSV response',
    }
    if checks is not None:
        payload['failed_checks'] = [item for item in checks if not item['passed']]
    raise AssertionError(_bounded(payload))

def _add(checks, check, observed, expected, passed):
    checks.append({'check': check, 'observed': str(observed)[:1200], 'expected': str(expected)[:1200], 'passed': bool(passed)})

def _canon(name):
    text = str(name).replace(chr(65279), '').strip().lower()
    text = text.replace('_', ' ').replace('-', ' ')
    text = ' '.join(text.split())
    return text.rstrip('?').strip()

def _map_columns(page):
    canon_to_field = {}
    for field, aliases in SOURCE_FIELDS.items():
        for alias in aliases:
            canon_to_field[_canon(alias)] = field
    mapping = {}
    used = set()
    for column in page.columns:
        field = canon_to_field.get(_canon(column))
        if field is not None and field not in used:
            mapping[column] = field
            used.add(field)
    return page.rename(columns=mapping), mapping

def _read_page(path):
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()

def _force_user_agent(request):
    for container in (request.headers, request.unredirected_hdrs):
        for key in list(container):
            if key.lower() == 'user-agent':
                container.pop(key, None)
    request.add_unredirected_header('User-Agent', USER_AGENT)

def _install_user_agent():
    current = urllib.request.urlopen
    if getattr(current, '_cfpb_user_agent_wrapper', False):
        return
    original = current

    def wrapper(request, *args, **kwargs):
        if isinstance(request, urllib.request.Request):
            _force_user_agent(request)
        else:
            request = urllib.request.Request(request, headers={'User-Agent': USER_AGENT})
        return original(request, *args, **kwargs)

    wrapper._cfpb_user_agent_wrapper = True
    urllib.request.urlopen = wrapper

def _api_url(year):
    params = {
        'format': 'csv',
        'product': PRODUCT,
        'date_received_min': str(year) + '-01-01',
        'date_received_max': str(year) + '-12-31',
        'no_aggs': 'true',
    }
    return BASE_URL + '?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

def _fetch_year(year, cache):
    url = _api_url(year)
    name = 'cfpb_bank_complaints_' + str(year) + '_v2.csv'
    last_error = None
    for attempt in range(3):
        try:
            return fetch(url, cache, name)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (403, 429, 500, 502, 503, 504) or attempt == 2:
                raise
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                raise
        time.sleep(2 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError('annual CFPB CSV fetch failed without an exception')

def _naive_utc(frame):
    return frame['_dt'].dt.tz_convert('UTC').dt.tz_localize(None)

def _prepare(frame):
    out = frame.copy()
    naive = _naive_utc(out)
    out[TIME_COL] = naive.dt.strftime(TIME_FORMAT)
    out['month'] = naive.dt.month.astype(int)
    out['weekday'] = naive.dt.day_name()
    for column in CATEGORICAL:
        out[column] = out[column].astype(str).str.strip()
    out[ID_COL] = out[ID_COL].astype(str).str.strip()
    out[TARGET] = out[TARGET].astype(int)
    out = out.sort_values(['_dt', ID_COL], kind='mergesort')
    return out[OUT_COLS]

def build(output: Path, cache: Path):
    output = Path(output)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    (output / 'public').mkdir(parents=True, exist_ok=True)
    (output / 'private').mkdir(parents=True, exist_ok=True)
    _install_user_agent()
    checks = []
    frames = []
    per_year_rows = {}
    observed_headers = []
    first_mapping = {}
    missing_fields = []
    for year in YEARS:
        path = _fetch_year(year, cache)
        page = _read_page(path)
        if page is None or page.empty:
            _raise_evidence('Annual CFPB CSV export is empty', observed_headers, [], checks)
        page.columns = [str(column).replace(chr(65279), '').strip() for column in page.columns]
        if not observed_headers:
            observed_headers = list(page.columns)
        mapped, mapping = _map_columns(page)
        if not first_mapping:
            first_mapping = dict(mapping)
        missing = [field for field in REQUIRED if field not in set(mapping.values())]
        per_year_rows[str(year)] = int(len(page))
        if missing:
            missing_fields = missing
            break
        frames.append(mapped[REQUIRED].copy())
    _add(checks, 'Publisher CSV display headers map to declared field names', first_mapping, 'every declared source field has a canonical publisher header match', not missing_fields)
    _add(checks, 'CFPB annual CSV exposes required ID, time, population, label and feature fields', observed_headers, 'contains ' + ', '.join(REQUIRED), not missing_fields)
    if missing_fields:
        _raise_evidence('Required source fields are missing from the CFPB annual CSV export', observed_headers, missing_fields, checks)
    annual_ok = len(frames) == len(YEARS) and all(0 < int(per_year_rows.get(str(year), 0)) < EXPORT_CAP for year in YEARS)
    _add(checks, 'Annual CSV exports are complete and not truncated at the export cap', per_year_rows, 'each year between 1 and 99999 rows, below the publisher 100000-row CSV export cap', annual_ok)
    if not annual_ok:
        _raise_evidence('Annual CSV export row counts are empty or at the truncation cap', observed_headers, [], checks)
    raw = pd.concat(frames, ignore_index=True)
    raw['_dt'] = pd.to_datetime(raw[TIME_COL].astype(str).str.strip(), errors='coerce', utc=True)
    product_raw = raw['product'].astype(str).str.strip()
    included_product = product_raw.eq(PRODUCT)
    pop = raw[included_product].copy()
    other_products = product_raw[~included_product].value_counts().to_dict()
    _add(checks, 'Population product filter uses publisher product value', {'included_rows': int(len(pop)), 'other_product_counts': other_products}, 'rows with product equal to Checking or savings account included; other products excluded', len(pop) > 0)
    if len(pop) == 0:
        _raise_evidence('Product population is empty', observed_headers, [], checks)
    bad_dates = int(pop['_dt'].isna().sum())
    pop = pop[pop['_dt'].notna()].copy()
    in_window = (pop['_dt'] >= YEAR_START) & (pop['_dt'] < DATA_END)
    out_window = int((~in_window).sum())
    pop = pop[in_window].copy()
    year_counts = {int(key): int(value) for key, value in pop['_dt'].dt.year.value_counts().sort_index().items()}
    coverage_ok = bad_dates == 0 and all(int(year_counts.get(year, 0)) >= MIN_YEAR_ROWS for year in YEARS)
    _add(checks, 'Requested annual event windows return parsed rows', {'rows_by_year': year_counts, 'invalid_dates_in_product_rows': bad_dates, 'rows_outside_2019_2023_excluded': out_window}, 'zero unparseable dates among product rows; each year 2019 through 2023 represented with at least 5000 rows', coverage_ok)
    if not coverage_ok:
        _raise_evidence('Date parsing or annual coverage failed', observed_headers, [TIME_COL], checks)
    pop['company_response'] = pop['company_response'].astype(str).str.strip()
    response_counts = {str(key): int(value) for key, value in pop['company_response'].value_counts(dropna=False).items()}
    pos_mask = pop['company_response'].eq(POS)
    neg_mask = pop['company_response'].isin(NEG)
    known_mask = pos_mask | neg_mask
    unknown_counts = {str(key): int(value) for key, value in pop.loc[~known_mask, 'company_response'].value_counts(dropna=False).items()}
    scored = pop[known_mask].copy()
    scored[TARGET] = scored['company_response'].eq(POS).astype(int)
    label_ok = len(scored) > 0
    _add(checks, 'Label mapping uses exact terminal disposition strings', {'response_counts': response_counts, 'unknown_or_nonterminal_excluded': unknown_counts, 'scored_rows': int(len(scored))}, 'Closed with monetary relief maps to 1; recognized other terminal dispositions map to 0; in progress, blank and other responses are excluded', label_ok)
    if not label_ok:
        _raise_evidence('No scored rows after label mapping', observed_headers, [], checks)
    scored[ID_COL] = scored[ID_COL].astype(str).str.strip()
    missing_ids = int(scored[ID_COL].eq('').sum())
    missing_times = int(scored['_dt'].isna().sum())
    duplicate_ids = int(scored[ID_COL].duplicated().sum())
    id_ok = missing_ids == 0 and missing_times == 0 and duplicate_ids == 0
    _add(checks, 'Stable complaint IDs and event times are nonmissing and unique in scored rows', {'missing_ids': missing_ids, 'missing_times': missing_times, 'duplicate_ids': duplicate_ids}, 'zero missing and zero duplicate complaint IDs; zero missing event times', id_ok)
    if not id_ok:
        _raise_evidence('ID or time validation failed', observed_headers, [ID_COL, TIME_COL], checks)
    literal_nan = {column: int(scored[column].astype(str).str.strip().str.lower().eq('nan').sum()) for column in CATEGORICAL}
    blank_counts = {column: int(scored[column].astype(str).str.strip().eq('').sum()) for column in CATEGORICAL}
    _add(checks, 'Missing categorical values remain blank and are never zero or literal nan', {'literal_nan_counts': literal_nan, 'blank_counts': blank_counts}, 'zero literal nan strings; blank strings are allowed for optional intake fields', all(value == 0 for value in literal_nan.values()))
    if any(value > 0 for value in literal_nan.values()):
        _raise_evidence('Literal nan found in feature values', observed_headers, [column for column, value in literal_nan.items() if value > 0], checks)
    train = scored[(scored['_dt'] >= YEAR_START) & (scored['_dt'] < TRAIN_END)].copy()
    evald = scored[(scored['_dt'] >= EVAL_START) & (scored['_dt'] < EVAL_END)].copy()
    hold = scored[(scored['_dt'] >= HOLDOUT_START) & (scored['_dt'] < DATA_END)].copy()
    split_counts = {'train': int(len(train)), 'eval': int(len(evald)), 'holdout': int(len(hold))}
    splits_ok = all(value > 0 for value in split_counts.values())
    _add(checks, 'Fixed chronological half-open splits are nonempty', split_counts, 'train 2019-01-01 to 2022-01-01; eval 2022-01-01 to 2023-01-01; holdout 2023-01-01 onward', splits_ok)
    if not splits_ok:
        _raise_evidence('One or more fixed splits are empty', observed_headers, [], checks)
    partition_ok = sum(split_counts.values()) == len(scored)
    _add(checks, 'Every scored row falls in exactly one fixed split', {'split_rows': split_counts, 'scored_rows': int(len(scored))}, 'sum of split row counts equals scored row count', partition_ok)
    if not partition_ok:
        _raise_evidence('Scored rows do not partition into the fixed splits', observed_headers, [], checks)
    max_train = train['_dt'].max()
    min_eval = evald['_dt'].min()
    max_eval = evald['_dt'].max()
    min_hold = hold['_dt'].min()
    boundary_ok = bool(max_train < TRAIN_END) and bool(min_eval >= EVAL_START) and bool(max_eval < EVAL_END) and bool(min_hold >= HOLDOUT_START)
    _add(checks, 'Split boundaries are respected without row crossover', {'train_max': str(max_train), 'eval_min': str(min_eval), 'eval_max': str(max_eval), 'holdout_min': str(min_hold)}, 'train below 2022-01-01; eval from 2022-01-01 to below 2023-01-01; holdout from 2023-01-01', boundary_ok)
    if not boundary_ok:
        _raise_evidence('Split boundary crossover detected', observed_headers, [], checks)
    train_out = _prepare(train)
    eval_out = _prepare(evald)
    hold_out = _prepare(hold)
    columns_ok = list(train_out.columns) == OUT_COLS and list(eval_out.columns) == OUT_COLS and list(hold_out.columns) == OUT_COLS
    _add(checks, 'Constructed files contain exactly declared columns', {'train': list(train_out.columns), 'eval': list(eval_out.columns), 'holdout': list(hold_out.columns)}, OUT_COLS, columns_ok)
    if not columns_ok:
        _raise_evidence('Constructed output columns do not match declaration', observed_headers, [], checks)
    window_ranges = {}
    tz_aware_frames = []
    window_ok = True
    for label, frame in (('train', train_out), ('eval', eval_out), ('holdout', hold_out)):
        parsed = pd.to_datetime(frame[TIME_COL].astype(str).str.strip(), errors='coerce')
        start, end = WINDOW_BOUNDS[label]
        naive_frame = bool(parsed.notna().all()) and getattr(parsed.dt, 'tz', None) is None
        inside = bool(parsed.notna().all())
        if start is not None:
            inside = inside and bool((parsed >= start).all())
        if end is not None:
            inside = inside and bool((parsed < end).all())
        window_ranges[label] = {'min': str(parsed.min()), 'max': str(parsed.max()), 'rows': int(len(parsed))}
        if not naive_frame:
            tz_aware_frames.append(label)
        window_ok = window_ok and naive_frame and inside
    _add(checks, 'Written event timestamps are timezone-naive and inside the declared half-open split windows', {'ranges': window_ranges, 'tz_aware_or_unparsed_splits': tz_aware_frames}, 'every constructed time string parses without a timezone offset and lies within the declared train, eval and holdout windows', window_ok)
    if not window_ok:
        _raise_evidence('Constructed time values do not fit the declared naive split windows', observed_headers, [TIME_COL], checks)
    target_values = sorted(set(train_out[TARGET].unique()).union(set(eval_out[TARGET].unique())).union(set(hold_out[TARGET].unique())))
    target_ok = set(target_values).issubset({0, 1})
    _add(checks, 'Target is binary and unknown outcomes are not negative labels', {'target_values': target_values, 'unknown_or_nonterminal_excluded_count': int(sum(unknown_counts.values()))}, 'target values subset of 0 and 1; unknown outcomes excluded', target_ok)
    if not target_ok:
        _raise_evidence('Target is not binary', observed_headers, [], checks)
    leak = [column for column in FEATURES if column in ('company_response',)]
    _add(checks, 'No post-intake label or disposition field is used as a feature', leak, 'empty feature-label overlap', len(leak) == 0)
    if leak:
        _raise_evidence('Label leakage in features', observed_headers, leak, checks)
    time_all = pd.concat([train_out[TIME_COL], eval_out[TIME_COL], hold_out[TIME_COL]], ignore_index=True)
    month_all = pd.concat([train_out['month'], eval_out['month'], hold_out['month']], ignore_index=True)
    weekday_all = pd.concat([train_out['weekday'], eval_out['weekday'], hold_out['weekday']], ignore_index=True)
    parsed_all = pd.to_datetime(time_all, errors='coerce')
    calendar_ok = bool(parsed_all.notna().all()) and bool(month_all.eq(parsed_all.dt.month).all()) and bool(weekday_all.eq(parsed_all.dt.day_name()).all())
    _add(checks, 'Calendar features are deterministic functions of the event date', {'parsed_rows': int(parsed_all.notna().sum()), 'months_match': bool(month_all.eq(parsed_all.dt.month).all()), 'weekdays_match': bool(weekday_all.eq(parsed_all.dt.day_name()).all())}, 'every month matches the parsed month and every weekday matches the parsed day name', calendar_ok)
    if not calendar_ok:
        _raise_evidence('Calendar feature derivation failed', observed_headers, ['month', 'weekday'], checks)
    id_sets = [set(train_out[ID_COL]), set(eval_out[ID_COL]), set(hold_out[ID_COL])]
    overlap = (id_sets[0] & id_sets[1]) | (id_sets[0] & id_sets[2]) | (id_sets[1] & id_sets[2])
    overlap_ok = len(overlap) == 0
    _add(checks, 'Complaint IDs do not overlap across the three fixed splits', {'overlap_count': int(len(overlap))}, 'zero overlapping complaint IDs', overlap_ok)
    if not overlap_ok:
        _raise_evidence('Complaint ID overlap across splits', observed_headers, [ID_COL], checks)
    sorted_ok = all(frame[TIME_COL].is_monotonic_increasing for frame in (train_out, eval_out, hold_out))
    _add(checks, 'Constructed rows are sorted deterministically by event time and ID', sorted_ok, 'each split is nondecreasing by date_received', sorted_ok)
    if not sorted_ok:
        _raise_evidence('Constructed rows are not sorted', observed_headers, [TIME_COL], checks)
    destinations = [('public/train.csv', train_out), ('public/eval.csv', eval_out), ('private/holdout.csv', hold_out)]
    for name, frame in destinations:
        frame.to_csv(output / name, index=False)
    written = {name: int((output / name).stat().st_size) for name, frame in destinations}
    write_ok = all(value > 0 for value in written.values())
    _add(checks, 'Constructed CSV files exist and are nonempty', written, 'each output file larger than zero bytes', write_ok)
    if not write_ok:
        _raise_evidence('Constructed output file is empty', observed_headers, [], checks)
    return checks
