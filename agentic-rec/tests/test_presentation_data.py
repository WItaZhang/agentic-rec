import json
from copy import deepcopy

import pytest
import yaml

from src.presentation_data import (
    fingerprint,
    normalized_payload,
    pair_candidate_snapshots,
    verify_transmitted_inputs,
)
from src.protocol import CandidateSnapshot
from src.utils import digest


def payload_pair():
    data = {'candidate_order': 'descending frozen base-model score',
            'candidates': [{'id': 'C001', 'title': 'a'}, {'id': 'C002', 'title': 'b'}],
            'history': [{'title': 'prior', 'rating': 4}], 'top_k': 1}
    body = {'model': 'pinned', 'input': [{'role': 'system', 'content': 'rank'},
                                      {'role': 'user', 'content': json.dumps(data)}],
            'text': {'format': {'schema': {'properties': {'item_ids': {'items': {'enum': ['C001', 'C002']}}}}}},
            'temperature': 0, 'max_output_tokens': 256, 'store': False}
    data['candidate_order'] = 'shuffled rows; ascending candidate IDs encode descending frozen base-model score'
    data['candidates'].reverse()
    shuffled = deepcopy(body)
    shuffled['input'][1]['content'] = json.dumps(data)
    return body, shuffled


def test_payload_equivalence_preserves_content_options_and_aliases():
    ordered, shuffled = payload_pair()
    reference = normalized_payload(ordered, 'ordered')
    assert normalized_payload(shuffled, 'shuffled') == reference
    for field in ('candidates', 'history'):
        changed = deepcopy(shuffled)
        data = json.loads(changed['input'][1]['content'])
        data[field][0]['title'] = 'changed'
        changed['input'][1]['content'] = json.dumps(data)
        assert normalized_payload(changed, 'shuffled') != reference
    changed = deepcopy(shuffled)
    changed['max_output_tokens'] = 512
    assert normalized_payload(changed, 'shuffled') != reference
    changed = deepcopy(shuffled)
    data = json.loads(changed['input'][1]['content'])
    data['candidates'][0]['id'] = data['candidates'][1]['id']
    changed['input'][1]['content'] = json.dumps(data)
    with pytest.raises(ValueError, match='aliases'):
        normalized_payload(changed, 'shuffled')
    with pytest.raises(ValueError, match='annotation'):
        normalized_payload(ordered, 'shuffled')


def test_candidate_proof_preserves_source_hash_and_exact_identity():
    left = {'q': {'request_id': 'q', 'item_ids': ['a', 'b'], 'scores': [0.2, 0.1],
                  'model_hash': 'frozen', 'prediction_time': 7}}
    right = deepcopy(left)
    right['q']['scores'][0] += 1e-16
    matrices = {name: [{'request_id': 'q', 'candidate_hash': CandidateSnapshot(**record['q']).content_hash}]
                for name, record in [('ordered', left), ('shuffled', right)]}
    result, proof = pair_candidate_snapshots(left, right, matrices)
    assert proof['score_different_requests'] == 1
    assert result['ordered'][0]['candidate_hash'] == result['shuffled'][0]['candidate_hash']
    assert result['ordered'][0]['source_candidate_hash'] != result['shuffled'][0]['source_candidate_hash']
    assert 'source_candidate_hash' not in matrices['ordered'][0]
    for field, value in [('item_ids', ['b', 'a']), ('model_hash', 'other'), ('prediction_time', 8)]:
        changed = deepcopy(right)
        changed['q'][field] = value
        with pytest.raises(ValueError, match='identity, order, model or time'):
            pair_candidate_snapshots(left, changed, matrices)
    changed = deepcopy(matrices)
    changed['shuffled'][0]['candidate_hash'] = 'forged'
    with pytest.raises(ValueError, match='source candidate hash'):
        pair_candidate_snapshots(left, right, changed)


def save_config(directory, config):
    directory.mkdir()
    (directory / 'config.yaml').write_text(yaml.safe_dump(config))
    (directory / 'manifest.json').write_text(json.dumps({'config_sha256': digest(directory / 'config.yaml')}))


def test_transmitted_pairing_resolves_shared_inputs_and_rejects_tampering(tmp_path):
    paths, calls = {}, {}
    for name, body in zip(('ordered', 'shuffled'), payload_pair(), strict=True):
        paths[name] = tmp_path / name
        save_config(paths[name], {'collection_runs': [name + '_collect']})
        save_config(tmp_path / (name + '_collect'), {'batch_run': name + '_submit'})
        submission = tmp_path / (name + '_submit')
        submission.mkdir()
        canonical = 'q_R3' if name == 'ordered' else 'q_R4'
        (submission / 'batch_input.jsonl').write_text(json.dumps({'custom_id': canonical, 'body': body}) + '\n')
        calls[name] = [{'request_id': 'q', 'plan': 'R4', 'canonical_id': canonical,
                        'prompt_sha256': fingerprint({key: body[key] for key in ('model', 'input', 'text')})}]
    proof = verify_transmitted_inputs(tmp_path, paths, calls, ['R4'])
    assert proof['normalized_payloads_exact'] and proof['logical_pairs_verified'] == 1
    payload = tmp_path / 'shuffled_submit' / 'batch_input.jsonl'
    row = json.loads(payload.read_text())
    row['body']['input'][0]['content'] = 'changed instruction'
    payload.write_text(json.dumps(row) + '\n')
    with pytest.raises(ValueError, match='Transmitted presentation input changed'):
        verify_transmitted_inputs(tmp_path, paths, calls, ['R4'])
    calls['shuffled'][0]['prompt_sha256'] = fingerprint({key: row['body'][key] for key in ('model', 'input', 'text')})
    with pytest.raises(ValueError, match='beyond candidate row order'):
        verify_transmitted_inputs(tmp_path, paths, calls, ['R4'])
