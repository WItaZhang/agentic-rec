"""Paired conventional-model comparison on identical sampled validation requests."""

import json

import yaml

from .data import load_amazon_reviews
from .llm_experiment import choose_views
from .metrics import aggregate_requests, paired_bootstrap, single_target_metrics
from .protocol import replay_requests
from .utils import digest, managed_run, write_json


def run_baseline_comparison(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        settings = config["comparison"]
        sources, candidates, source_config = {}, {}, None
        for name, location in settings["prepared_runs"].items():
            directory = root / location
            state = json.loads((directory / "manifest.json").read_text())
            if state["status"] != "completed" or digest(directory / "candidates.json") != state["candidates_sha256"]:
                raise ValueError("Candidate source changed or is incomplete")
            original = yaml.safe_load((directory / "config.yaml").read_text(encoding="utf-8"))
            if original["evaluation"]["partition"] != "validation" or original["sampling"]["mode"] != "uniform_users":
                raise ValueError("This comparison requires population validation, never test")
            if source_config is not None and any(original[key] != source_config[key] for key in ("data", "protocol", "sampling", "seed")):
                raise ValueError("Conventional baselines require identical request sampling and time visibility")
            source_config = original
            candidates[name] = json.loads((directory / "candidates.json").read_text())
            sources[name] = {"path": location, "config_sha256": state["config_sha256"],
                             "candidate_sha256": state["candidates_sha256"], "retriever": original["retriever"]}
        names = list(candidates)
        ids = sorted(candidates[names[0]])
        if any(set(candidates[name]) != set(ids) for name in names):
            raise ValueError("Candidate snapshots do not cover identical users")
        # Rankings are already materialized; labels only enter below this point.
        raw = root / source_config["data"]["raw_path"]
        if digest(raw) != source_config["data"]["sha256"]:
            raise ValueError("Raw data changed")
        events, _ = load_amazon_reviews(raw)
        views, _, ends = choose_views(events, source_config)
        views = {v.request_id: v for v in views}
        targets = {label.request_id: label.item_id for _, label in replay_requests(
            events, ends, source_config["protocol"]["positive_rating"])}
        outcomes, metrics = {}, {}
        for name in names:
            outcomes[name] = [{"request_id": q, "user_id": views[q].user_id,
                "history_count": len(views[q].history), **single_target_metrics(
                    candidates[name][q]["item_ids"][:settings["k"]], targets[q],
                    candidates[name][q]["item_ids"], settings["k"])} for q in ids]
            metrics[name] = aggregate_requests(outcomes[name])
        comparisons = {}
        for left, right in settings["pairs"]:
            comparisons[f"{left}_minus_{right}"] = {key: paired_bootstrap(
                [r[key] for r in outcomes[left]], [r[key] for r in outcomes[right]],
                settings["bootstrap_repetitions"], config["seed"], settings["confidence"])
                for key in ("ndcg", "hr", "candidate_recall")}
        write_json(run_dir / "outcomes.json", outcomes)
        write_json(run_dir / "metrics.json", {"models": metrics, "paired_comparisons": comparisons,
            "scope": "same sampled validation users; each base model has its own retrieval candidates",
            "within_retriever_llm_comparison": "Use that model's immutable candidate pool in its separate evidence matrix"})
        manifest.update(test_scored=False, sources=sources, paid_api_usd=0)
        print(json.dumps({"models": metrics, "paired": comparisons}), flush=True)
