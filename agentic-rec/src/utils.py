"""Configuration, paths, provenance and artifact helpers."""

import hashlib
import json
import platform
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    if config["model"]["name"] != "popularity":
        raise ValueError("Only the popularity model is implemented")
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
