"""Bounded source-owned licence evidence; unreadable/conflicting terms fail closed.

HTTP and native-browser captures share the same inspection. This module preserves
what the source says; it does not choose which conflicting grant should prevail.
"""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

VERSION='1.0.0'
LIMIT=240*1024
CHALLENGE=re.compile(r'access denied|403 forbidden|verify you are human|just a moment|'
                     r'checking your browser|enable javascript and cookies to continue|captcha',re.I)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metadata_fields(value):
    result=[]
    def visit(obj):
        if isinstance(obj,dict):
            for key,item in obj.items():
                if re.search('licen[cs]e|rights',key,re.I) and isinstance(item,(str,int,float)):
                    result.append({'key':key,'value':str(item)})
                if isinstance(item,(dict,list)):
                    visit(item)
        elif isinstance(obj,list):
            for item in obj:
                visit(item)
    visit(value)
    return result


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text=[];self.links=[];self.metadata=[];self.hidden=0;self.script=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('script','style'):
            self.hidden+=1
        if tag=='script':
            self.script=[]
        if tag in ('a','link') and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag=='meta' and re.search('licen[cs]e|rights',attrs.get('name','')+' '+attrs.get('property',''),re.I):
            self.metadata.append({'key':attrs.get('name') or attrs.get('property'),'value':attrs.get('content','')})
    def handle_endtag(self,tag):
        if tag=='script' and self.script is not None:
            try:
                self.metadata.extend(metadata_fields(json.loads(''.join(self.script))))
            except (ValueError,TypeError):
                pass
            self.script=None
        if tag in ('script','style'):
            self.hidden=max(0,self.hidden-1)
        if tag in ('p','div','li','h1','h2','h3','footer','br'):
            self.text.append('\n')
    def handle_data(self,data):
        if self.script is not None:
            self.script.append(data)
        if not self.hidden:
            self.text.append(data)


def extract(raw,content_type,url):
    text=raw.decode('utf-8',errors='strict')
    metadata=[];links=[]
    if 'json' in content_type:
        value=json.loads(text);metadata=metadata_fields(value)
    elif 'html' in content_type or re.search(r'<(?:html|!doctype|body|head)\b',text,re.I):
        parser=Page();parser.feed(text);parser.close()
        text=' '.join(parser.text)
        text=re.sub(r'[^\S\n]+',' ',text)
        text=re.sub(r'\n\s*\n+','\n',text).strip()
        metadata=parser.metadata;links=[urljoin(url,p) for p in parser.links]
    elif not content_type.startswith('text/'):
        raise ValueError('non-text source needs a native browser/document text capture')
    return {'text':text,'metadata':metadata,'links':sorted(set(links))}


def signals(text):
    """Finite extraction of contradictory CC grants; custom terms stay verbatim."""
    folded=''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c)).lower()
    found=[]
    for match in re.finditer(r'creativecommons\.org/licenses/(by(?:-(?:nc|nd|sa))*)/(\d\.\d)',folded):
        found.append(('CC-'+match[1].upper(),match[2]))
    for match in re.finditer(r'\bcc[ _-]*(by(?:[ _-]*(?:nc|nd|sa))*)(?:[ _-]*(\d\.\d))?\b',folded):
        family='CC-'+re.sub(r'[ _]+','-',match[1]).upper()
        found.append((family,match[2]))
    for match in re.finditer(r'creative commons\s+(?:attribution|atribuicao)([^\n<>]{0,65})',folded):
        rest=match[1];family='CC-BY'
        if re.search(r'noncommercial|naocomercial|nao.comercial',rest):family+='-NC'
        if re.search(r'noderiv|semderiv|sem.deriv|no.deriv',rest):family+='-ND'
        elif re.search(r'sharealike|compartilha',rest):family+='-SA'
        version=re.search(r'\b(\d\.\d)\b',rest)
        found.append((family,version[1] if version else None))
    return sorted(set(found),key=lambda x:(x[0],x[1] or ''))


def inspect(capture,*,owner_hosts):
    problems=[]
    requested=urlparse(capture.get('requested_url',''))
    final=urlparse(capture.get('final_url',''))
    if (requested.scheme!='https' or final.scheme!='https' or requested.username or final.username
            or requested.hostname not in owner_hosts or final.hostname not in owner_hosts):
        problems.append('source URL is not on the declared owner hosts')
    if capture.get('channel') not in ('http','native_browser'):
        problems.append('unknown evidence capture channel')
    if capture.get('status')!=200 or capture.get('complete') is not True:
        problems.append('source unreadable or incomplete; interpretation cannot replace readable terms')
    text=capture.get('text','')
    if not isinstance(text,str) or len(text.strip())<120 or CHALLENGE.search(text[:3000]):
        problems.append('source text is absent, too short or a challenge/error page')
    observations=signals(text)
    for item in capture.get('metadata',[]):
        observations.extend(signals(str(item.get('value',''))))
    for link in capture.get('links',[]):
        observations.extend(signals(link))
    observations=sorted(set(observations),key=lambda x:(x[0],x[1] or ''))
    families={family for family,_ in observations}
    versions={version for _,version in observations if version}
    if len(families)>1 or len(versions)>1:
        problems.append('conflicting source licence metadata/text/links; no precedence interpretation is allowed')
    if observations and not versions:
        problems.append('source licence version is unresolved')
    return {'ok':not problems,'problems':problems,
            'observed_cc_grants':[{'family':f,'version':v} for f,v in observations],
            'text_sha256':sha(text.encode()) if isinstance(text,str) else None,
            'scope':'readability and consistency only; no independent permission/legal interpretation'}


