import io
import json
from pathlib import Path
import tempfile
import unittest
from email.message import Message

from factory.license_evidence import extract, inspect, fetch, import_browser, verify, signals


TERMS='Creative Commons Attribution 4.0. You may share and adapt this material with attribution. '+('The source terms and attribution are preserved. '*4)
URL='https://source.example/terms'


class Response(io.BytesIO):
    def __init__(self,body,*,status=200,url=URL,content_type='text/html'):
        super().__init__(body);self.status=status;self.url=url;self.headers=Message()
        self.headers['Content-Type']=content_type
    def geturl(self):return self.url


class LicenseEvidenceTests(unittest.TestCase):
    def test_metadata_and_visible_footer_conflict_is_refused(self):
        html=('<html><script id="__NEXT_DATA__" type="application/json">'+json.dumps(
              {'props':{'license_id':'cc-by','license_title':'Creative Commons Atribuição'}})+
              '</script><body>'+('Source catalogue and resource descriptions. '*5)+
              '<footer>Creative Commons Atribuição-SemDerivações 3.0</footer></body></html>').encode()
        capture=dict(extract(html,'text/html',URL),requested_url=URL,final_url=URL,channel='http',status=200,complete=True)
        report=inspect(capture,owner_hosts=['source.example'])
        self.assertFalse(report['ok'])
        self.assertTrue(any('conflicting' in p for p in report['problems']))
        self.assertEqual({'CC-BY','CC-BY-ND'},{g['family'] for g in report['observed_cc_grants']})

    def test_http_403_is_preserved_and_never_promoted_by_old_prose(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'evidence'
            result=fetch(URL,path,owner_hosts=['source.example'],opener=lambda *a,**k:
                         Response(b'<html><body>403 Forbidden</body></html>',status=403))
            self.assertFalse(result['inspection']['ok'])
            self.assertEqual(403,verify(path)['status'])
            self.assertTrue((path/'source-response.txt').is_file())

    def test_readable_source_is_reproducible_and_changed_text_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'evidence'
            result=fetch(URL,path,owner_hosts=['source.example'],opener=lambda *a,**k:
                         Response(('<html><body>'+TERMS+'</body></html>').encode()))
            self.assertTrue(result['inspection']['ok'],result['inspection'])
            self.assertEqual(result,verify(path))
            (path/'source-text.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError,'changed'):
                verify(path)

    def test_honest_native_browser_fallback_and_challenge_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);capture=root/'browser.json'
            value={'requested_url':URL,'final_url':URL,'status':200,'complete':True,
                   'text':TERMS,'metadata':[],'links':['https://creativecommons.org/licenses/by/4.0/'],
                   'provider':'native browser tool'}
            capture.write_text(json.dumps(value))
            result=import_browser(capture,root/'ok',owner_hosts=['source.example'])
            self.assertTrue(result['inspection']['ok']);verify(root/'ok')
            value['text']='Verify you are human. '+TERMS;capture.write_text(json.dumps(value))
            self.assertFalse(import_browser(capture,root/'blocked',owner_hosts=['source.example'])['inspection']['ok'])

    def test_redirect_to_different_owner_or_unknown_version_refuses(self):
        capture={'requested_url':URL,'final_url':'https://mirror.example/terms','status':200,'complete':True,
                 'text':TERMS,'metadata':[],'links':[],'channel':'http'}
        self.assertFalse(inspect(capture,owner_hosts=['source.example'])['ok'])
        capture['final_url']=URL;capture['text']=TERMS.replace('4.0','')
        self.assertFalse(inspect(capture,owner_hosts=['source.example'])['ok'])

    def test_cc_aliases_do_not_invent_an_unqualified_override(self):
        self.assertIn(('CC-BY-NC-SA','4.0'),signals('CC BY-NC-SA 4.0'))
        self.assertIn(('CC-BY-ND','3.0'),signals('Creative Commons Atribuição-SemDerivações 3.0'))
        self.assertIn(('CC-BY','4.0'),signals('https://creativecommons.org/licenses/by/4.0/'))


if __name__=='__main__':
    unittest.main()
