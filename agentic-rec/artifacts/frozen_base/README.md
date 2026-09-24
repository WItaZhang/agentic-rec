# Frozen base-recommender artifacts

These small derived model artifacts make the historical evidence experiments
replayable without requiring bit-identical cross-platform retraining. Raw reviews,
API credentials, request prompts and review text are not included here.

| Model | Source run | Weight bytes | Model fingerprint |
|---|---|---:|---|
| ItemKNN | `20260923_232911_amazon_magazine_replay` | 55,543 | `8f35c8afe52cf6cc1669ba9e9cea3b7eda364043e00d16cb7456e939781da6b8` |
| Causal sequence | `20260923_233625_amazon_magazine_sequence` | 963,955 | `3c706f2f0e67e3cf57aa0196e61615bc2f5b201d695d3a6c83aa271b45758932` |

Each directory includes training config, source manifest, model metadata and file
checksums. Both models use only events before 2018; hyperparameter selection uses
an internal pre-2018 temporal holdout. The loader checks the model fingerprint,
including weights, and refuses a mismatch. The sequence checkpoint is loaded
with `weights_only=True`. This preserves the original source commits and does
not substitute a newer model based on validation or test performance.

For raw-data reproduction and dataset attribution, see
[the reproduction guide](../../docs/adaptive-evidence/REPRODUCE.md). Amazon Reviews
2023 is provided by the McAuley Lab; see Hou et al. (2024),
[Bridging Language and Items for Retrieval and Recommendation](https://arxiv.org/abs/2403.03952).
