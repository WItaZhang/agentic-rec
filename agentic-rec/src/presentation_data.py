"""Verify saved candidates and transmitted inputs for a row-order comparison."""

import hashlib
import json
from copy import deepcopy

from .protocol import CandidateSnapshot
from .utils import digest, verified_run_config


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def pair_candidate_snapshots(left, right, matrices):
    """Compare exact candidate identities/order; never silently rewrite source hashes."""
    if set(left) != set(right):
        raise ValueError('Presentation candidate populations differ')
    identities, source_hashes, differences = {}, {'ordered': {}, 'shuffled': {}}, []
    for request in left:
        a, b = dict(left[request]), dict(right[request])
        scores_a, scores_b = a.pop('scores'), b.pop('scores')
        if a != b:
            raise ValueError('Presentation candidate identity, order, model or time changed')
        identities[request] = fingerprint(a)
        for name, record in [('ordered', left[request]), ('shuffled', right[request])]:
            source_hashes[name][request] = CandidateSnapshot(**record).content_hash
        if scores_a != scores_b:
            differences.append(max(abs(x-y) for x, y in zip(scores_a, scores_b, strict=True)))
    normalized = {}
    for name, rows in matrices.items():
        if {row['request_id'] for row in rows} != set(identities):
            raise ValueError('Presentation outcome/candidate population mismatch')
        normalized[name] = []
        for row in rows:
            request = row['request_id']
            if row['candidate_hash'] != source_hashes[name][request]:
                raise ValueError('Presentation source candidate hash changed')
            normalized[name].append({**row, 'source_candidate_hash': row['candidate_hash'],
                                     'candidate_hash': identities[request]})
    return normalized, {
        'requests': len(identities), 'candidate_identity_and_order_exact': True,
        'score_different_requests': len(differences), 'max_absolute_score_difference': max(differences, default=0),
        'comparison_candidate_hash_scope': 'request, ordered item IDs, model hash and prediction time; excludes unused numeric scores',
        'source_hashes_preserved_in': 'source_candidate_hash',
        'score_difference_acceptance': 'Requires independent exact transmitted-payload equivalence except row order and annotation; no numerical tolerance',
    }


def normalized_payload(body, presentation):
    """Retain every transmitted field except the two declared presentation changes."""
    result = deepcopy(body)
    messages = result['input']
    if len(messages) != 2 or [m['role'] for m in messages] != ['system', 'user']:
        raise ValueError('Unexpected presentation message structure')
    data = json.loads(messages[1]['content'])
    descriptions = {
        'ordered': 'descending frozen base-model score',
        'shuffled': 'shuffled rows; ascending candidate IDs encode descending frozen base-model score',
    }
    if data.pop('candidate_order') != descriptions[presentation]:
        raise ValueError('Unexpected candidate order annotation')
    ids = [row['id'] for row in data['candidates']]
    aliases = result['text']['format']['schema']['properties']['item_ids']['items']['enum']
    if len(ids) != len(set(ids)) or sorted(ids) != aliases or (presentation == 'ordered' and ids != aliases):
        raise ValueError('Candidate aliases or original order changed')
    data['candidates'] = sorted(data['candidates'], key=lambda row: row['id'])
    messages[1]['content'] = json.dumps(data, sort_keys=True)
    return fingerprint(result)


def verify_transmitted_inputs(root, paths, calls, plans):
    """Read actual submitted JSONL, including canonical shared calls, without any API."""
    paired, proofs = {}, {}
    for name, matrix in paths.items():
        config = verified_run_config(matrix)
        selected = [row for row in calls[name] if row['plan'] in plans]
        expected = {}
        for row in selected:
            identity = row['canonical_id']
            if identity in expected and expected[identity] != row['prompt_sha256']:
                raise ValueError('Shared presentation call changed input')
            expected[identity] = row['prompt_sha256']
        actual, hashes = {}, {}
        for location in config['collection_runs']:
            collection = verified_run_config(root / location)
            payload = root / collection['batch_run'] / 'batch_input.jsonl'
            hashes[str(payload.relative_to(root))] = digest(payload)
            with payload.open(encoding='utf-8') as stream:
                for line in stream:
                    row = json.loads(line)
                    identity = row['custom_id']
                    if identity not in expected:
                        continue
                    if identity in actual:
                        raise ValueError('Duplicate transmitted presentation call')
                    body = row['body']
                    common = {key: body[key] for key in ('model', 'input', 'text')}
                    if fingerprint(common) != expected[identity]:
                        raise ValueError('Transmitted presentation input changed')
                    actual[identity] = normalized_payload(body, name)
        if set(actual) != set(expected):
            raise ValueError('Missing transmitted presentation input')
        paired[name] = {(row['request_id'], row['plan']): actual[row['canonical_id']] for row in selected}
        proofs[name] = {'physical_payloads_verified': len(actual), 'payload_file_hashes': hashes}
    if paired['ordered'] != paired['shuffled']:
        raise ValueError('Transmitted evidence changed beyond candidate row order and annotation')
    return {'logical_pairs_verified': len(paired['ordered']), 'normalized_payloads_exact': True,
            'normalization': 'Only candidate row permutation and its declared candidate_order annotation',
            'sources': proofs}
