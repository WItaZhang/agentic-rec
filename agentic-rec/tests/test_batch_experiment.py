import pytest

pytest.importorskip("filelock")

from src.batch_experiment import parse_batch_line


def test_batch_usage_includes_nonvisible_tokens_and_errors_are_unknown():
    row = parse_batch_line({"custom_id": "q_R1", "response": {"status_code": 200,
        "body": {"status": "completed", "usage": {"input_tokens": 100, "output_tokens": 20},
        "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"item_ids":[]}'},
                                                       {"type": "refusal", "refusal": "ignored"}]}]}}})
    assert row["usage"]["output_tokens"] == 20
    assert row["text"] == '{"item_ids":[]}'
    error = parse_batch_line({"custom_id": "q_R2", "response": None, "error": {"code": "batch_expired"}})
    assert error["usage"] is None and error["status"] == "batch_error"
