"""Explicit synthetic evidence for gate unit tests; never used for real dataset acceptance."""
def research_contract(columns, target):
    return {'use': 'retrospective_research', 'access': 'isolated_rows',
            'feature_evidence': {c: {'source': 'synthetic test fixture', 'availability': 'constructed input',
                                     'status': 'assumed'} for c in columns if c != target},
            'vintage': {'kind': 'current_snapshot', 'evidence': 'synthetic test fixture'},
            'selection': {'kind': 'prediction_time', 'evidence': 'synthetic test fixture'},
            'training_label_timing': 'unverified',
            'limitations': ['Synthetic software fixture, not empirical data or a forecasting claim'],
            'cross_row_audit': {'probes': [], 'rationale': 'Independent synthetic fixture rows',
                                'auxiliary_files_review': 'Only the declared test inputs'}}
