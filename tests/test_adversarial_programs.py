"""Safety and causal phase tests, not historical dataset acceptance."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from factory import adversarial_programs as p
from factory import adversarial_execution as execution
from factory import leakage_battery as battery
from factory.recovery_recipes import Panel


def col(name): return {'op':'column', 'name':name}
def const(value): return {'op':'constant', 'value':value}
def op(name, *args): return {'op':name, 'args':list(args)}
def attack(expression):
    return {'name':'novel_identity', 'rationale':
            'The later observation may disclose a prior outcome through its feature value.',
            'expression':expression}


def join(value, offset=1, unit='days'):
    return {'op':'join', 'keys':['entity'], 'time':'date', 'offset':const(offset),
            'unit':unit, 'value':value}


class ExpressionTests(unittest.TestCase):
    def panel(self):
        return Panel({'entity':['A','A','A','B'],
                      'date':['2024-01-01','2024-01-02','2024-01-03','2024-01-01'],
                      'operand':['5','50','5','unknown'], 'text':['abc','DEF','abc','']},
                     {'train':(0,0), 'eval':(0,2), 'holdout':(2,4)}, 'label')

    def test_unfamiliar_composed_identity_and_donor_scopes(self):
        expr = op('gt', op('sub', join(op('number',col('operand'))),
                         op('number',col('operand'))), const(20))
        result = {(r['scope'],r['split']):v for r,v in p.predictions(self.panel(),[attack(expr)])}
        self.assertEqual(1, result['self','eval'][0])
        self.assertTrue(math.isnan(result['self','eval'][1]))
        self.assertEqual([1,0], result['all','eval'])

    def test_duplicate_donor_does_not_choose_a_convenient_row(self):
        panel = self.panel(); panel.cols['date'][2] = '2024-01-02'
        values = p.evaluate(panel, join(op('number',col('operand'))), range(panel.n))
        self.assertIsNone(values[0])

    def test_group_unique_and_invalid_operands_abstain(self):
        panel = self.panel()
        expr = {'op':'group','keys':['entity'],'aggregate':'unique','value':col('operand')}
        self.assertEqual([None,None,None,'unknown'], p.evaluate(panel,expr,range(panel.n)))
        expr.update(aggregate='sum', value=op('number',col('operand')))
        self.assertEqual([60,60,60,None], p.evaluate(panel,expr,range(panel.n)))

    def test_text_date_and_rounded_arithmetic(self):
        self.assertEqual(1, p.scalar('contains',['hello','ell']))
        self.assertEqual('abc', p.scalar('lower',['ABC']))
        self.assertIsNone(p.scalar('div',[1,0]))
        self.assertIsNone(p.scalar('gt',[None,0]))
        self.assertEqual(1, p.scalar('rounded_count',[3,.3333,4]))
        self.assertIsNone(p.scalar('rounded_count',[100000,.5,4]))
        self.assertIsNone(p.shifted(p.day('2024-01-31'),1,'months'))
        self.assertEqual(p.day('2024-02-29'),p.shifted(p.day('2024-02-28'),1,'days'))

    def test_no_code_io_hidden_keys_target_or_unbounded_expression(self):
        panel = self.panel()
        invalid = [col('label'), {'op':'eval','args':[const('__import__("os")')]},
                   {'op':'column','name':'operand','path':'/secret'},
                   {'op':'constant','value':float('inf')},
                   {'op':'constant','value':True},
                   {'op':'constant','value':'x'*257},
                   {'op':'add','args':[const(1)]}]
        deep = const(1)
        for _ in range(15): deep=op('abs',deep)
        invalid.append(deep)
        for expr in invalid:
            with self.subTest(expr=expr), self.assertRaises(ValueError):
                list(p.predictions(panel,[attack(expr)]))

    def test_work_limit_refuses_before_execution(self):
        with patch.object(p,'MAX_CELL_OPERATIONS',1), patch.object(p,'evaluate') as evaluate:
            with self.assertRaisesRegex(ValueError,'work limit'):
                list(p.predictions(self.panel(),[attack(col('operand'))]))
            evaluate.assert_not_called()

    def test_invalid_feature_width_and_names_fail_closed(self):
        panel=self.panel(); panel.cols['text'][0]='x'*4097
        with self.assertRaisesRegex(ValueError,'string limit'):
            list(p.predictions(panel,[attack(col('text'))]))
        with self.assertRaisesRegex(ValueError,'duplicate attack'):
            p.validate([attack(col('text')),attack(col('text'))],panel.cols,panel.target)


class FreezeTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root=Path(temp.name); self.data=self.root/'data';self.data.mkdir()
        quality={'target':'label','positive_label':1,
                 'splits':{s:s+'.csv' for s in ('train','eval','holdout')}}
        (self.data/'quality.json').write_text(json.dumps(quality))
        for split in quality['splits']:
            (self.data/(split+'.csv')).write_text('entity,date,operand,label\n'
                'A,2024-01-01,5,1\nA,2024-01-02,50,0\nA,2024-01-03,5,0\n')
        self.proposal=self.root/'proposal.json'
        self.write_proposal()

    def write_proposal(self):
        self.proposal.write_text(json.dumps({'version':execution.VERSION,
            'artifact_digest':battery.digest(execution.artifact_identity(self.data)),
            'programs':[attack(op('gt',join(op('number',col('operand'))),const(20)))]}))

    def test_no_labels_read_until_every_vector_is_frozen(self):
        with patch.object(battery,'read_labels', wraps=battery.read_labels) as read:
            frozen=execution.freeze(self.data,self.root/'scratch',self.proposal)
            read.assert_not_called()
            result=execution.score(self.data,self.root/'scratch')
            self.assertEqual(['eval','holdout'],[call.args[-1] for call in read.call_args_list])
        self.assertEqual(4,len(frozen['vectors']))
        self.assertTrue(result['requires_semantic_review'])
        self.assertFalse(result['release_authorized'])

    def test_changed_labels_do_not_change_predictions_but_invalidate_receipt(self):
        a=execution.freeze(self.data,self.root/'a',self.proposal)
        path=self.data/'eval.csv';path.write_text(path.read_text().replace(',5,1',',5,0'))
        self.write_proposal()
        b=execution.freeze(self.data,self.root/'b',self.proposal)
        self.assertEqual(a['predictions_sha256'],b['predictions_sha256'])
        self.assertNotEqual(a['artifact_digest'],b['artifact_digest'])
        with self.assertRaisesRegex(ValueError,'artifact changed'):
            execution.score(self.data,self.root/'a')

    def test_stale_proposal_and_mutated_non_data_bytes_refuse(self):
        (self.data/'README.md').write_text('changed documentation')
        with self.assertRaisesRegex(ValueError,'complete staged artifact'):
            execution.freeze(self.data,self.root/'a',self.proposal)
        self.write_proposal();execution.freeze(self.data,self.root/'b',self.proposal)
        (self.data/'README.md').write_text('changed again')
        with self.assertRaisesRegex(ValueError,'artifact changed'):
            execution.score(self.data,self.root/'b')

    def test_archive_code_and_receipt_tampering_refuse(self):
        execution.freeze(self.data,self.root/'a',self.proposal)
        with patch.object(execution,'code_identity',return_value={}):
            with self.assertRaisesRegex(ValueError,'implementation changed'):
                execution.score(self.data,self.root/'a')
        with (self.root/'a/predictions.zip').open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(ValueError,'evidence changed'):
            execution.score(self.data,self.root/'a')

    def test_output_cannot_overwrite_artifact_or_stale_scratch(self):
        with self.assertRaisesRegex(ValueError,'outside artifact'):
            execution.freeze(self.data,self.data/'audit',self.proposal)
        execution.freeze(self.data,self.root/'a',self.proposal)
        with self.assertRaises(FileExistsError):
            execution.freeze(self.data,self.root/'a',self.proposal)

    def test_json_duplicate_keys_nonfinite_and_target_reference_refuse(self):
        for content in ('{"a":1,"a":2}', '{"a":NaN}'):
            self.proposal.write_text(content)
            with self.assertRaises(ValueError):execution.bounded_json(self.proposal)
        self.write_proposal();data=json.loads(self.proposal.read_text())
        data['programs'][0]['expression']=col('label');self.proposal.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'target column'):
            execution.freeze(self.data,self.root/'a',self.proposal)


if __name__ == '__main__': unittest.main()
