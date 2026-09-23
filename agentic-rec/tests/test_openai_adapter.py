from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("filelock")

from src.openai_adapter import OpenAIBackend
from src.paid_budget import PaidBudget


def test_count_failure_does_not_generate_and_timeout_is_reserved(tmp_path):
    import yaml

    config = yaml.safe_load(Path("configs/amazon_llm_smoke.yaml").read_text())["llm"]
    budget = PaidBudget(tmp_path / "ledger", "test", 1, 1, 1)
    generated = []

    def bad_count(**kwargs):
        raise RuntimeError("SECRET in exception must not be logged")

    def bad_generate(**kwargs):
        generated.append(1)
        raise TimeoutError("SECRET")

    responses = SimpleNamespace(input_tokens=SimpleNamespace(count=bad_count), create=bad_generate)
    backend = OpenAIBackend(config, tmp_path, budget, SimpleNamespace(responses=responses))
    result = backend.complete([], {}, {})
    assert result["status"] == "count_error"
    assert not generated and budget.snapshot()["campaign_accounted_usd"] == 0
    assert "SECRET" not in str(result)
    responses.input_tokens.count = lambda **kwargs: SimpleNamespace(input_tokens=100)
    result = backend.complete([], {}, {})
    assert result["status"] == "generation_error" and len(generated) == 1
    assert result["usage"] is None and "SECRET" not in str(result)
    assert budget.snapshot()["campaign_accounted_usd"] > 0
