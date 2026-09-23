"""CPU sequence baseline training and inner-temporal validation, without test scoring."""

import time
from itertools import product

import torch
from torch import nn

from .baselines import fit_itemknn
from .data import load_amazon_reviews
from .feature import popularity_features
from .metrics import aggregate_requests, single_target_metrics
from .model import PopularityModel
from .protocol import hash_sample, replay_requests
from .replay import evaluate_views, make_candidates, model_fingerprint
from .sequence_model import CausalSequenceModel, SequenceRecommender
from .utils import digest, managed_run, utc_seconds, write_json


def training_examples(events, catalog, threshold, max_length, end):
    indices = {item: i + 1 for i, item in enumerate(catalog)}
    sequences, targets = [], []
    for request, target in replay_requests(events, [("train", end)], threshold):
        prefix = [indices[event.item] for event in request.history
                  if event.rating >= threshold and event.item in indices][-max_length:]
        if prefix:
            sequences.append(prefix + [0] * (max_length - len(prefix)))
            targets.append(indices[target.item_id])
    return torch.tensor(sequences, dtype=torch.long), torch.tensor(targets, dtype=torch.long)


def build_training(events, threshold, end, architecture, config):
    torch.manual_seed(config["seed"])
    popularity, _ = popularity_features(events, threshold)
    catalog = tuple(sorted(popularity))
    network = CausalSequenceModel(len(catalog), **architecture)
    x, y = training_examples(events, catalog, threshold, architecture["max_length"], end)
    optimizer = torch.optim.AdamW(network.parameters(), lr=config["learning_rate"],
                                 weight_decay=config["weight_decay"], betas=tuple(config["betas"]))
    return network, x, y, optimizer, catalog, tuple(popularity[item] for item in catalog)


def train_epoch(network, x, y, optimizer, config, epoch):
    if not len(y):
        raise ValueError("No nonempty-prefix training examples")
    network.train()
    generator = torch.Generator().manual_seed(config["seed"] + epoch)
    order = torch.randperm(len(y), generator=generator)
    losses = []
    for indices in order.split(config["batch_size"]):
        optimizer.zero_grad(set_to_none=True)
        loss = nn.functional.cross_entropy(network(x[indices]), y[indices],
                                           label_smoothing=config["label_smoothing"])
        if not torch.isfinite(loss):
            raise RuntimeError("Nonfinite sequence model loss")
        loss.backward()
        nn.utils.clip_grad_norm_(network.parameters(), config["gradient_clip"])
        optimizer.step()
        losses.append(float(loss.detach()) * len(indices))
    return sum(losses) / len(y)


