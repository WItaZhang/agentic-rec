# Validation failures: retrieval limits and useful base hits lost

This analysis uses the already completed **3,318-user population validation**, with zero additional model calls. It does not use the incomplete policy-training matrix or final-test labels. Cases are selected by a fixed hash within each error class (seed 42, three cases per class), not by the largest loss or the most persuasive example. Classes overlap.

| Observable event | Recent R1 | Full R4 |
|---|---:|---:|
| Requests | 3,318 | 3,318 |
| Target absent from candidate pool | 1,480 | 1,480 |
| Cold target | 418 | 418 |
| Base top-10 hit lost | 38 | 388 |
| Base top-10 miss rescued | 49 | 196 |
| Lower NDCG than base | 43 | 395 |
| Empty history and output miss | 2,524 | 2,720 |
| Deterministic ranking repair | 15 | 5 |
| API generation failure | 0 | 0 |
| Observed API USD on unrecalled targets | 1.0552606 | 2.2795312 |

The base has 480 hits. R1 finishes with 491 hits (480−38+49); R4 finishes with 288 (480−388+196). Full evidence loses 80.8% of the base's original hits, so its lower quality cannot be explained only by the five repaired rankings. It still rescues some misses; choosing those requests after observing their targets would be an invalid oracle policy.

About 44.6% of the measured single-action API cost is spent on unrecalled targets in each scheme. Since candidates are fixed, those calls cannot produce an exact target hit. This is a diagnosis of the pipeline's retrieval ceiling, **not an executable rule to skip such calls**: the target is unknown at prediction time. Cold targets are included among retrieval misses and must not be added again as separate failures.

## Deterministically selected examples

All titles below are public product metadata. Full case records include distinct item IDs, candidate/output ranks and at most three history events, but no user identifiers or review text. Product variants can share a title while retaining different item IDs; this analysis does not redefine exact-item relevance using title similarity.

| Example and selection class | Visible history | Target and outcome | Supported observation |
|---|---|---|---|
| R1 `q_e000068406`, base hit lost | One-star review of *Country*, 31 days earlier | *Popular Science*: base rank 3, removed from top 10 | The output begins with country/lifestyle titles despite a negative historical rating. This suggests a case worth checking for over-weighted topic matching; the observed output does not reveal the model's internal reason. |
| R1 `q_e000027954`, miss rescued | Five-star *HGTV Magazine*, 345 days earlier | *Fine Homebuilding*: base rank 188 → output rank 8 | A retrieved but low-ranked relevant item can be rescued. This does not tell a deployable router when a rescue will occur. |
| R4 `q_e000053715`, base hit lost | No history | *Family Handyman*: base rank 5, removed from top 10 | Full evidence changes a useful base order without personal history. The leading output titles are *National Geographic*, *Popular Science*, and *Smithsonian*. |
| R4 `q_e000019670`, miss rescued | No history | *Food Network Magazine*: base rank 11 → output rank 5 | A similar empty-history reranking can also help an individual request. One favorable case cannot outweigh population losses. |
| Both, `q_e000070873`, retrieval miss | No history | *Closer Weekly*: absent from top-200 candidates | Neither reranker can recover this target under the fixed-candidate protocol. The request remains in every metric denominator. |

These cases illustrate observable error patterns, not causal explanations or newly tuned rules. The registered routing grid, prompts, history-group boundaries and future primary comparison are unchanged. The [population paired intervals](../20260925_m3_evidence_validation/README.md) remain the quantitative evidence for quality differences; selected examples do not supply new significance claims.

## Provenance and reproduction

- Matrix: `logs/20260925_071030_amazon_validation_matrix_evaluate`.
- Failure run: `logs/20260925_191516_amazon_validation_failure_analysis`, source `994cedc`.
- [Configuration](config.yaml), [all class counts and selected cases](failure_cases.json), [manifest and matrix checksum](manifest.json).
- With the documented checksummed local dataset and completed matrix, from the inner project root:

```powershell
uv run --locked --extra yaml --extra experiments --extra api python main.py --config configs/amazon_validation_failure_analysis.yaml
```

This command reads local results; it does not instantiate an API client or spend money. The `api` extra supplies existing pipeline dependencies, not permission for new calls. Final-test failure analysis is still gated on a completed frozen test and has not run.
