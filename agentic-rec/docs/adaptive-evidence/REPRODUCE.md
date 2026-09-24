# Research reproduction and accounting

Run from the inner `agentic-rec/` directory. The authoritative stage/status table
is [PROGRESS.md](PROGRESS.md). This document does not imply that planned final
experiments have been completed.

## Environment and immutable inputs

```sh
uv sync --locked --extra yaml --extra experiments --extra api
uv run --locked --extra yaml --extra experiments --extra api ruff check .
uv run --locked --extra yaml --extra experiments --extra api python -m pytest
```

Use the checked-in Python version and lockfile. Add `--extra local-llm` for the
CPU sequence model and its tests. The optional local language-model adapter has
not been exercised with a real model and is not part of measured results.

Download inputs from the official URLs below; keep them read-only under
`data/raw/`. SHA-256 must match each YAML; different files require a new input
version. Raw datasets, credentials and generated predictions are excluded from Git.

- MovieLens: [u.data](https://files.grouplens.org/datasets/movielens/ml-100k/u.data)
  to `data/raw/ml-100k/u.data`. Follow [terms and citation](../real-data-experiment.md).
- Amazon Reviews 2023: append `Magazine_Subscriptions.jsonl.gz` or
  `Digital_Music.jsonl.gz` to
  `https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/`.
  Save under `data/raw/amazon/`.
- Amazon metadata: append `meta_Magazine_Subscriptions.jsonl.gz` or
  `meta_Digital_Music.jsonl.gz` to
  `https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/meta_categories/`.
  See the [official dataset](https://amazon-reviews-2023.github.io/) and
  Hou et al. (2024), [Bridging Language and Items for Retrieval and Recommendation](https://arxiv.org/abs/2403.03952).

## Conventional and temporal stages

```sh
uv run --locked --extra yaml --extra experiments python main.py --config configs/ml100k_popularity.yaml
uv run --locked --extra yaml --extra experiments python main.py --config configs/ml100k_baselines.yaml
uv run --locked --extra yaml --extra experiments python main.py --config configs/amazon_profile.yaml
uv run --locked --extra yaml --extra experiments python main.py --config configs/amazon_magazine_replay.yaml
uv run --locked --extra yaml --extra experiments --extra local-llm python main.py --config configs/amazon_magazine_sequence.yaml
```

Each run creates a new UTC timestamped folder with copied config, metrics, log,
input/source/lock hashes, and completion or failure state. The MovieLens protocol
is fixed-history multi-positive evaluation. Amazon uses timestamp-batch causal
history and a separate evaluator target table. Their metric values are not directly
comparable. Amazon development stages refuse final test scoring.

The sequence implementation is a SASRec-style causal Transformer with full-softmax
loss, not a reproduction of the original sampled objective. Both conventional model
selection and sequence selection use the base-training period's internal time split.

API configs pin a model fingerprint and initially name its original run directory.
If reproducing on a new checkout, `artifact_search_root: logs` resolves a newly
timestamped model only when its fingerprint exactly matches. It never chooses a
model using test scores or a latest-run heuristic. A present but mismatched model
fails instead of being silently replaced.

## Paid calls and secrets

The user's current authorization is USD 50 total; this is not permission for other
users to consume that account. Store the authorized key in the local file specified
by `llm.credential_file` (currently `../env.txt`, ignored at repository root). Never
commit the file or put its contents in YAML, logs, messages or reports.

All paid rounds require a versioned price table, total and round caps, a planning
stop and the shared ledger path. The initial campaign stops planning at USD 45.
`logs/budget/openai_ledger.jsonl` must survive process restarts and must not be
cleared to restart a round. Reservations are appended and flushed before submission;
unknown/unfinished calls retain their maximum charge. Report known usage-priced
cost and uncertain reservations separately. These are estimates from provider
usage, not reconciled invoices.

```sh
uv run --locked --extra yaml --extra experiments --extra api python main.py --config configs/amazon_llm_smoke.yaml
```

That command executes a new paid smoke. Read its config and preflight estimate
first. Do not rerun an existing experiment just to inspect its artifacts. Exact
provider token counting includes the output schema; billed usage comes from each
response. No character-based token estimate is used. Model, prompt, temperature,
candidate members, timeout and retry settings are recorded. Automatic provider
prefix caching is visible in usage; application generation caching is disabled in
the synchronous pilot.

If a synchronous round stops, its call and prediction journals retain completed
attempts and failed-request fallbacks. A `resume_from` config must preserve every
inference/sampling setting; rate-only amendments are explicit and change the
latency regime. In-flight requests are drained before an orderly stop. Do not
blindly retry an interrupted attempt whose outcome is uncertain.

## Offline batch labels

`matrix_prepare` produces target-free request/candidate views and hash-identified
planned calls. It may reuse a token count for identical payloads, without executing
generations. `batch_submit` reserves the entire selected shard before upload and
submission. `batch_collect` persists terminal responses and settles each physical
call once; recollection is idempotent. Submission and collection are separate states.
`matrix_evaluate` refuses a missing, duplicate, or input-mismatched action outcome.

For later matrices, identical model inputs may share one random draw **only within
the same request and candidate snapshot**, controlled in the preparation YAML.
This avoids mistaking stochastic differences between identical inputs for evidence
benefits. Logical action rows retain their single-action usage/cost; physical calls
and offline construction cost are deduplicated by call ID. No output is shared with
a later/earlier request. Independent repetitions remain necessary to assess model
noise for genuinely different inputs.

Batch turnaround is not request service latency. It is recorded separately; missing
service latency is null. Pricing discounts and shared label-construction calls are
not algorithmic serving savings. Counterfactual route cost comes from the measured
matrix execution regime; a frozen synchronous serving audit is needed to assess
deployment cost when caching/traffic conditions differ.

## Interpretation limits

Titles/categories are crawler snapshots under `snapshot_assumed_static`; this is
not a fully historical production replay. Snapshot ratings, price and rating counts
are excluded. A pretrained LLM may have encountered public review data; absence of
labels in inference inputs does not prove pretraining decontamination.

All unrecalled targets, OOV items, cold users and failed requests remain in the
relevant quality denominator. Single-request smoke scores are not effectiveness
evidence. A confidence interval containing zero is not evidence of equivalence;
quality tolerance and main test comparisons must be frozen on validation.
