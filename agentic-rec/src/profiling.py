"""Training-only dataset profiling and immutable input audit."""

from .data import load_amazon_metadata, load_amazon_reviews
from .feature import training_profile
from .utils import digest, managed_run, utc_seconds, write_json


def run_profile(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        profiles, inputs = {}, {}
        for category in config["data"]["categories"]:
            for kind in ("reviews", "metadata"):
                spec = category[kind]
                path = root / spec["path"]
                observed = digest(path)
                if observed != spec["sha256"]:
                    raise ValueError(f"Checksum mismatch for {path.name}")
                inputs[spec["path"]] = {"sha256": observed, "source": spec["source"]}
            events, audit = load_amazon_reviews(root / category["reviews"]["path"])
            metadata = load_amazon_metadata(root / category["metadata"]["path"],
                                            config["data"]["allowed_metadata_fields"])
            profiles[category["name"]] = {
                "input_audit": audit,
                **training_profile(events, metadata, utc_seconds(config["data"]["base_train_end"]) * 1000,
                                   config["protocol"]["positive_rating"],
                                   config["profile"]["history_thresholds"])}
            print(f"{category['name']}: {profiles[category['name']]}")
        for path, record in inputs.items():
            if digest(root / path) != record["sha256"]:
                raise RuntimeError("Raw data changed during profile")
        manifest.update(inputs=inputs, paid_api_usd=0, llm_calls=0)
        write_json(run_dir / "dataset_profile.json", profiles)
        write_json(run_dir / "metrics.json", {"stage": "profile_only", "ranking_evaluated": False})
