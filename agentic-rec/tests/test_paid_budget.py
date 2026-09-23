from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("filelock")

from src.paid_budget import BudgetExceeded, PaidBudget, usage_cost


def test_reservations_persist_across_restart_and_unknown_failure(tmp_path):
    path = tmp_path / "ledger.jsonl"
    first = PaidBudget(path, "a", 1, 0.5, 1)
    call = first.reserve(0.4, {})
    first.settle(call, None, "timeout")
    second = PaidBudget(path, "a", 1, 0.5, 1)
    with pytest.raises(BudgetExceeded):
        second.reserve(0.2, {})
    third = PaidBudget(path, "b", 1, 0.9, 1)
    third.reserve(0.5, {})
    with pytest.raises(BudgetExceeded):
        third.reserve(0.2, {})
    assert third.snapshot()["unknown_or_pending_calls"] == 2
    assert third.snapshot()["campaign_accounted_usd"] == pytest.approx(0.9)


def test_concurrent_reservations_cannot_overspend(tmp_path):
    def attempt(index):
        budget = PaidBudget(tmp_path / "ledger", str(index), 1, 1, 1)
        try:
            budget.reserve(0.3, {})
            return 1
        except BudgetExceeded:
            return 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(8))) == 3


def test_settlement_records_overage_and_cached_tokens(tmp_path):
    budget = PaidBudget(tmp_path / "ledger", "a", 1, 1, 1)
    call = budget.reserve(0.1, {})
    with pytest.raises(BudgetExceeded):
        budget.settle(call, 0.2, "completed")
    assert budget.snapshot()["campaign_actual_known_usd"] == 0.2
    with pytest.raises(ValueError):
        budget.settle(call, 0.2, "completed")
    assert usage_cost({"input_tokens": 1000, "output_tokens": 100,
                       "input_tokens_details": {"cached_tokens": 400}},
                      {"input_per_million_usd": 0.4, "cached_input_per_million_usd": 0.1,
                       "output_per_million_usd": 1.6}) == pytest.approx(0.00044)
