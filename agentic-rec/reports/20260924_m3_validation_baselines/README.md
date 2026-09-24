# Conventional baselines on the exact LLM-validation request sample

Run `logs/20260924_010938_amazon_validation_baselines`, source `7e1fbf5`.
One hash-selected positive unseen request per validation user; all 3,318 users
are included, with 2,968 empty histories and 418 targets outside the training
catalog. No LLM generation and no final-test scoring occur in this analysis.

| Base model | NDCG@10 | HR@10 | CandidateRecall@200 |
|---|---:|---:|---:|
| Popularity | 0.063170 | 0.140145 | 0.552140 |
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

Popularity was subsequently evaluated on exactly the same sample in
`logs/20260924_014748_amazon_three_validation_baselines`, clean source `f195317`.
Its ordering is restored from the original pre-2018 positive counts and matches
the original model fingerprint `9af3900b3654761dceeefc2d46be812d77488828402d4ff4a7a13fd568f9d746`.
ItemKNN minus Popularity NDCG is +0.003385, nominal paired 95% interval
[+0.000663, +0.006196]. No LLM calls or refitting were needed; the original
ItemKNN/sequence metrics and intervals reproduce exactly. The additional run's
config, manifest and aggregate metrics are preserved as `three_model_*` files.
Popularity will also be a prespecified conventional final baseline, with its
own candidate pool, and part of the controlled serving resource audit.

Reproduce from the inner project after preparing both candidate bundles:

```sh
uv run --locked --extra yaml --extra experiments --extra api --extra local-llm python main.py --config configs/amazon_three_validation_baselines.yaml
```

Bind artifact paths to the newly emitted preparation runs when reproducing on
another machine. Their model fingerprints and data checksums must still match.
