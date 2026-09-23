# Amazon development replay and frozen candidates

Implementation: `a20628e`. Clean-source run: `20260923_232911_amazon_magazine_replay`.
This is a development baseline; **no final test quality has been computed**.
Protocol: `amazon_next_positive_unseen_v1`; single positive unseen target,
global UTC boundaries, user-macro metrics, full-catalog retrieval followed by
Top-50 candidates. Do not compare these numbers to the MovieLens multi-positive scores.

## Data and visibility

Source: [Amazon Reviews 2023, McAuley Lab](https://amazon-reviews-2023.github.io/),
Magazine_Subscriptions. Citation: Hou et al. (2024), *Bridging Language and Items
for Retrieval and Recommendation*, arXiv:2403.03952. Full raw file: 71,497 rows;
575 exact duplicates removed, 70,922 valid events. User-item joins use parent_asin;
timestamps retain millisecond resolution. No minimum-history user filtering.
Only aggregate results are published; raw review text and user identifiers stay local.

Base training ends 2018-01-01; policy training ends 2020-01-01; validation ends
2021-01-01; final test ends 2023-09-10. At time t, all requests use history strictly
before t. The batch becomes visible only after all predictions at that timestamp.
All previous feedback excludes seen items, while only positive feedback (rating
at least 4) contributes ItemKNN preference. Models and item universe remain frozen.

Base model selection uses an inner 2016-01-01 cutoff, entirely inside base_train.
Nine ItemKNN settings were evaluated on 2,000 label-blind sampled users from this
inner validation period. The selected model has 20 neighbors and shrinkage 100.
No policy/validation/test labels were used to select that model's parameters.

## Development results

| Partition | Method | Requests / users | User-macro NDCG@10 | HR@10 | CandidateRecall@50 |
|---|---|---:|---:|---:|---:|
| Policy train | Popularity | 9,568 / 8,272 | 0.074933 | 0.149051 | 0.379233 |
| Policy train | ItemKNN | 9,568 / 8,272 | 0.079761 | 0.154158 | 0.385033 |
| Validation | Popularity | 3,624 / 3,318 | 0.063029 | 0.139869 | 0.368568 |
| Validation | ItemKNN | 3,624 / 3,318 | 0.065456 | 0.142830 | 0.373081 |

Every eligible request contributes, including 737/448 cold-item misses in the
policy/validation blocks and 7,787/3,072 requests without prior history.
Conditional reranking quality cannot replace these all-request metrics.

Candidate coverage is too limited to justify extensive LLM experiments yet:
about 63% of validation targets cannot be repaired by Top-50 reranking. The next
step is a conventional causal sequence model and a development-only candidate
size sweep (50, 100, 200). This is a coverage diagnostic, not test-based retuning.

## Frozen inference artifacts

Local directory: `data/processed/20260923_232911_amazon_magazine_replay`.
`requests.jsonl` contains only request IDs, users, times and prior event IDs;
`candidates.jsonl` contains immutable members/scores/model hash; evaluator-only
targets are in a separate file. Candidate construction never accepts a target.
Each snapshot and each file has a content hash in the run manifest.

One request per user is selected by a seed-42 hash, then users are sampled by
hash. Frozen counts: 512 policy users, 512 validation users, 1,024 test users.
Selection is independent of target identity and retrieval success. These are
initial pilot manifests, not a statistical-power claim for final evaluation.
Test targets are materialized for the evaluator but have not been scored.

## Resources and reproduction

Run wall time: 148.23 seconds; process CPU time: 144.92 seconds. Zero LLM calls
and zero paid API expenditure. A later lint-only zip(strict=False) change does
not alter protocol behavior. The original source hashes remain in the manifest.

```sh
uv sync --locked --extra yaml --extra experiments
uv run --locked --extra yaml --extra experiments python main.py --config configs/amazon_magazine_replay.yaml
```

Download the raw file from the source URL in the configuration before running;
its SHA-256 is checked. Metadata source/hash and the training-only category
selection evidence are in [M1b](../20260923_m1b_amazon_profile/).
