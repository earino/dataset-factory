"""Generate release terms from captured source text, with no licence precedence rule.

The source's complete text travels with the package. Selecting relevant quotations
does not prove legal suitability; the release audit still reviews source scope and
compatibility. A failed capture can never be turned into permission by a decision.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from .asset_integrity import safe_path, sha256
from .license_evidence import canonical, inspect, verify, LIMIT

VERSION = '1.0.0'
ROOT = Path(__file__).resolve().parents[1]
BEGIN = '<!-- FACTORY-LICENSE -->'
END = '<!-- /FACTORY-LICENSE -->'
BLOCK = re.compile(re.escape(BEGIN)+r'\n(.*?)\n'+re.escape(END), re.S)
TERMS = re.compile(r'licen[cs]|\b(?:CC0|CC-BY|public domain|attribution|share.alike|'
                   r'non.commercial|relicens\w*|copyright|OGL|MIT)\b', re.I)
SCOPE = ('Only our contribution to this derived compilation is covered by the '
         'compilation terms. Upstream data retains its source terms. This is a '
         'derived research dataset, not an official or endorsed source product.')


def read_json(path):
    if path.stat().st_size > LIMIT:
        raise ValueError('licence declaration exceeds bounded evidence limit')
    return json.loads(path.read_text())


def quoted(text):
    # Keep source text literal even if it contains Markdown/HTML or backtick fences.
    length=max([3]+[len(m[0])+1 for m in re.finditer(r'`+',text)])
    fence='`'*length
    return fence+'text\n'+text+'\n'+fence


def build(package, *, fresh=False, now=None):
    package=Path(package)
    plan=read_json(safe_path(package,'LICENSE-EVIDENCE.json'))
    if plan.get('version') != 1 or not isinstance(plan.get('sources'),list) or not 1<=len(plan['sources'])<=16:
        raise ValueError('LICENSE-EVIDENCE.json requires one to sixteen sources')
    policy=read_json(ROOT/'config/licensing-policy.json')
    captures={};inputs={'LICENSE-EVIDENCE.json':sha256(package/'LICENSE-EVIDENCE.json')}
    sources=[];ids=set();full_text=[]
    now=now or datetime.now(timezone.utc)
    for source in plan['sources']:
        ident=source['id']
        if not isinstance(ident,str) or not re.fullmatch('[a-z0-9-]+',ident) or ident in ids:
            raise ValueError('source ids must be distinct simple identifiers')
        ids.add(ident)
        evidence=source['evidence']
        if not isinstance(evidence,list) or not 1<=len(evidence)<=8 or len(set(evidence))!=len(evidence):
            raise ValueError('each source needs one to eight distinct captured pages')
        if source.get('catalogue') not in evidence or source.get('terms') not in evidence:
            raise ValueError('each source must identify captured catalogue and terms pages; one page may serve both roles')
        source_captures={}
        for name in evidence:
            if not isinstance(name,str) or not name.startswith('licensing/'):
                raise ValueError('captured pages must be inside package licensing/')
            directory=safe_path(package,name)
            capture=verify(directory)
            if not capture['inspection']['ok']:
                raise ValueError(name+': '+'; '.join(capture['inspection']['problems']))
            if fresh:
                age=(now-datetime.fromisoformat(capture['captured_at'])).total_seconds()
                if not 0<=age<=24*3600:
                    raise ValueError(name+': packaging requires a new source fetch within 24 hours')
            for filename in ('capture.json','source-response.txt','source-text.txt'):
                relative=name+'/'+filename
                inputs[relative]=sha256(safe_path(package,relative))
            source_captures[name]=capture;captures[name]=capture
        # Conflicts across catalogue/terms pages are just as fatal as a footer conflict.
        combined=dict(next(iter(source_captures.values())))
        combined['text']='\n'.join(c['text'] for c in source_captures.values())
        combined['metadata']=[m for c in source_captures.values() for m in c['metadata']]
        combined['links']=[u for c in source_captures.values() for u in c['links']]
        result=inspect(combined,owner_hosts=combined['owner_hosts'])
        if not result['ok']:
            raise ValueError(ident+': '+'; '.join(result['problems']))
        def quote(key, *, optional=False):
            ref=source.get(key)
            if optional and ref is None:
                return None
            if not isinstance(ref,dict) or ref.get('evidence') not in source_captures:
                raise ValueError(ident+': '+key+' needs a reference to a captured source page')
            text=ref.get('quote')
            if not isinstance(text,str) or not text.strip() or text not in source_captures[ref['evidence']]['text']:
                raise ValueError(ident+': '+key+' must be an exact quotation from source text')
            return {'text':text,'url':source_captures[ref['evidence']]['final_url'],
                    'evidence':ref['evidence'],'text_sha256':source_captures[ref['evidence']]['inspection']['text_sha256']}
        item={'id':ident,'designation':quote('designation'),'grant':quote('grant'),
              'attribution':quote('attribution',optional=True),'citation':quote('citation',optional=True),
              'evidence':evidence}
        spdx=source.get('spdx','')
        grants=result['observed_cc_grants']
        known={g['family']+'-'+g['version'] for g in grants if g['version']}
        if known:
            if spdx not in known:
                raise ValueError(ident+': licence identifier differs from source text')
        elif not re.fullmatch(r'LicenseRef-[A-Za-z0-9.-]+',spdx):
            raise ValueError(ident+': custom terms require a LicenseRef identifier and verbatim designation')
        item['spdx']=spdx;sources.append(item)
    # Our terms are policy-derived, never used to override the upstream designation.
    code=dict(policy['code_default']);compilation=dict(policy['compilation_default'],scope=SCOPE)
    for entry in (code,compilation):
        inputs[entry['file']]=sha256(safe_path(package,entry['file']))
    receipt={'version':VERSION,'policy_version':policy['policy_version'],
             'policy_sha256':sha256(ROOT/'config/licensing-policy.json'),
             'implementation':{n:sha256(Path(__file__).with_name(n)) for n in
                               ('license_contract.py','license_evidence.py')},
             'inputs':inputs,'sources':sources,'code':code,'data_compilation':compilation}
    lines=['## Terms for this derived dataset','',
           'Our code and documentation: '+code['spdx']+' ('+code['file']+').',
           'Our compilation contribution: '+compilation['spdx']+' ('+compilation['file']+').',SCOPE]
    for source in sources:
        lines+=['','### Source: '+source['id'],
                'Preserved source designation ('+source['spdx']+'):',quoted(source['designation']['text']),
                'Source-stated grant:',quoted(source['grant']['text'])]
        for key in ('attribution','citation'):
            value=source[key]
            if value:
                lines += ['Source '+key+' (verbatim):',quoted(value['text'])]
        lines+=['Captured source pages:']+['- '+captures[n]['final_url'] for n in source['evidence']]
    lines+=['','Complete captured terms and evidence accompany this package in LICENSE.md and licensing/.',
            'These quotations do not resolve a conflict or certify legal compatibility; source scope remains part of release review.']
    card=BEGIN+'\n'+'\n'.join(lines)+'\n'+END
    for name,capture in sorted(captures.items()):
        full_text += ['','### Captured page: '+name,capture['final_url'],quoted(capture['text'])]
    license_doc='# Release terms and source evidence\n\n'+card+'\n\n## Complete source text\n'+'\n'.join(full_text)+'\n'
    if len(license_doc.encode())>LIMIT or len(canonical(receipt))>LIMIT:
        raise ValueError('generated terms exceed bounded release-document limit')
    manifest={'policy_version':policy['policy_version'],'code':code,'data_compilation':compilation,
              'source_data':{'spdx':' AND '.join(s['spdx'] for s in sources),
                             'status':'Source terms preserved verbatim; no precedence interpretation.',
                             'attribution':'\n'.join(s['attribution']['text'] for s in sources if s['attribution']),
                             'citation':'\n'.join(s['citation']['text'] for s in sources if s['citation']),
                             'evidence':sources,'derived_labelling':SCOPE},
              'evidence_receipt_sha256':hashlib.sha256(canonical(receipt)).hexdigest()}
    return {'receipt':receipt,'license':license_doc,'card':card,'manifest':manifest}


def without_generated(text, expected):
    matches=list(BLOCK.finditer(text))
    if any(m[0]!=expected for m in matches):
        raise ValueError('generated licence block differs from verified source evidence')
    remainder=BLOCK.sub('',text)
    if 'FACTORY-LICENSE' in remainder:
        raise ValueError('malformed generated licence block')
    return remainder


def check_card(text, expected, *, template=False):
    if template:
        if text.count('{LICENSE_BLOCK}')!=1:
            raise ValueError('card template requires exactly one {LICENSE_BLOCK}')
        text=text.replace('{LICENSE_BLOCK}',expected)
        text=text.replace('{LICENSE_METADATA}','license: other\nlicense_name: source-terms-preserved\nlicense_link: LICENSE.md')
    if len(list(BLOCK.finditer(text)))!=1:
        raise ValueError('card requires exactly one generated licence block')
    remainder=without_generated(text,expected)
    # Metadata is generated too; a bare CC0 card would override preserved upstream terms.
    metadata='license: other\nlicense_name: source-terms-preserved\nlicense_link: LICENSE.md'
    if metadata not in remainder:
        raise ValueError('card requires generated source-preserving licence metadata')
    remainder=remainder.replace(metadata,'')
    for line in remainder.splitlines():
        if TERMS.search(line):
            raise ValueError('card contains an ungenerated licence statement: '+line[:160])
    return text


def validate(package, *, manifest=None, fresh=False, template=None):
    package=Path(package);generated=build(package,fresh=fresh)
    receipt=read_json(safe_path(package,'license-receipt.json'))
    if receipt!=generated['receipt']:
        raise ValueError('licence receipt no longer matches source evidence, policy or implementation')
    if safe_path(package,'LICENSE.md').read_text()!=generated['license']:
        raise ValueError('LICENSE.md differs from generated source terms')
    card=safe_path(package,'card.md').read_text()
    check_card(card,generated['card'])
    if template is not None:
        check_card(template,generated['card'],template=True)
    if manifest is not None and manifest.get('licenses')!=generated['manifest']:
        raise ValueError('manifest licences differ from generated source terms')
    return generated
