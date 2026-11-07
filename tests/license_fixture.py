"""Synthetic source transport fixture, exclusively for licence admission unit tests."""
import json
from pathlib import Path

from factory.license_evidence import import_browser, canonical
from factory.license_contract import build, check_card

TEXT=('Creative Commons Attribution 4.0. You may share and adapt this material with attribution. '
      'Credit Example Source. Suggested citation: Example Source dataset. '
      'The attribution condition and all source terms continue to apply to redistributed material.')
TEMPLATE='---\n{LICENSE_METADATA}\n---\n# Dataset\n\n{LICENSE_BLOCK}\n'


def prepare(root):
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    export=root/'browser-export.json'
    export.write_text(json.dumps({'requested_url':'https://source.example/terms',
                                 'final_url':'https://source.example/terms','status':200,
                                 'complete':True,'text':TEXT,'metadata':[],
                                 'links':['https://creativecommons.org/licenses/by/4.0/'],
                                 'provider':'synthetic native browser transport fixture'}))
    import_browser(export,root/'licensing/source',owner_hosts=['source.example'])
    export.unlink()
    def ref(text):return {'evidence':'licensing/source','quote':text}
    source={'id':'source','spdx':'CC-BY-4.0','evidence':['licensing/source'],
            'catalogue':'licensing/source','terms':'licensing/source',
            'designation':ref('Creative Commons Attribution 4.0'),
            'grant':ref('You may share and adapt this material with attribution.'),
            'attribution':ref('Credit Example Source.'),
            'citation':ref('Suggested citation: Example Source dataset.')}
    (root/'LICENSE-EVIDENCE.json').write_text(json.dumps({'version':1,'sources':[source]}))
    for name in ('LICENSE-MIT.txt','LICENSE-CC0-1.0.txt'):
        if not (root/name).exists():(root/name).write_text('Unit test own-terms fixture '+name)
    generated=build(root)
    (root/'license-receipt.json').write_bytes(canonical(generated['receipt'])+b'\n')
    (root/'LICENSE.md').write_text(generated['license'])
    (root/'card.md').write_text(check_card(TEMPLATE,generated['card'],template=True))
    return generated
