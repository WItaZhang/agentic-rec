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


def test_restored_sequence_checkpoint_keeps_scores_and_rejects_changed_weights(tmp_path):
    import json

    import numpy as np

    from src.model_artifacts import load_frozen_retriever
    from src.sequence_model import SequenceRecommender

    architecture = dict(max_length=4, dimension=8, heads=2, layers=1, dropout=0,
                        feedforward_multiplier=4, embedding_std=.02)
    network = CausalSequenceModel(3, **architecture).eval()
    original = SequenceRecommender(network, ('a', 'b', 'c'), (3, 2, 1))
    (tmp_path / 'model.json').write_text(json.dumps({'catalog': original.catalog,
        'popularity': original.popularity, 'selected': {'architecture': architecture}}))
    torch.save(network.state_dict(), tmp_path / 'sequence.pt')
    config = {'name': 'causal_sequence', 'artifact_path': '.', 'cpu_threads': 1,
              'model_hash': original.checkpoint_hash}
    restored = load_frozen_retriever(tmp_path, config)
    history = [ReviewEvent(1, 'u', 'a', 5, 'e')]
    assert np.allclose(original.score_history(history, 4), restored.score_history(history, 4))
    assert restored.score_history([], 4).tolist() == [3, 2, 1]
    with torch.no_grad():
        network.items.weight[1, 0] += 1
    torch.save(network.state_dict(), tmp_path / 'sequence.pt')
    with pytest.raises(ValueError, match='fingerprint'):
        load_frozen_retriever(tmp_path, config)
