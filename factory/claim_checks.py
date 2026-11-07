"""Claim checks over compact worker facts and the exact package text.

Automatic checks supplement explicit claims; neither a declaration nor a prose
lint proves source semantics. Unknown semantic claims go to the independent audit.
"""
import ast
import json
from pathlib import Path
import re

from .asset_integrity import safe_path, sha256
from .claim_facts import VERSION, canonical, population_claims

DOC_NAMES = {'README.md', 'DATA_DICTIONARY.md', 'RELEASE_NOTES.md', 'VERIFICATION.md',
             'REPRODUCE.md', 'LOADING.md', 'card.md'}
NEGATION = re.compile(r'\b(?:no|not|never|cannot|without|doesn.t|isn.t|aren.t|not guaranteed)\b', re.I)
SCORING = re.compile(r'holdout|scor(?:e|ing)|benchmark|runner|evaluated agents?', re.I)
GUARANTEE = re.compile(r'guarantee\w*|enforc\w*|ensures?|keeps?[^.;]{0,60}outside|'
                       r'(?:stays?|remains?)\s+(?:sealed|outside)|sealed until', re.I)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def text_claims(text, facts=None):
    findings = []
    # Sentence-local negation: a disclaimer in one sentence cannot waive a later guarantee.
    for sentence in re.split(r'(?<=[.;!?])\s+|\n\s*\n', text):
        sentence = re.sub(r'\s+', ' ', sentence)
        if (re.search(r'(?:every|each|all).{0,70}(?:sha256|digest|hash).{0,70}(?:pinned|verified|checked)|'
                      r'build.{0,60}(?:fails?|refuses?).{0,80}(?:bytes?\s+chang|digest\s+mismatch)',sentence,re.I)
                and re.search(r'page|publisher|source|pinned bytes',sentence,re.I)
                and not NEGATION.search(sentence)):
            findings.append({'rule':'unsupported_source_digest_guarantee','text':sentence[:240]})
        for match in GUARANTEE.finditer(sentence):
            prefix = sentence[max(0, match.start()-85):match.start()]
            clause = re.split(r'\b(?:but|however|yet|although)\b', prefix, flags=re.I)[-1]
            if SCORING.search(sentence) and not NEGATION.search(clause):
                findings.append({'rule': 'unsupported_scoring_guarantee', 'text': sentence[:240]})
                break
        if re.search(r'\b(?:inseparable|equivalent|parity)\b', sentence, re.I) and re.search(
                r'(?:interval|spans? zero|contains? zero)', sentence, re.I) and not NEGATION.search(sentence):
            findings.append({'rule': 'interval_zero_is_not_equivalence', 'text': sentence[:240]})
    if re.search(r'edge over.{0,300}?\[\s*[-−]\d*\.\d+\s*,\s*[-−]\d*\.\d+\s*\]', text, re.S|re.I):
        findings.append({'rule': 'interval_direction',
                         'detail': 'An edge-over claim uses a negative interval; name and recompute left minus right'})
    if facts:
        time_column=facts.get('time_column')
        for match in re.finditer(r'\b(train(?:ing)?|eval|holdout)\s+(?:rows\s+cover\s+|years?\s+|period\s+)?'
                                 r'((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2})',text,re.I):
            split='train' if match[1].lower()=='training' else match[1].lower()
            info=facts['splits'][split]['columns'].get(time_column,{})
            years=info.get('years',[])
            if years and (int(match[2])!=min(years) or int(match[3])!=max(years)):
                findings.append({'rule':'split_year_range','split':split,'claimed':[int(match[2]),int(match[3])],
                                 'observed':[min(years),max(years)]})
        for sentence in re.split(r'[\n;]|(?<=[.!?])\s+', text):
            if not re.search(r'prevalence|positive.rate|escape.rate|exceedance.rate|rate.drifts?', sentence, re.I):
                continue
            expressions = [(m[1].lower(),m[2]) for m in re.finditer(
                r'\b(train|eval|holdout)(?:\s+(?:19|20)\d{2}(?:[-–](?:19|20)\d{2})?)?\s*\(?\s*(\d+(?:\.\d+)?)%', sentence,re.I)]
            expressions += [(m[2].lower(),m[1]) for m in re.finditer(
                r'(\d+(?:\.\d+)?)%\s*\b(train|eval|holdout)\b',sentence,re.I)]
            for split, literal in expressions:
                decimals = len(literal.split('.')[1]) if '.' in literal else 0
                observed = facts['splits'][split]['positive_rate']*100
                if abs(float(literal)-observed) > .5*10**(-decimals)+1e-12:
                    findings.append({'rule':'prevalence_prose','split':split,'claimed_percent':literal,
                                     'observed_percent':observed})
        for line in text.splitlines():
            match = re.match(r'\s*\|\s*`([^`]+)`\s*\|(.+)',line)
            if not match:
                continue
            column, description = match.groups()
            bins = set(re.findall(r'\b\d+\s*[-–]\s*\d+|\b\d+\+',description))
            if not bins:
                continue
            bins = {re.sub(r'\s','',x).replace('–','-') for x in bins}
            for split, stats in facts['splits'].items():
                info = stats['columns'].get(column)
                if not info or info['values_truncated']:
                    continue
                actual = set(info['values'])
                actual_bins = {v for v in actual if re.fullmatch(r'\d+-\d+|\d+\+',v)}
                if actual_bins and actual_bins != bins:
                    findings.append({'rule':'dictionary_bins','column':column,'split':split,
                                     'claimed':sorted(bins),'observed':sorted(actual)})
    return findings


def inspect(package, facts=None, *, verified_license=None):
    package = Path(package)
    findings = list(facts.get('problems',[])) if facts else []
    for path in sorted(package.rglob('*')):
        relative = path.relative_to(package).as_posix()
        if path.is_symlink():
            findings.append({'rule':'unsafe_claim_file','file':relative})
            continue
        if not path.is_file() or (path.name not in DOC_NAMES and path.name not in
                                 ('meta.json','quality.json','measurements.json','summary.json') and path.suffix!='.py'):
            continue
        if path.stat().st_size > 2*1024*1024:
            findings.append({'rule':'claim_file_too_large','file':relative})
            continue
        try:
            if path.suffix == '.py':
                found=[]
                for node in ast.walk(ast.parse(path.read_text())):
                    if isinstance(node,ast.Constant) and isinstance(node.value,str) and len(node.value)>20:
                        found.extend(text_claims(node.value,facts))
            elif path.suffix == '.json':
                obj = json.loads(path.read_text())
                found = population_claims(obj,facts) if facts else []
                for value in strings(obj):
                    found.extend(text_claims(value,facts))
            else:
                text=path.read_text()
                if verified_license is not None:
                    from .license_contract import without_generated
                    text=without_generated(text,verified_license)
                found = text_claims(text,facts)
            findings.extend(dict(f,file=relative) for f in found)
        except (ValueError,TypeError,KeyError,SyntaxError) as exc:
            findings.append({'rule':'claim_inspection_incomplete','file':relative,'error':str(exc)})
    # Bound reports, refuse incomplete inspection instead of dropping failures silently.
    unique = {canonical(f):f for f in findings}
    result = list(unique.values())
    if len(result) > 200:
        result = result[:200]+[{'rule':'claim_findings_truncated','count':len(result)}]
    return {'ok':not result,'findings':result,'full_row_facts':facts is not None}
