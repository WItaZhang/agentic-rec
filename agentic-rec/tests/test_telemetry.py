import pytest

from src.telemetry import TokenBudget


def test_budget_reserves_full_output_and_charges_failures():
    budget = TokenBudget(100, 3)
    assert budget.reserve(50, 30)
    assert not budget.reserve(1, 1)  # sequential backend cannot double reserve
    budget.settle(50, 10)
    assert budget.used_tokens == 60 and budget.calls == 1
    assert not budget.reserve(30, 20)
    assert budget.reserve(20, 20)
    budget.settle(20, None)
    assert budget.used_tokens == 100 and budget.usage_unknown
    assert not budget.reserve(0, 0)


def test_call_limit_counts_empty_or_failed_responses():
    budget = TokenBudget(100, 1)
    assert budget.reserve(10, 10)
    budget.settle(10, 0)
    assert not budget.reserve(10, 10)
    with pytest.raises(ValueError):
        budget.settle(0, 0)
