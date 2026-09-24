import copy
import json

import pytest

from src.frozen_protocol import verify_final_config
from src.policy_inference import decide_frozen_policies
from src.utils import digest


def frozen_fixture(root):
    (root / 'prompt.txt').write_text('frozen instructions')
    selection = root / 'routing'
    selection.mkdir()
    (selection / 'selection_frozen.json').write_text('{}')
    configuration = {key: {} for key in ('protocol', 'data', 'retriever', 'llm', 'sampling',
                                        'runtime', 'budget', 'preparation')}
    configuration.update(evidence={'prompt_path': 'prompt.txt'}, seed=42,
        evaluation={'partition': 'test'}, final_test_freeze='freeze.json')
    record = {'test_config': configuration, 'routing_run': 'routing',
        'prompt_sha256': digest(root / 'prompt.txt'),
        'selection_artifact_hashes': {'selection_frozen.json': digest(selection / 'selection_frozen.json')}}
    (root / 'freeze.json').write_text(json.dumps(record))
    (root / 'manifest.json').write_text(json.dumps({'status': 'completed', 'test_scored': False,
                                                    'freeze_sha256': digest(root / 'freeze.json')}))
    return configuration


def test_final_inputs_and_output_sharing_cannot_change_after_freeze(tmp_path):
    config = frozen_fixture(tmp_path)
    verify_final_config(config, tmp_path)
    for key in ('evidence', 'sampling', 'retriever', 'llm', 'preparation', 'budget', 'evaluation'):
        altered = copy.deepcopy(config)
        altered[key]['changed'] = True
        with pytest.raises(ValueError, match='configuration changed'):
            verify_final_config(altered, tmp_path)
    (tmp_path / 'prompt.txt').write_text('changed after observing results')
    with pytest.raises(ValueError, match='prompt changed'):
        verify_final_config(config, tmp_path)


def test_artifact_mutation_or_unfinished_freeze_is_rejected(tmp_path):
    config = frozen_fixture(tmp_path)
    (tmp_path / 'routing/selection_frozen.json').write_text('{"changed": true}')
    with pytest.raises(ValueError, match='artifact changed'):
        verify_final_config(config, tmp_path)
    (tmp_path / 'freeze.json').write_text('{}')
    with pytest.raises(ValueError, match='altered'):
        verify_final_config(config, tmp_path)


def test_frozen_policy_decisions_need_no_outcomes_or_targets(tmp_path):
    selection = {'plans': ['R0', 'R1', 'R4'], 'chosen': {
        'rule_0.25': {'policy': {'kind': 'rule', 'rule': 'full_if_history'}}}}
    path = tmp_path / 'selection_frozen.json'
    path.write_text(json.dumps(selection))
    result = decide_frozen_policies(tmp_path, '.', ['q1', 'q2'],
        [{'has_history': 0}, {'has_history': 1}], {'selection_frozen.json': digest(path)}, 1)
    assert result['actions']['rule_0.25'] == ['R0', 'R4']
    assert result['actions']['fixed_R1'] == ['R1', 'R1']
    assert result['label_access'] is False
