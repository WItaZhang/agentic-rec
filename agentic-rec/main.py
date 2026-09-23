"""Entrypoint: YAML config -> components -> experiment artifacts."""

import argparse
import contextlib
import sys
import traceback
from pathlib import Path

from src.data import load_ratings, temporal_split
from src.trainer import run_experiment
from src.utils import (
    Tee,
    create_run_dir,
    digest,
    load_config,
    prepare_paths,
    provenance,
    seed_everything,
    utc_seconds,
    write_json,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="Only selects a YAML; no overrides")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    config = load_config(args.config)
    if config.get("stage") == "profile_amazon":
        from src.profiling import run_profile

        run_profile(config, args.config, root)
        return
    raw, (processed, _staging, logs) = prepare_paths(config, root)
    run_dir = create_run_dir(logs, config["experiment_name"])
    (run_dir / "config.yaml").write_bytes(args.config.read_bytes())
    with (run_dir / "run.log").open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(Tee(sys.stdout, log)), contextlib.redirect_stderr(Tee(sys.stderr, log)):
            try:
                seed_everything(config["seed"])
                manifest = {"status": "running", **provenance(root), "config_sha256": digest(args.config)}
                write_json(run_dir / "manifest.json", manifest)
                actual_hash = digest(raw)
                if actual_hash != config["data"]["sha256"]:
                    raise ValueError("Raw dataset checksum mismatch; refusing to run")
                rows = load_ratings(raw)
                splits = temporal_split(rows, utc_seconds(config["data"]["train_end"]),
                                        utc_seconds(config["data"]["validation_end"]))
                split_summary = {
                    name: {"count": len(part), "min_timestamp": min(r.timestamp for r in part),
                           "max_timestamp": max(r.timestamp for r in part)}
                    for name, part in splits.items()
                }
                # Boundaries + immutable input hash fully identify each partition.
                write_json(processed / f"{run_dir.name}_splits.json", split_summary)
                print(f"Loaded {len(rows)} ratings; splits: {split_summary}")
                metrics = run_experiment(config, splits, run_dir)
                if digest(raw) != actual_hash:
                    raise RuntimeError("Raw data changed during the experiment")
                manifest.update(status="completed", raw_sha256=actual_hash,
                                data_source=config["data"]["source"], splits=split_summary)
                write_json(run_dir / "manifest.json", manifest)
                print(metrics)
                print(f"Artifacts: {run_dir.relative_to(root)}")
            except Exception as error:
                traceback.print_exc()
                write_json(run_dir / "failure.json", {"status": "failed", "error": str(error)})
                if "manifest" in locals():
                    manifest["status"] = "failed"
                    write_json(run_dir / "manifest.json", manifest)
                raise


if __name__ == "__main__":
    main()
