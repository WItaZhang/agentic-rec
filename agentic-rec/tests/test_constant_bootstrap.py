import numpy as np
import pytest

from src.metrics import paired_bootstrap


@pytest.mark.parametrize('value', [0., .1, -.125])
def test_constant_paired_effect_has_exact_resampling_interval(value):
    left = [value] * 103
    expected = float(np.mean(left))
    a = paired_bootstrap(left, [0.] * 103, 100, 42, .95)
    b = paired_bootstrap(left, [0.] * 103, 100, 97, .95)
    assert a['difference'] == a['ci_low'] == a['ci_high'] == expected
    assert a == b
