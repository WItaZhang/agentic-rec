# MovieLens conventional baseline comparison

This is an engineering baseline under `ml100k_fixed_history_multipositive_v0`,
not an LLM, next-item, or adaptive-routing result. All 100,000 original ratings
were processed. Input source and terms: [GroupLens](https://grouplens.org/datasets/movielens/100k/).
Cite Harper and Konstan (2015), DOI 10.1145/2827872.

Implementation: `ccd702a`. Clean-source run: `20260923_232152_ml100k_baselines`.
Configuration: [ml100k_baselines.yaml](../../configs/ml100k_baselines.yaml).
No test-based retuning followed this run.

## Protocol and selection

Global cutoffs are 1998-01-01 and 1998-03-01 UTC. The same training-only
history is used for validation and test. Targets are all eligible unseen
positive items in each window. Cold targets remain misses. All training items
are ranked; there is no negative sampling or target injection.

ItemKNN uses binary positive user-item cosine similarities, no self-edges,
source-row top neighbors, sum aggregation, and training popularity followed by
item ID for ties/fallback. Negative feedback is excluded from recommendations
but does not contribute positive preference. The denominator is the product
of vector norms plus shrinkage. Validation NDCG selected 20 neighbors and
shrinkage 10 from nine prespecified configurations. The selection artifact was
written before evaluating test. Group history threshold is the training-user median.

## Results

| Test method | Users | Recall@10 | NDCG@10 | Mean rank latency (ms) | P95 (ms) |
|---|---:|---:|---:|---:|---:|
| Popularity | 315 | 0.073772 | 0.259814 | 0.063 | 0.099 |
| ItemKNN | 315 | 0.069132 | 0.259959 | 1.318 | 1.681 |

Primary paired NDCG difference (ItemKNN minus Popularity): **+0.000145**,
95% user-bootstrap interval **[-0.008999, +0.008047]**, 5,000 replicates.
Recall difference: -0.004639, interval [-0.013478, +0.002029]. This does not
establish an improvement or equivalence/non-inferiority. No quality tolerance
was declared for this engineering experiment.

235/315 users have no training history and receive exactly the same ranking
under both methods. The 22 short-history users have NDCG difference +0.001671
and the 58 long-history users +0.000156; both intervals are wide and span zero.
These subgroup results are descriptive, with no corrected confirmatory claims.
There are 12,275 positive targets, including 454 cold-item misses.

## Resources, failures, and continuation

The complete nine-fit benchmark and statistics used 8.31 wall seconds and
8.25 process CPU seconds; training fits used 1.85 wall seconds in total.
Paid API use, LLM calls and tokens were all zero. Single-process CPU, no cache.
Per-user latency measures ranking only, excludes metric calculation, and is a
descriptive local measurement without interleaved repetitions; do not extrapolate
it to production serving. Local electricity consumption was not measured.

The failure to improve is consistent with the protocol's dominant cold-user
population and stale fixed history; this is an interpretation, not proof of a
causal mechanism. Keep Popularity as a control. Proceed with the separately
versioned event-replay protocol, where earlier events can become visible to
later requests, and assess coverage before running LLM experiments.

## Reproduction

From the inner project directory, obtain the checksummed raw file as described
in [real-data-experiment.md](../../docs/real-data-experiment.md), then run:

```sh
uv sync --locked --extra yaml --extra experiments
uv run --locked --extra yaml --extra experiments python main.py --config configs/ml100k_baselines.yaml
```

The public directory contains aggregate statistics and provenance. The original
per-user predictions and fitted graph remain in the ignored local run directory;
they can be regenerated with this command. Latencies vary by machine/load.
