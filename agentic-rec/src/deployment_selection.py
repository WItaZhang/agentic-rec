"""Choose the practical method from validation only, before opening final test."""

import json

import yaml

from .utils import digest, managed_run, verified_run_config, write_json


def select_deployment(candidates, settings):
    if set(candidates) != set(settings["candidates"]):
        raise ValueError("Deployment candidate set differs from the registered plan")
    if settings["partition"] != "validation" or settings["order"] != [
        "lowest_observed_api_cost", "simplest_method", "highest_validation_quality"
    ]:
        raise ValueError("Unsupported deployment selection protocol")
    eligible = {k: v for k, v in candidates.items()
                if v["api_usd_per_1000"] <= settings["budget_usd_per_1000"]}
    highest = max(v["ndcg"] for v in eligible.values())
    near = {k: v for k, v in eligible.items()
            if v["ndcg"] >= highest - settings["tolerance_to_highest_eligible_quality"]}
    selected = min(near, key=lambda k: (near[k]["api_usd_per_1000"],
        settings["simplicity_order"].index(k), -near[k]["ndcg"]))
    return {"selected_method": selected, "selected": candidates[selected],
        "candidates": candidates, "eligible": list(eligible), "within_quality_tolerance": list(near),
        "highest_validation_ndcg": highest,
        "selection_scope": "validation_only; tolerance is not a noninferiority claim",
        "test_role": "Report the frozen method's result; do not reselect from test quality"}


def run_deployment_selection(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        sources = config["sources"]
        paths = {key: root / sources[key] for key in ("baseline_run", "routing_run")}
        statuses = {key: json.loads((path / "manifest.json").read_text()) for key, path in paths.items()}
        if any(s["status"] != "completed" or s.get("test_scored") for s in statuses.values()):
            raise ValueError("Deployment selection requires completed development-only runs")
        original = {key: verified_run_config(path) for key, path in paths.items()}
        if original["baseline_run"]["stage"] != "validation_baseline_comparison":
            raise ValueError("Conventional outcomes must come from population validation")
        routing = original["routing_run"]
        matrix = root / routing["routing"]["validation_run"]
        if digest(matrix / "outcomes.json") != statuses["routing_run"]["validation_outcome_sha256"]:
            raise ValueError("Validation matrix changed since routing selection")
        outcomes = json.loads((matrix / "outcomes.json").read_text())
        ids = {r["request_id"] for r in outcomes}
        baselines = json.loads((paths["baseline_run"] / "outcomes.json").read_text())
        if any({r["request_id"] for r in rows} != ids or len(rows) != len(ids) for rows in baselines.values()):
            raise ValueError("Deployment methods must cover exactly the same validation requests")
        plan_path = root / sources["selection_plan"]
        settings = yaml.safe_load(plan_path.read_text(encoding="utf-8"))["selection"]
        selected = json.loads((paths["routing_run"] / "selection_frozen.json").read_text())
        candidates = {name: {"ndcg": sum(r["ndcg"] for r in rows) / len(rows),
            "api_usd_per_1000": 0, "requests": len(rows), "method": name}
            for name, rows in baselines.items()}
        budget = settings["budget_usd_per_1000"]
        for kind in ("fixed", "rule", "learned"):
            row = selected["chosen"][f"{kind}_{budget}"]
            candidates[f"selected_{kind}"] = {"ndcg": row["ndcg"],
                "api_usd_per_1000": 1000 * row["mean_accounted_usd"],
                "requests": row["requests"], "method": row["id"], "policy": row["policy"]}
        result = select_deployment(candidates, settings)
        result.update(selection_plan_sha256=digest(plan_path),
            source_hashes={key: {name: digest(path / name) for name in
                (("outcomes.json", "metrics.json") if key == "baseline_run" else ("selection_frozen.json",))}
                for key, path in paths.items()}, settings=settings)
        write_json(run_dir / "deployment_selection.json", result)
        manifest.update(test_scored=False, paid_api_usd=0,
            decision_sha256=digest(run_dir / "deployment_selection.json"))
        print(json.dumps({"selected_method": result["selected_method"], "candidates": candidates}), flush=True)
