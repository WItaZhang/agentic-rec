"""Final-test entry requires a recorded development-only freeze and intact artifacts."""

import json

import yaml

from .utils import digest, managed_run, write_json

INFERENCE_KEYS = ("protocol", "data", "retriever", "evidence", "llm")


def verify_final_config(config, root):
    location = root / config["final_test_freeze"]
    freeze = json.loads(location.read_text())
    manifest = json.loads((location.parent / "manifest.json").read_text())
    if manifest["status"] != "completed" or manifest.get("test_scored") or digest(location) != manifest["freeze_sha256"]:
        raise ValueError("Final protocol freeze is incomplete or altered")
    for key in (*INFERENCE_KEYS, "sampling", "seed", "runtime", "evaluation", "budget", "preparation"):
        if config[key] != freeze["test_config"][key]:
            raise ValueError(f"Final inference configuration changed after freeze: {key}")
    if config["evaluation"]["partition"] != "test":
        raise ValueError("Final freeze is only valid for its test partition")
    if digest(root / config["evidence"]["prompt_path"]) != freeze["prompt_sha256"]:
        raise ValueError("Final prompt changed after freeze")
    for filename, checksum in freeze["selection_artifact_hashes"].items():
        if digest(root / freeze["routing_run"] / filename) != checksum:
            raise ValueError("Development-selected routing artifact changed")
    if "deployment_selection_path" in freeze and digest(root / freeze["deployment_selection_path"]) != freeze["deployment_selection_sha256"]:
        raise ValueError("Practical method selection changed after freeze")
    return freeze


def run_freeze(config, config_path, root):
    settings = config["freeze"]
    with managed_run(config, config_path, root) as (run_dir, manifest):
        directory = root / settings["routing_run"]
        status = json.loads((directory / "manifest.json").read_text())
        if status["status"] != "completed" or status.get("test_scored"):
            raise ValueError("Cannot freeze from incomplete or test-selected routing")
        for old in (root / config["logging"]["path"]).glob("*/manifest.json"):
            record = json.loads(old.read_text())
            if record.get("final_test_freeze") and record.get("test_scored"):
                raise ValueError("A final test was already scored; do not refreeze against its results")
        grid = yaml.safe_load((root / settings["grid_path"]).read_text(encoding="utf-8"))
        routing_config = yaml.safe_load((directory / "config.yaml").read_text(encoding="utf-8"))
        for key, value in grid["routing"].items():
            if routing_config["routing"][key] != value:
                raise ValueError("Routing selection differs from the recorded grid")
        if routing_config["seed"] != grid["seed"] or routing_config["runtime"] != grid["runtime"]:
            raise ValueError("Routing randomness or compute settings changed")
        if routing_config["analysis"] != grid["analysis"]:
            raise ValueError("Primary comparison or analysis rules changed after grid registration")
        validation = root / routing_config["routing"]["validation_run"]
        validation_manifest = json.loads((validation / "manifest.json").read_text())
        inference = root / validation_manifest["prepared_run"]
        original = yaml.safe_load((inference / "config.yaml").read_text(encoding="utf-8"))
        if original["evaluation"]["partition"] != "validation" or validation_manifest.get("test_scored"):
            raise ValueError("The selection matrix must be validation-only")
        artifacts = ["selection_frozen.json", "config.yaml", "fit_resources.json",
                     *[p.name for p in sorted(directory.glob("estimator_*.joblib"))]]
        test_config = {"experiment_name": settings["test_experiment_name"], "stage": "frozen_matrix_prepare",
            "seed": config["seed"], **{key: original[key] for key in INFERENCE_KEYS},
            "sampling": settings["test_sampling"], "runtime": original["runtime"],
            "evaluation": {"partition": "test", "purpose": "frozen_final_comparison",
                           "additional_baselines": settings.get("additional_baselines", {})},
            "budget": settings["test_budget"], "logging": config["logging"],
            "preparation": original["preparation"],
            "final_test_freeze": str((run_dir / "freeze.json").relative_to(root))}
        if test_config["sampling"]["mode"] != "uniform_users" or test_config["seed"] != original["seed"]:
            raise ValueError("Final population sampling must preserve the development seed and user unit")
        record = {"scope": "one frozen final test; no post-test parameter selection",
            "test_config": test_config, "routing_run": settings["routing_run"],
            "selection_artifact_hashes": {name: digest(directory / name) for name in artifacts},
            "grid_sha256": digest(root / settings["grid_path"]), "analysis": grid["analysis"],
            "routing_cpu_threads": routing_config["runtime"]["cpu_threads"],
            "prompt_sha256": digest(root / original["evidence"]["prompt_path"]),
            "validation_outcome_sha256": status["validation_outcome_sha256"],
            "policy_outcome_sha256": status["policy_outcome_sha256"], "test_scored": False}
        if settings.get("deployment_selection_run"):
            selection_dir = root / settings["deployment_selection_run"]
            selection_status = json.loads((selection_dir / "manifest.json").read_text())
            selection_config = yaml.safe_load((selection_dir / "config.yaml").read_text(encoding="utf-8"))
            selection_path = selection_dir / "deployment_selection.json"
            if (selection_status["status"] != "completed" or selection_status.get("test_scored")
                    or selection_config["sources"]["routing_run"] != settings["routing_run"]
                    or digest(selection_path) != selection_status["decision_sha256"]):
                raise ValueError("Practical method selection must use this completed development fit")
            record.update(deployment_selection_path=str(selection_path.relative_to(root)),
                          deployment_selection_sha256=digest(selection_path))
        write_json(run_dir / "freeze.json", record)
        (run_dir / "test_config.yaml").write_text(yaml.safe_dump(test_config, sort_keys=False), encoding="utf-8")
        manifest.update(test_scored=False, freeze_sha256=digest(run_dir / "freeze.json"), stage_status="frozen")
        print("Final protocol frozen; no test inputs prepared and no labels scored", flush=True)
