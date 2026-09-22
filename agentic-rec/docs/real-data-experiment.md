# MovieLens 100K: first real-data experiment

This small addition establishes an evaluation protocol before connecting the
existing agent framework or a real LLM. The original TOML recipes and package
are unchanged. No new model architecture or performance claim is introduced.

## Reproduce

From `agentic-rec/`, use Python 3.11 (recorded in `.python-version`):

```sh
uv sync --locked --extra yaml
```

Read the [GroupLens dataset terms](https://files.grouplens.org/datasets/movielens/ml-100k-README.txt).
Download [u.data](https://files.grouplens.org/datasets/movielens/ml-100k/u.data)
once into `data/raw/ml-100k/u.data`. Create those directories if needed.
The loader only reads this file and checks its SHA-256 against the YAML.
Do not commit or redistribute the dataset. The official terms require separate
permission for redistribution and commercial use. Cite Harper and Konstan (2015),
[DOI 10.1145/2827872](https://doi.org/10.1145/2827872), when publishing research.

```sh
uv run --locked --extra yaml python main.py --config configs/ml100k_popularity.yaml
uv run --locked --extra yaml python -m pytest
uv run --locked --extra yaml ruff check .
```

The CLI only selects a config file. No hyperparameters are overridden through
environment variables or command-line flags. Paths are relative to the project
root; config selection is relative to the caller's current directory.

## Frozen protocol v0

- Train: timestamp < 1998-01-01 UTC; validation: [1998-01-01, 1998-03-01);
  test: >= 1998-03-01. These are global cutoffs, not per-user last-item splits.
  Timestamp ties always stay together. This does not use the supplied random folds.
- Positives: rating >= 4. Popularity counts only positive training ratings.
  The candidate universe contains only items observed in training, including items
  with zero positive counts. Equal counts break by ascending integer item ID.
- Both held-out partitions use the same frozen training model and training history.
  All training interactions (including negative ratings) are excluded from recommendations.
  Validation history is not fed into test ranking. No validation-based tuning yet.
- Rank every candidate, with no sampled negatives. Macro Recall@10 and binary
  NDCG@10 average over users with at least one eligible held-out positive.
  Cold users receive the same popularity ranking. Cold-item positives remain in
  the denominator as misses. Counts report both, plus excluded users.
- These are offline ratings, not randomized exposure or click data. Unrated
  items are unobserved; the results cannot establish causal user benefit.

## Module and artifact boundaries

`src/data.py`: loading, validation, splitting; `feature.py`: pure transforms;
`model.py`: ranking definition; `trainer.py`: fit, evaluate, checkpoint;
`utils.py`: configuration, paths, seed, provenance; `main.py`: wiring only.

`uv.lock` fixes dependencies; YAML support is optional so the existing package
keeps its zero-runtime-dependency installation. New experiments use YAML; existing
TOML recipes remain structural examples and are not migrated in this step.

Each run writes `logs/YYYYMMDD_HHMMSS_ml100k_popularity/` (UTC) with copied config,
metrics, model, manifest (input/config/lock hashes, Git revision and dirty status),
and captured stdout/stderr. Errors also produce `failure.json` after run creation.
Same-second collisions fail instead of overwriting. Split summaries go under
`data/processed/`; `data/staging/` is reserved for future caches. None are tracked.

Tests use synthetic rows and need no network. They verify cutoff ties, leakage,
cold-item denominators, known ranking metrics, corrupt input and path isolation.
CI retains both supported test versions (3.11/3.12) and the original synthetic demo.

Next bounded step: add one item-kNN baseline under this identical protocol, then
compare it with popularity before wiring agent components into the real dataset.
