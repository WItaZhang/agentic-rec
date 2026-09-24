from pathlib import Path

import pytest
import yaml

from src.utils import load_config


def test_checked_in_executable_yaml_configs_are_loadable():
    # Include real registered experiments; parameter-only templates are not CLI entries.
    for path in (Path(__file__).resolve().parents[1] / 'configs').glob('*.yaml'):
        raw = yaml.safe_load(path.read_text(encoding='utf-8'))
        if raw.get('experiment_name'):
            assert load_config(path) == raw


@pytest.mark.parametrize('stage', ['freeze_final_protocol', 'frozen_matrix_prepare',
                                  'final_policy_analysis', 'serving_resource_audit'])
def test_new_stage_config_is_dispatched_without_conventional_model_fields(tmp_path, stage):
    path = tmp_path / 'new_stage.yaml'
    path.write_text(yaml.safe_dump({'experiment_name': 'new_stage', 'stage': stage}))
    assert load_config(path)['stage'] == stage
