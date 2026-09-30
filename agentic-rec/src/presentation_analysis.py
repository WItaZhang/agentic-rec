"""Paired row-presentation sensitivity with unchanged requests and candidate pools."""

import json

from .evidence_analysis import analyze_matrix, draw_cost_quality, validate_table
from .utils import digest, managed_run, verified_run_config, write_json


def join_presentations(ordered_rows, ordered_calls, shuffled_rows, shuffled_calls, plans):
    def select(rows, calls):
        rows = [r for r in rows if r['plan'] in ['R0', *plans]]
        calls = [r for r in calls if r['plan'] in plans]
        table, _ = validate_table(rows, calls, ['R0', *plans])
        return rows, calls, table

    left, left_calls, a = select(ordered_rows, ordered_calls)
    right, right_calls, b = select(shuffled_rows, shuffled_calls)
    if set(a) != set(b):
        raise ValueError('Presentation control must retain the identical request population')
    keys = ('user_id', 'candidate_hash', 'ranking', 'ndcg', 'hr', 'candidate_recall', 'history_count', 'cold_item')
    for q in a:
        if any(a[q]['R0'][key] != b[q]['R0'][key] for key in keys):
            raise ValueError('Presentation control changed base ranking, targets or request history')
    rows = [r for r in left if r['plan'] == 'R0']
    calls = []
    for prefix, outcomes, attempts in [('ordered', left, left_calls), ('shuffled', right, right_calls)]:
        rows.extend({**r, 'plan': f"{prefix}_{r['plan']}"} for r in outcomes if r['plan'] != 'R0')
        calls.extend({**r, 'plan': f"{prefix}_{r['plan']}"} for r in attempts)
    validate_table(rows, calls, ['R0', *[f'{prefix}_{plan}' for prefix in ('ordered', 'shuffled') for plan in plans]])
    return rows, calls


def run_presentation_analysis(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        paths = {key: root / config['sources'][key] for key in ('ordered', 'shuffled')}
        originals, matrices, calls = {}, {}, {}
        for key, path in paths.items():
            state = json.loads((path / 'manifest.json').read_text())
            if state['status'] != 'completed' or state.get('test_scored') or state.get('stage_status') != 'evaluated':
                raise ValueError('Presentation analysis requires complete development matrices')
            originals[key] = verified_run_config(root / state['prepared_run'])
            if originals[key]['evaluation']['partition'] != 'validation':
                raise ValueError('Presentation analysis is validation-only')
            matrices[key] = json.loads((path / 'outcomes.json').read_text())
            calls[key] = [json.loads(line) for line in (path / 'calls.jsonl').read_text().splitlines()]
        for key in ('protocol', 'data', 'retriever', 'llm', 'sampling', 'seed', 'runtime'):
            if originals['ordered'][key] != originals['shuffled'][key]:
                raise ValueError(f'Presentation comparison changed inference setting: {key}')
        left, right = [dict(originals[key]['evidence']) for key in ('ordered', 'shuffled')]
        if left.pop('candidate_presentation', 'base_score') != 'base_score' or right.pop('candidate_presentation') != 'shuffled_rows':
            raise ValueError('Expected original base order versus shuffled rows')
        right.pop('presentation_seed')
        left.pop('plans')
        right.pop('plans')
        if left != right:
            raise ValueError('Evidence content changed across presentation conditions')
        rows, attempts = join_presentations(matrices['ordered'], calls['ordered'], matrices['shuffled'],
                                            calls['shuffled'], config['sources']['plans'])
        result = analyze_matrix(rows, attempts, config['analysis'])
        write_json(run_dir / 'outcomes.json', rows)
        (run_dir / 'calls.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in attempts), encoding='utf-8')
        write_json(run_dir / 'analysis.json', result)
        draw_cost_quality(result, run_dir)
        manifest.update(test_scored=False, paid_api_usd=0, stage_status='presentation_analyzed',
            presentation_scope=('Shared target-independent row permutation; alias IDs retain base-rank information. '
                'Order annotation also changes. Dates/output realizations remain possible confounders; exploratory sensitivity.'),
            source_hashes={key: {name: digest(path/name) for name in ('outcomes.json', 'calls.jsonl')}
                           for key, path in paths.items()})
        print(json.dumps(result['comparisons']), flush=True)
