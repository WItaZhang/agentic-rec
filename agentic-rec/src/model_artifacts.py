"""Load immutable, fingerprint-verified recommender artifacts without refitting."""

import json

from scipy import sparse

from .model import ItemKNNModel, PopularityModel
from .replay import model_fingerprint


def load_frozen_retriever(root, config):
    name = config["name"]
    if name not in ("itemknn", "causal_sequence", "popularity"):
        raise ValueError("Unsupported frozen retriever")
    directory = root / config["artifact_path"]
    weight_file = {"itemknn": "itemknn.npz", "causal_sequence": "sequence.pt", "popularity": "model.json"}[name]
    if not directory.exists() and config.get("artifact_fallback_path"):
        directory = root / config["artifact_fallback_path"]
    if not directory.exists() and config.get("artifact_search_root"):
        # Timestamped reproductions resolve by the exact model hash, never by quality.
        for candidate in sorted((root / config["artifact_search_root"]).glob("*/manifest.json")):
            record = json.loads(candidate.read_text())
            if record.get("status") == "completed" and record.get("model_hashes", {}).get(name) == config["model_hash"]:
                if (candidate.parent / weight_file).exists():
                    directory = candidate.parent
                    break
    metadata = json.loads((directory / "model.json").read_text())
    if name == "popularity":
        ordered = sorted(zip(metadata["catalog"], metadata["popularity"], strict=True), key=lambda pair: (-pair[1], pair[0]))
        result = PopularityModel(tuple(item for item, _ in ordered))
    elif name == "itemknn":
        result = ItemKNNModel(tuple(metadata["catalog"]), sparse.load_npz(directory / weight_file),
                              tuple(metadata["popularity"]))
    else:
        import torch

        from .sequence_model import CausalSequenceModel, SequenceRecommender

        torch.set_num_threads(config["cpu_threads"])
        torch.use_deterministic_algorithms(True)
        network = CausalSequenceModel(len(metadata["catalog"]), **metadata["selected"]["architecture"])
        network.load_state_dict(torch.load(directory / weight_file, map_location="cpu", weights_only=True))
        result = SequenceRecommender(network, metadata["catalog"], metadata["popularity"])
    if model_fingerprint(result) != config["model_hash"]:
        raise ValueError("Frozen model fingerprint mismatch")
    return result
