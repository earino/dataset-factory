"""Bind measurable prose to recomputed worker facts through generated claim blocks."""
import hashlib
import json
from pathlib import Path
import re

from .asset_integrity import safe_path, sha256
from .claim_facts import canonical, measure
from .claim_checks import DOC_NAMES, inspect
from .paired_claims import from_evidence

VERSION = '1.0.0'
BLOCK = re.compile(r'<!-- FACTORY-CLAIM ([a-z0-9-]+) -->\n(.*?)\n<!-- /FACTORY-CLAIM -->', re.S)


def implementation():
    return {name:sha256(Path(__file__).with_name(name)) for name in
            ('claim_facts.py','claim_checks.py','paired_claims.py','claim_contract.py','asset_integrity.py')}


def pointer(value, path):
    if not isinstance(path,str) or not path.startswith('/'):
        raise ValueError('claim source must use an explicit JSON pointer')
    for part in path[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        value=value[int(part)] if isinstance(value,list) else value[part]
    return value


def declaration(package):
    plan=json.loads(safe_path(package,'CLAIMS.json').read_text())
    claims=plan.get('claims')
    if plan.get('version')!=1 or not isinstance(claims,list) or not claims or len(claims)>200:
        raise ValueError('CLAIMS.json requires 1..200 explicit claims')
    ids=[c['id'] for c in claims]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch('[a-z0-9-]+',i) for i in ids):
        raise ValueError('claim ids must be distinct simple identifiers')
    return plan


def qualification_binding(package, path, *, historical=False):
    if path is None:
        raise ValueError('claims measurement requires the exact qualification report')
    report=json.loads(Path(path).read_text())
    results=report.get('results',[])
    mandatory={'battery.exact_recovery','battery.recorded_in_quality','artifacts.no_shipped_answers'}
    passed=(report.get('ok') is True and report.get('failed_checks')==[] and results
            and all(r.get('ok') is True for r in results)
            and mandatory <= {r.get('check') for r in results})
    if report.get('gate_version')!='1.6.0' or (not historical and not passed):
        raise ValueError('new package claims require passing gate 1.6 qualification')
    for key in ('train','eval','holdout','meta.json','quality.json'):
        entry=report['artifact'][key]
        if sha256(safe_path(Path(package),entry['file']))!=entry['sha256']:
            raise ValueError('claims bytes differ from the qualified artifact')
    return report


def compute(package, *, evidence_root=None, qualification=None, historical=False):
    package=Path(package); plan=declaration(package)
    report=qualification_binding(package,qualification,historical=historical)
    grains=[c['columns'] for c in plan['claims'] if c['kind']=='grain']
    facts=measure(package,grain_keys=grains)
    facts.update({'contract_version':VERSION,'implementation':implementation(),
                  'declaration_sha256':sha256(safe_path(package,'CLAIMS.json')),
                  'historical_only':historical,'paired':{},'source_values':{}})
    report_path=Path(qualification)
    for key in ('train','eval','holdout','meta.json','quality.json'):
        entry=report['artifact'][key]
        if facts['inputs'].get(entry['file'])!=entry['sha256']:
            raise ValueError('claims bytes differ from the qualified artifact')
    for name,expected in facts['inputs'].items():
        if report['artifact'].get('scanned_files',{}).get(name)!=expected:
            raise ValueError('factual input is absent or changed from qualified inventory: '+name)
    facts['qualification_sha256']=sha256(report_path)
    facts['artifact_version']=report['artifact']['artifact_version']['digest']
    for claim in plan['claims']:
        if claim['kind']=='paired_interval':
            if evidence_root is None:
                raise ValueError('paired claims require full scorer evidence on worker')
            facts['paired'][claim['id']]=from_evidence(package,evidence_root,claim['evidence'])
        elif claim['kind'] in ('summary_value','source_definition'):
            name='summary.json' if claim['kind']=='summary_value' else 'quality.json'
            source=safe_path(package,name)
            if claim['kind']=='source_definition' and not claim['pointer'].startswith(
                    ('/timing/','/external_threshold','/task/')):
                raise ValueError('source definitions are limited to timing, target and threshold declarations')
            value=pointer(json.loads(source.read_text()),claim['pointer'])
            if claim['kind']=='source_definition' and re.search(
                    r'\bprevalence\b|positive.rate|\d+\s*(?:rows|positives|exclusions)\b',str(value),re.I):
                raise ValueError('population claims cannot be disguised as source definitions')
            if isinstance(value,(dict,list)):
                raise ValueError('source claim must address a scalar')
            facts['source_values'][claim['id']]=value
            facts['inputs'][name]=sha256(source)
    facts['input_digest']=hashlib.sha256(canonical(facts['inputs'])).hexdigest()
    # Render every claim now, so missing evidence/false assertions fail on the worker.
    for claim in plan['claims']:
        render(claim,facts)
    return facts


