# Conventional baselines on the exact LLM-validation request sample

Run `logs/20260924_010938_amazon_validation_baselines`, source `7e1fbf5`.
One hash-selected positive unseen request per validation user; all 3,318 users
are included, with 2,968 empty histories and 418 targets outside the training
catalog. No LLM generation and no final-test scoring occur in this analysis.

| Base model | NDCG@10 | HR@10 | CandidateRecall@200 |
|---|---:|---:|---:|
| ItemKNN | 0.066556 | 0.144665 | 0.553948 |
| Causal sequence model | 0.068723 | 0.146474 | 0.550030 |

Sequence minus ItemKNN NDCG is +0.002167, 95% paired-user bootstrap interval
[+0.000173, +0.004190] (10,000 resamples). HR difference is +0.001808
[-0.001808, +0.005425]; candidate-recall difference is -0.003918
[-0.008137, +0.000301]. These are development comparisons with nominal intervals.
The sequence baseline improves the NDCG point estimate with a positive interval,
but neither a hit-rate increase nor a candidate-recall increase is established.

Each conventional model uses its own candidate pool. Subsequent LLM comparisons
must hold the candidate pool fixed **within** each retriever; a cross-pool change
must not be attributed to evidence routing. Sequence-model architecture and
epochs were selected using only the internal base-training temporal split.
The full-softmax SASRec-style implementation is an adaptation, not a numerical
reproduction of a paper. See the original sequence-baseline report for training.

These values differ from the earlier all-request, user-macro M1d values because
this comparison uses the predeclared one-request-per-user LLM sample. No model
was retrained or selected using this comparison. The preceding diagnostic run
`logs/20260924_010857_amazon_validation_baselines` has identical quality metrics
but omitted the cold-target flag; its displayed zero cold count is superseded
by this corrected artifact, with all 418 cold-target misses retained.

Reproduce from the inner project after preparing both candidate bundles:

```sh
uv run --locked --extra yaml --extra experiments --extra api --extra local-llm python main.py --config configs/amazon_validation_baselines.yaml
```

Bind artifact paths to the newly emitted preparation runs when reproducing on
another machine. Their model fingerprints and data checksums must still match.
