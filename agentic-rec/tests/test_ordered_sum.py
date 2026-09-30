from src.metrics import sum_in_order


def test_archived_cost_reduction_preserves_rounding_and_numeric_types():
    assert sum_in_order([0.1, 0.2, 0.3]) == 0.6000000000000001
    assert sum_in_order([1e16, 1.0, -1e16]) == 0.0
    assert type(sum_in_order([])) is int
    assert type(sum_in_order([0, 0])) is int
    assert type(sum_in_order([0.0, 0.0])) is float