def render(claim,facts):
    kind=claim['kind']; split=claim.get('split'); stats=facts['splits'].get(split)
    if kind=='population':
        return f"{split}: {stats['rows']:,} rows; {stats['positives']:,} positives; positive rate {stats['positive_rate']:.4%}."
    if kind=='domain':
        column=claim['column']; info=stats['columns'][column]
        if info['values_truncated']:
            raise ValueError('domain claim exceeds bounded domain evidence')
        if 'expected' in claim and sorted(claim['expected'])!=info['values']:
            raise ValueError('declared dictionary domain differs from actual values')
        return f"{split} `{column}` observed domain: "+', '.join('`'+v+'`' for v in info['values'])+'.'
    if kind=='years':
        column=claim['column']; years=stats['columns'][column]['years']
        if (not years or stats['columns'][column]['year_unparsed']
                or ('expected' in claim and claim['expected']!=years)):
            raise ValueError('claimed split years differ from observed years')
        return f"{split} `{column}` observed years: "+', '.join(map(str,years))+'.'
    if kind=='grain':
        keys=','.join(claim['columns']); observed=stats['grains'][keys]
        unique=observed['duplicate_rows']==0
        if type(claim.get('unique')) is not bool or claim['unique']!=unique:
            raise ValueError('claimed grain uniqueness differs from observed rows')
        return f"{split} grain ({keys}): {observed['distinct']:,} distinct keys; {observed['duplicate_rows']:,} repeated rows."
    if kind=='summary_value':
        observed=facts['source_values'][claim['id']]
        if claim.get('expected')!=observed:
            raise ValueError('claimed count differs from construction summary')
        return f"Construction summary `{claim['pointer']}` reports {observed}."
    if kind=='source_definition':
        return 'Source-bound construction declaration (not independently measured here): '+str(facts['source_values'][claim['id']])
    if kind=='paired_interval':
        r=facts['paired'][claim['id']]
        return (f"{r['split']} AUC difference ({r['left']} minus {r['right']}): {r['observed_difference']:+.6f}; "
                f"paired cluster bootstrap 95% interval [{r['ci95_low']:+.6f}, {r['ci95_high']:+.6f}] "
                f"({r['resamples']} resamples, seed {r['seed']}). Direction: {r['direction']}. "
                'An interval containing zero is inconclusive and does not establish equivalence.')
    raise ValueError('unsupported measurable claim kind: '+str(kind))


def validate(package,facts,*,external_assets=False,manifest=None):
    package=Path(package); findings=[]
    plan=declaration(package)
    if (facts.get('contract_version')!=VERSION or facts.get('implementation')!=implementation()
            or facts.get('declaration_sha256')!=sha256(safe_path(package,'CLAIMS.json'))
            or facts.get('historical_only') is not False):
        raise ValueError('claims facts are stale, historical-only or from different code/declarations')
    if facts.get('qualification_sha256')!=sha256(safe_path(package,'qualification.json')):
        raise ValueError('claims facts are not bound to this qualification report')
    if facts.get('input_digest')!=hashlib.sha256(canonical(facts['inputs'])).hexdigest():
        raise ValueError('claims input fingerprint is inconsistent')
    if manifest is None:
        manifest=json.loads(safe_path(package,'MANIFEST.json').read_text())
    if facts.get('artifact_version')!=manifest.get('artifact_version'):
        raise ValueError('claims facts describe a different artifact version')
    for name,expected in facts['inputs'].items():
        path=safe_path(package,name)
        if (external_assets and not path.is_file() and name.endswith('.csv')
                and manifest.get('assets',{}).get(name,{}).get('sha256')==expected):
            continue
        if sha256(path)!=expected:
            raise ValueError('claims input changed: '+name)
    rendered={c['id']:render(c,facts) for c in plan['claims']}
    used=set()
    for path in sorted(package.rglob('*')):
        if not path.is_file() or path.name not in DOC_NAMES:
            continue
        name=path.relative_to(package).as_posix()
        text=safe_path(package,name).read_text()
        for match in BLOCK.finditer(text):
            ident,body=match.groups();used.add(ident)
            if ident not in rendered or body!=rendered[ident]:
                findings.append({'rule':'claim_block_mismatch','file':name,'claim':ident})
        remainder=BLOCK.sub('',text)
        remainder=re.sub(r'\A---\n.*?\n---\n','',remainder,flags=re.S)
        remainder=re.sub(r'```.*?```','',remainder,flags=re.S)
        remainder=re.sub(r'https?://[^\s)>]+','',remainder)
        remainder=re.sub(r'`[A-Za-z_][A-Za-z0-9_./:-]*`','',remainder)
        remainder=re.sub(r'\bv\d{4}\.\d{2}\b','',remainder)
        remainder=re.sub(r'^\s*\d+\.\s+','',remainder,flags=re.M)
        for line in remainder.splitlines():
            if re.search(r'\d|\b(?:unique|non[- ]?unique|equivalent|inseparable)\b',line,re.I):
                findings.append({'rule':'unbound_numeric_prose','file':name,'text':line[:200]})
        if 'FACTORY-CLAIM' in remainder:
            findings.append({'rule':'malformed_claim_block','file':name})
    if used!=set(rendered):
        findings.append({'rule':'unbound_claims','unused':sorted(set(rendered)-used),'unknown':sorted(used-set(rendered))})
    result=inspect(package,facts)
    result['findings'].extend(findings)
    result['ok']=not result['findings'] and facts.get('ok') is True
    return result
