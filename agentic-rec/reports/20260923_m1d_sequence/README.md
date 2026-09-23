# Sequence baseline and candidate coverage

Actual CPU run: `logs/20260923_233625_amazon_magazine_sequence` (257.47 s wall,
438.41 s process CPU, zero paid API calls). Implementation: `45be0c3`;
run manifest records a dirty checkout and exact source hashes. The then-untracked
local adapter was subsequently preserved in `8b3a885`; no altered sequence training
or evaluation logic is hidden by the dirty flag.

The SASRec-style causal Transformer uses full-softmax cross-entropy, not the
paper's sampled objective. Base-train internal temporal validation selected
64 dimensions, one layer, 20 epochs from six evaluated checkpoints. We do not
claim a paper reproduction. No final Amazon test quality was accessed.

| Model | Validation user-macro NDCG@10 | Candidate recall@50 | @100 | @200 |
|---|---:|---:|---:|---:|
| Popularity | 0.063029 | 0.368568 | 0.465028 | 0.551406 |
| ItemKNN | 0.065456 | 0.373081 | 0.467598 | 0.553227 |
| Causal sequence | 0.067832 | 0.367768 | 0.462361 | 0.548086 |

The sequence model is a stronger ranking baseline by point estimate, but it does
not improve candidate coverage. These development point differences do not yet
establish statistical superiority. Use frozen ItemKNN top-200 for the main evidence
comparison, selected for coverage before API outcomes; keep the stronger sequence
ranker for robustness. OOV and unrecalled targets remain misses. Top-200 still
misses about 45% of validation targets, explicitly limiting attainable quality.

Reproduce: `uv run --locked --extra yaml --extra experiments --extra local-llm
python main.py --config configs/amazon_magazine_sequence.yaml` (one command).
Inputs are the original Amazon Reviews 2023 Magazine files, with SHA-256 in config.
See the temporal replay report for the four-period protocol and data citation.
