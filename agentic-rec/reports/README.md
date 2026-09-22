# MovieLens 100K baseline evidence — 2026-09-21 (America/Los_Angeles)

Two local executions on clean source commit
[`965081d2645a`](https://github.com/WItaZhang/agentic-rec/commit/965081d2645a85a5f879c979aa0b8476c9d86222)
produced byte-identical `metrics.json` files. UTC run IDs were
`20260922_003349_ml100k_popularity` and `20260922_003423_ml100k_popularity`.
The second run's copied config, manifest, metrics and stdout/stderr log are retained
in [20260922_003423_ml100k_popularity/](20260922_003423_ml100k_popularity/).
Raw ratings and the fitted item ranking are not redistributed.

| Partition | Ratings | Evaluated users | Recall@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| Train | 52,899 | — | — | — |
| Validation | 25,086 | 324 | 0.079545 | 0.286367 |
| Test | 22,015 | 315 | 0.073772 | 0.259814 |

Protocol: global UTC cutoffs, positive rating >= 4, full training-item candidate
set, deterministic popularity counts, training-history exclusions, and no model
refit or hyperparameter search. See [full protocol](../docs/real-data-experiment.md).
The implementation test suite passed 42 tests; the original 11 synthetic recipes
also completed. These checks establish the first experiment path, not model superiority.

**Interpretation:** 235 of the 315 evaluated test users have no training history,
and 454 test positive targets refer to items absent from the training catalog.
They remain in the evaluation, rather than being silently removed. This global
time split has substantial cold-start exposure, which must be considered in the
next baseline comparison. This is an offline popularity baseline on historical
ratings, not an agent or paper benchmark result and not a measure of live impact.

Run timestamps use UTC; the report date above uses the requested Los Angeles timezone.
