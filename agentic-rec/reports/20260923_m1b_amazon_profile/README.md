# Training-only dataset choice

The completed run `logs/20260923_232442_amazon_training_profile` profiles the full
downloaded Magazine_Subscriptions and Digital_Music files, then computes selection
statistics using events strictly before 2018-01-01 UTC. No recommendation quality
or final-test labels were used to choose the category. The accompanying config,
input hashes, manifest, log and `dataset_profile.json` are the primary evidence.

| Pre-2018 property | Magazine Subscriptions | Digital Music |
|---|---:|---:|
| Events | 45,902 | 78,373 |
| Users | 38,987 | 61,048 |
| Items | 2,939 | 47,203 |
| Title coverage | 100% | 99.99% |
| Category coverage | 74.82% | 0.0127% |
| Users with at least five events | 268 | 883 |
| Dense float64 item matrix size estimate | 0.064 GiB | 16.601 GiB |

Magazine was selected for its usable category metadata and manageable local CPU
memory footprint. The dense matrix figure is a size calculation, not measured
peak memory or a claim that the final sparse model allocates that matrix.
Both datasets are sparse in user history; stronger claims about rich long-term
preferences will require another population. Neither category provides useful
`features` coverage in this snapshot.

The Magazine file contains 71,497 raw rows, 575 exact duplicates and 70,922 valid
events across all dates. Digital Music contains 130,434 raw rows, 1,670 exact
duplicates and 128,764 valid events. No minimum-history user filtering is applied.
Titles/categories are treated as static crawler-snapshot text, a stated limitation
rather than verified point-in-time metadata. Raw files remain read-only.

```sh
uv run --locked --extra yaml --extra experiments python main.py --config configs/amazon_profile.yaml
```

The download URLs and checksums are in the config. Source: [Amazon Reviews 2023,
McAuley Lab](https://amazon-reviews-2023.github.io/). No paid API was used.
