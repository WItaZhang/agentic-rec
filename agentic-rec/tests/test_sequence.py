import pytest

torch = pytest.importorskip("torch")

from src.data import ReviewEvent  # noqa: E402
from src.sequence_model import CausalSequenceModel  # noqa: E402
from src.sequence_trainer import training_examples  # noqa: E402


def test_sequence_attention_cannot_see_later_tokens():
    torch.manual_seed(42)
    model = CausalSequenceModel(5, 4, 8, 2, 1, 0, 4, .02).eval()
    with torch.inference_mode():
        before = model.encode(torch.tensor([[1, 2, 3, 4]]))
        after = model.encode(torch.tensor([[1, 2, 5, 4]]))
    assert torch.allclose(before[:, :2], after[:, :2], atol=1e-7)
    assert torch.isfinite(model(torch.tensor([[1, 2, 0, 0]]))).all()


def test_training_examples_keep_current_and_tied_targets_out_of_prefix():
    events = [ReviewEvent(1, "u", "a", 5, "e1"), ReviewEvent(2, "u", "b", 5, "e2"),
              ReviewEvent(2, "u", "c", 5, "e3"), ReviewEvent(3, "u", "d", 1, "e4")]
    x, y = training_examples(events, ("a", "b", "c", "d"), 4, 3, 4)
    assert x.tolist() == [[1, 0, 0], [1, 0, 0]]
    assert y.tolist() == [2, 3]