def run_sequence(config, config_path, root):
    torch.set_num_threads(config["runtime"]["cpu_threads"])
    torch.set_num_interop_threads(config["runtime"]["interop_threads"])
    torch.use_deterministic_algorithms(True)
    with managed_run(config, config_path, root) as (run_dir, manifest):
        raw = root / config["data"]["raw_path"]
        if digest(raw) != config["data"]["sha256"]:
            raise ValueError("Raw data checksum mismatch")
        if config["evaluation"]["partitions"] != ["policy_train", "validation"]:
            raise ValueError("Sequence development cannot score test labels")
        events, audit = load_amazon_reviews(raw)
        threshold = config["protocol"]["positive_rating"]
        ends = [(name, utc_seconds(config["data"][key]) * 1000) for name, key in (
            ("base_train", "base_train_end"), ("policy_train", "policy_train_end"),
            ("validation", "validation_end"), ("test", "test_end"))]
        inner_end = utc_seconds(config["data"]["inner_train_end"]) * 1000
        train_end = ends[0][1]
        if inner_end >= train_end:
            raise ValueError("Invalid inner temporal split")
        train = [event for event in events if event.timestamp < train_end]
        inner_train = [event for event in train if event.timestamp < inner_end]
        pairs = list(replay_requests(train, [("inner_train", inner_end), ("inner_validation", train_end)], threshold))
        inner_views = [view for view, _ in pairs if view.partition == "inner_validation"]
        inner_sample, sample_audit = hash_sample(inner_views, config["train"]["selection_max_users"], config["seed"])
        targets = {label.request_id: label.item_id for _, label in pairs}
        grid, best_key, selected = [], None, None
        for dimension, layers in product(config["model"]["dimensions"], config["model"]["layers"]):
            architecture = {"dimension": dimension, "layers": layers,
                            "heads": config["model"]["heads"], "dropout": config["model"]["dropout"],
                            "max_length": config["model"]["max_length"],
                            "feedforward_multiplier": config["model"]["feedforward_multiplier"],
                            "embedding_std": config["model"]["embedding_std"]}
            network, x, y, optimizer, catalog, pop = build_training(inner_train, threshold, inner_end,
                                                                  architecture, config["train"])
            print(f"Sequence inner fit: {architecture}, examples={len(y)}", flush=True)
            for epoch in range(1, max(config["model"]["epochs"]) + 1):
                loss = train_epoch(network, x, y, optimizer, config["train"], epoch)
                if epoch in config["model"]["epochs"]:
                    model = SequenceRecommender(network, catalog, pop)
                    quality = aggregate_requests(evaluate_views(inner_sample, targets, model,
                        config["model"]["candidate_count"], threshold, config["evaluation"]["k"]))
                    record = {"architecture": architecture, "epoch": epoch, "loss": loss, "quality": quality}
                    grid.append(record)
                    print(f"Inner validation epoch={epoch} dim={dimension}: {quality['user_macro']}", flush=True)
                    key = (quality["user_macro"]["ndcg"], -dimension, -layers, -epoch)
                    if best_key is None or key > best_key:
                        best_key, selected = key, {"architecture": architecture, "epochs": epoch}
        write_json(run_dir / "inner_validation_grid.json", grid)
        write_json(run_dir / "selection_frozen.json", {"selected": selected, "sample": sample_audit,
                                                       "scope": "base_train_internal_only", "test_scored": False})
        network, x, y, optimizer, catalog, pop = build_training(train, threshold, train_end,
                                                              selected["architecture"], config["train"])
        losses = []
        for epoch in range(1, selected["epochs"] + 1):
            losses.append(train_epoch(network, x, y, optimizer, config["train"], epoch))
        sequence = SequenceRecommender(network, catalog, pop)
        torch.save(network.state_dict(), run_dir / "sequence.pt")
        write_json(run_dir / "model.json", {"catalog": catalog, "popularity": pop,
                                           "selected": selected, "training_examples": len(y),
                                           "losses": losses, "base_train_end": train_end})
        knn, _, _ = fit_itemknn(train, threshold, **config["comparison"]["itemknn"])
        popularity = PopularityModel(tuple(sorted(catalog, key=lambda item: (-pop[catalog.index(item)], item))))
        models = {"popularity": popularity, "itemknn": knn, "causal_sequence": sequence}
        pairs = list(replay_requests(events, ends, threshold))
        targets = {label.request_id: label.item_id for _, label in pairs}
        metrics = {}
        for partition in config["evaluation"]["partitions"]:
            views = [view for view, _ in pairs if view.partition == partition]
            metrics[partition] = {}
            for name, model in models.items():
                start = time.perf_counter()
                outcomes = {count: [] for count in config["evaluation"]["candidate_counts"]}
                catalog_set, fingerprint = set(model.ranked_items), model_fingerprint(model)
                for request in views:
                    snapshot = make_candidates(request, model, max(outcomes), threshold, fingerprint)
                    target = targets[request.request_id]
                    for count in outcomes:
                        ranking = list(snapshot.item_ids[:config["evaluation"]["k"]])
                        outcomes[count].append({"user_id": request.user_id, "history_count": len(request.history),
                            "cold_item": target not in catalog_set,
                            **single_target_metrics(ranking, target, snapshot.item_ids[:count], config["evaluation"]["k"])})
                metrics[partition][name] = {str(count): aggregate_requests(rows) for count, rows in outcomes.items()}
                metrics[partition][name]["wall_seconds"] = time.perf_counter() - start
                print(f"{partition}/{name}: {metrics[partition][name]}", flush=True)
        manifest.update(raw_sha256=digest(raw), input_audit=audit, test_scored=False,
                        model_hashes={name: model_fingerprint(model) for name, model in models.items()},
                        paid_api_usd=0, llm_calls=0, device="cpu", torch_version=torch.__version__)
        write_json(run_dir / "metrics.json", metrics)
