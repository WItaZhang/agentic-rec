"""Configuration, paths, provenance and artifact helpers."""

import contextlib
import hashlib
import json
import platform
import random
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import yaml


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def utc_seconds(value):
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.utcoffset() is None:
        raise ValueError("Temporal cutoffs must include a timezone")
    return int(date.timestamp())


def load_config(path):
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-z0-9_]+", config["experiment_name"]):
        raise ValueError("Unsafe experiment name")
    if config.get("stage") == "llm_development":
        from .llm_experiment import validate_llm_config

        validate_llm_config(config)
        return config
    if config.get("stage") in ("profile_amazon", "replay_development", "sequence_development", "evidence_analysis",
                              "batch_submit", "batch_collect", "matrix_prepare", "matrix_evaluate", "routing_development",
                              "sampling_profile", "batch_schedule", "freeze_final_protocol", "frozen_matrix_prepare",
                              "final_policy_analysis", "serving_resource_audit", "validation_baseline_comparison"):
        return config
    if config.get("stage"):
        raise ValueError("Unknown experiment stage")
    if config["model"]["name"] not in ("popularity", "baseline_suite"):
        raise ValueError("Unknown conventional model")
    if config["model"]["name"] == "baseline_suite":
        supported = {"similarity": "binary_positive_cosine",
                     "shrinkage_formula": "dot_over_norm_product_plus_shrinkage",
                     "neighbor_direction": "source_row", "history_weight": "binary_positive",
                     "score_normalization": "none",
                     "fallback_and_ties": "training_popularity_then_item_id"}
        if any(config["model"].get(key) != value for key, value in supported.items()):
            raise ValueError("Unsupported ItemKNN protocol setting")
        if not config["model"]["neighbors_grid"] or not config["model"]["shrinkage_grid"]:
            raise ValueError("Validation grid cannot be empty")
    if not 1 <= config["model"]["positive_rating"] <= 5 or config["train"]["k"] < 1:
        raise ValueError("Invalid threshold or k")
    utc_seconds(config["data"]["train_end"])
    utc_seconds(config["data"]["validation_end"])
    return config


def prepare_paths(config, root):
    raw = (root / config["data"]["raw_path"]).resolve()
    outputs = [(root / config[section][key]).resolve() for section, key in (
        ("data", "processed_path"), ("data", "staging_path"), ("logging", "path")
    )]
    for output in outputs:
        if output == raw.parent or raw.parent in output.parents or output in raw.parents:
            raise ValueError("Outputs must be isolated from raw data")
        if output == root or root not in output.parents:
            raise ValueError("Outputs must stay inside the experiment project")
        if output.parts[len(root.parts)] not in ("data", "logs"):
            raise ValueError("Outputs must stay in data/ or logs/")
    for i, left in enumerate(outputs):
        for right in outputs[i + 1:]:
            if left == right or left in right.parents or right in left.parents:
                raise ValueError("Output directories must be separate")
    for output in outputs:
        output.mkdir(parents=True, exist_ok=True)
    return raw, outputs


def create_run_dir(log_root, name):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = log_root / f"{stamp}_{name}"
    path.mkdir()  # Never overwrite a previous run, including a same-second collision.
    return path


def provenance(root):
    def git(*args):
        try:
            result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        except FileNotFoundError:
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    status = git("status", "--porcelain")
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(status) if status is not None else None,
        "uv_lock_sha256": digest(root / "uv.lock"),
        "source_sha256": {str(path.relative_to(root)).replace("\\", "/"): digest(path)
                          for path in [root / "main.py", *sorted((root / "src").glob("*.py"))]},
    }


def seed_everything(seed):
    random.seed(seed)


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


@contextlib.contextmanager
def managed_run(config, config_path, root):
    """Shared run envelope for new stages; captures failures and immutable source provenance."""
    _, (_, _, log_root) = prepare_paths(config, root)
    run_dir = create_run_dir(log_root, config["experiment_name"])
    (run_dir / "config.yaml").write_bytes(Path(config_path).read_bytes())
    started, cpu_started = time.perf_counter(), time.process_time()
    manifest = {"status": "running", **provenance(root), "config_sha256": digest(config_path)}
    write_json(run_dir / "manifest.json", manifest)
    with (run_dir / "run.log").open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(Tee(sys.stdout, log)), contextlib.redirect_stderr(Tee(sys.stderr, log)):
            try:
                seed_everything(config["seed"])
                yield run_dir, manifest
                manifest["status"] = "completed"
                print(f"Artifacts: {run_dir.relative_to(root)}")
            except Exception as error:
                traceback.print_exc()
                manifest["status"] = "failed"
                write_json(run_dir / "failure.json", {"error": str(error), "status": "failed"})
                raise
            finally:
                manifest["wall_seconds"] = time.perf_counter() - started
                manifest["cpu_seconds"] = time.process_time() - cpu_started
                write_json(run_dir / "manifest.json", manifest)