def save_capture(directory,capture,raw,*,owner_hosts):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    (directory/'license-evidence-owner.json').write_bytes(canonical({'owner':'factory/license-evidence','version':VERSION})+b'\n')
    if len(raw)>LIMIT:
        raise ValueError('licence raw capture exceeds bounded evidence limit')
    if len(canonical(capture))>LIMIT-8192:
        capture=dict(capture,text=capture.get('text','')[:64000],metadata=[],links=[],complete=False,
                     capture_error='extracted licence evidence exceeded bounded capture limit')
    (directory/'source-response.txt').write_bytes(raw)
    (directory/'source-text.txt').write_text(capture.get('text',''))
    capture=dict(capture,raw_sha256=sha(raw),raw_bytes=len(raw),
                 captured_at=datetime.now(timezone.utc).isoformat(),owner_hosts=sorted(owner_hosts),
                 version=VERSION,implementation_sha256=sha(Path(__file__).read_bytes()))
    result=inspect(capture,owner_hosts=owner_hosts)
    capture['inspection']=result
    (directory/'capture.json').write_bytes(canonical(capture)+b'\n')
    return capture


def fetch(url,directory,*,owner_hosts,opener=urlopen):
    if urlparse(url).scheme!='https' or urlparse(url).hostname not in owner_hosts:
        raise ValueError('fetch URL must be HTTPS on a declared source owner host')
    capture={'requested_url':url,'final_url':url,'channel':'http','status':None,
             'complete':False,'text':'','metadata':[],'links':[]}
    raw=b''
    try:
        request=Request(url,headers={'User-Agent':'DatasetFactory-LicenseEvidence/1.0','Accept':'text/html,application/json,text/plain'})
        try:
            response=opener(request,timeout=30)
        except HTTPError as error:
            response=error
        with response:
            capture.update(status=response.status,final_url=response.geturl(),content_type=response.headers.get_content_type())
            raw=response.read(LIMIT+1)
        capture['complete']=len(raw)<=LIMIT
        raw=raw[:LIMIT]
        capture.update(extract(raw,capture['content_type'],capture['final_url']))
    except (OSError,ValueError,UnicodeError,RecursionError,URLError) as exc:
        capture['capture_error']=type(exc).__name__+': '+str(exc)
        capture['complete']=False
    return save_capture(directory,capture,raw,owner_hosts=owner_hosts)


def import_browser(path,directory,*,owner_hosts):
    """Import the existing native browser's exported capture; never install a browser."""
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>LIMIT:
        raise ValueError('invalid browser capture file')
    raw=path.read_bytes();capture=json.loads(raw)
    required={'requested_url','final_url','status','complete','text','links','metadata','provider'}
    if not isinstance(capture,dict) or not required<=set(capture) or not capture['provider']:
        raise ValueError('browser capture lacks URL, complete text, metadata, provider or status')
    capture['channel']='native_browser'
    return save_capture(directory,capture,raw,owner_hosts=owner_hosts)


def verify(directory):
    directory=Path(directory)
    paths=[directory/n for n in ('capture.json','source-response.txt','source-text.txt')]
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size>LIMIT for p in paths):
        raise ValueError('missing, unsafe or oversized licence evidence')
    capture=json.loads(paths[0].read_text());raw=paths[1].read_bytes()
    if (capture.get('version')!=VERSION or capture.get('implementation_sha256')!=sha(Path(__file__).read_bytes())
            or capture.get('raw_sha256')!=sha(raw) or capture.get('raw_bytes')!=len(raw)
            or paths[2].read_text()!=capture.get('text')):
        raise ValueError('licence evidence bytes or implementation changed')
    result=inspect(capture,owner_hosts=capture['owner_hosts'])
    if capture.get('inspection')!=result:
        raise ValueError('licence inspection receipt differs from source bytes')
    if result['ok']:
        if capture['channel']=='http':
            derived=extract(raw,capture['content_type'],capture['final_url'])
            for field in ('text','metadata','links'):
                if derived[field]!=capture[field]:
                    raise ValueError('licence text/metadata do not reproduce from captured source response')
        else:
            original=json.loads(raw)
            for field in ('text','metadata','links','requested_url','final_url','status','complete','provider'):
                if original[field]!=capture[field]:
                    raise ValueError('licence receipt differs from native browser capture')
    return capture
