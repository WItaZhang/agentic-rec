"""Paired sensitivity of evidence effects to the frozen candidate generator."""

import gzip
import json

from .evidence_analysis import validate_table
from .metrics import paired_bootstrap
from .utils import digest, managed_run, write_json


def load_archive(path, plans):
    manifest = json.loads((path / 'archive_manifest.json').read_text())
    if manifest['status'] != 'completed' or manifest['kind'] != 'evidence' or manifest['test_scored']:
        raise ValueError('Retriever sensitivity requires complete development evidence archives')
    for name, expected in manifest['files'].items():
        if '/' in name or '\\' in name or digest(path / name) != expected:
            raise ValueError('Archived evidence changed')
    rows = json.loads(gzip.decompress((path / 'outcomes.json.gz').read_bytes()))
    calls = [json.loads(line) for line in gzip.decompress((path / 'calls.jsonl.gz').read_bytes()).decode().splitlines()]
    return validate_table(rows, calls, plans)[0]


def compare_retrievers(first, second, settings):
    if not first or set(first) != set(second):
        raise ValueError('Both retrievers must retain the same complete request population')
    ids = sorted(first, key=lambda q: first[q]['R0']['user_id'])
    if len({first[q]['R0']['user_id'] for q in ids}) != len(ids):
        raise ValueError('This registered comparison requires one request per user')
    for q in ids:
        if any(first[q]['R0'][key] != second[q]['R0'][key]
               for key in ('user_id', 'history_count', 'cold_item')):
            raise ValueError('Request identity, history or catalog visibility changed')
        if set(first[q]) != set(settings['plans']) or set(second[q]) != set(settings['plans']):
            raise ValueError('Incomplete evidence comparison')

    def paired(a, b):
        return paired_bootstrap(a, b, settings['bootstrap_repetitions'], settings['seed'], settings['confidence'])

    def comparison(selected):
        result = {'users': len(selected), 'base_second_minus_first': {}, 'evidence_effect_interactions': {}}
        for metric in ('ndcg', 'hr', 'candidate_recall'):
            result['base_second_minus_first'][metric] = paired(
                [second[q]['R0'][metric] for q in selected], [first[q]['R0'][metric] for q in selected])
        for plan in settings['plans']:
            if plan == 'R0':
                continue
            result['evidence_effect_interactions'][plan] = {
                metric: paired([second[q][plan][metric] - second[q]['R0'][metric] for q in selected],
                               [first[q][plan][metric] - first[q]['R0'][metric] for q in selected])
                for metric in ('ndcg', 'hr')}
        if len(selected) < settings['minimum_group_users_for_interval']:
            for row in [*result['base_second_minus_first'].values(),
                        *[v for p in result['evidence_effect_interactions'].values() for v in p.values()]]:
                row.update(ci_low=None, ci_high=None, interval_status='descriptive_small_group')
        return result

    groups = {}
    for name, lower, upper in settings['history_groups']:
        selected = [q for q in ids if lower <= first[q]['R0']['history_count'] < upper]
        groups[name] = comparison(selected) if selected else {'users': 0}
    return {'overall': comparison(ids), 'history_groups': groups,
            'identical_candidate_snapshots': sum(first[q]['R0']['candidate_hash'] == second[q]['R0']['candidate_hash'] for q in ids),
            'snapshot_identity_scope': 'The fingerprint includes item IDs/order, scores, model hash and prediction time; '
                                       'a different fingerprint does not prove different item membership.',
            'interaction_definition': '(action minus base under second retriever) minus (action minus base under first retriever)',
            'inference': 'Exploratory paired sensitivity; nominal intervals. Each within-retriever contrast fixes candidates. '
                         'Cross-retriever interactions include changes in candidate composition and base order; '
                         'they do not isolate stronger embeddings or establish a routing improvement.'}


def run_retriever_robustness(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        settings = config['analysis']
        paths = {name: root / path for name, path in config['archives'].items()}
        first, second = [load_archive(paths[name], settings['plans']) for name in ('first', 'second')]
        result = compare_retrievers(first, second, settings)
        write_json(run_dir / 'analysis.json', result)
        manifest.update(test_scored=False, paid_api_usd=0, llm_calls=0,
                        archive_hashes={name: digest(path / 'archive_manifest.json') for name, path in paths.items()})
        print(json.dumps(result['overall']), flush=True)
