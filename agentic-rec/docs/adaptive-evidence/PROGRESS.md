# Research execution checkpoint

Last updated: 2026-09-23 UTC. The full research goal remains active.

## Authorization and resources

- Branch: `codex/evidence-policy-study`; repository default:
  `claude/agentic-recommendation-survey-9afqks`.
- Paid API authorization updated by user: **USD 50 total**, estimate each round.
  First smoke round cap USD 1; campaign planning stop USD 45. No cloud rental.
  Persistent ledger: `logs/budget/openai_ledger.jsonl`; uncertain calls retain
  maximum reservations. Request a popup before exceeding the total authorization.
- Available local hardware: Ryzen 7 5800H (8 cores / 16 threads), 14.89 GB RAM,
  AMD integrated graphics; no CUDA GPU detected. CPU experiments are the default.
- Cached real model: `Qwen/Qwen2.5-1.5B-Instruct`, revision
  `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, including 3.09 GB weights.
  Availability is verified; inference feasibility and quality are not yet verified.
- User supplied a local OpenAI credential file, excluded via `.git/info/exclude`.
  Credential authentication verified through the unbilled model-list endpoint.
  Never copy credentials into configs, reports, tool output or Git.

## Initial audit

- Default branch at `1cacbc738529499a6c979d4f52f0dd0c4254e71d`: reference
  framework and eight adaptive-evidence design documents; all eight read.
- PR [#1](https://github.com/WItaZhang/agentic-rec/pull/1) is open, not merged,
  has no reviews/comments, and its Python 3.11/3.12 CI passed.
- Preserved its original commits `965081d` and `ad35806` by merging its branch
  into this task's branch. The existing PR was not rewritten or merged remotely.
- Fresh isolated clone; no other person's uncommitted project work was touched.

## Milestones

| Stage | Status | Implementation / evidence | Finding / next action |
|---|---|---|---|
| M0 audit and reproduction | validated | Original `ad35806`; local runs `logs/20260923_231823_ml100k_popularity` and `logs/20260923_231847_ml100k_popularity` | Both reproduce original metrics; 42 tests and Ruff pass. Preserve fixed-history, multi-positive protocol as `ml100k_fixed_history_multipositive_v0`. |
| M1a conventional models | validated | `ccd702a`; `logs/20260923_232152_ml100k_baselines`; [report](../../reports/20260923_m1a_baselines/README.md) | NDCG difference +0.000145, 95% CI [-0.008999, +0.008047]; no established gain, Recall lower. No test-based retuning. |
| M1b Amazon coverage | validated | `34cdb4e`; `logs/20260923_232442_amazon_training_profile`; `configs/amazon_profile.yaml` | Magazine selected using training-only coverage and memory. Digital Music retained as rejected candidate. |
| M1c event replay | validated | `a20628e`; `logs/20260923_232911_amazon_magazine_replay`; [report](../../reports/20260923_m1c_amazon_replay/README.md) | Validation CandidateRecall@50=0.373081; improve/expand retrieval before LLM scale-up. Test unscored. |
| M1d sequence baseline | validated | `45be0c3`; `logs/20260923_233625_amazon_magazine_sequence`; [report](../../reports/20260923_m1d_sequence/README.md) | Sequence validation NDCG 0.067832; retrieval no better. Freeze ItemKNN top-200 for main evidence comparisons. |
| M2 real LLM | real backends validated; development running | `2791754`, `7c26d47`, `00d8fcf`, `ea30200`; synchronous and batch smoke reports | 32+32 real completed smoke calls; USD 0.1055496 combined. Output repeatability requires analysis. 256-user paired pilot running; no effectiveness claim yet. |
| M3–M4 evidence and routing | planned | Conditional on usable evidence variation | Keep fixed, rule and random controls; no obligation to retain a failed complex method. |
| M5 sequential evidence | conditional | No implementation claimed | Only pursue if observations after fetching evidence can improve a decision. |
| M6 report and career materials | planned | Claim ledger tied to completed results | Strong baseline, statistics, ablations, limitations and honest LaTeX. |

Current work: durable paid-call accounting, target-free R1–R4 evidence, real API
smoke, then a development sample sized using variance and measured costs.
`configs/amazon_llm_smoke.yaml` fixes all settings and prices; prompts are versioned.
The local float32 adapter remains implemented but unexecuted (only about 1.9 GB
RAM free at inspection). No cloud resource, quantized model, or runtime was rented.
No external input is pending. Paid spending after first smoke: USD 0.069304; remaining USD 49.930696.
Actual run `logs/20260923_234647_amazon_llm_smoke`, source `2791754`: 32/32
completed, one deterministic ranking repair, all provider counts matched usage.
[Smoke report](../../reports/20260923_m2_api_smoke/README.md). Next: 256-user
uniform development pilot (USD 6 cap). This is not a final effectiveness result.
PR [#2](https://github.com/WItaZhang/agentic-rec/pull/2) passed Python 3.11/3.12
CI and was merged as `12d00bf`, preserving the original PR #1 commits.
The MovieLens foundation is now included in the repository default branch.

## Decisions and limitations

- The user's full-route authorization supersedes the design's instruction to stop
  after one milestone. Changes remain small and independently reviewable.
- M0 test NDCG@10 = 0.25981395087250847, Recall@10 = 0.07377170290648945.
  These are **multi-positive window** metrics, not next-item metrics.
- 235/315 test users have no training history; 454 cold-item positives remain
  misses. This substantially limits what personalization can improve in v0.
- The original input SHA-256 matches the official file; all 100,000 rows used.
- The existing reference framework's mutable candidate tools and character
  counters are unsuitable for claims about fixed-candidate/token-cost research.
- Amazon choice: Magazine has 2,939 training items and 74.8% category coverage;
  Digital Music has 47,203 items and 0.013% category coverage. Magazine's richer
  categories and lower memory cost support the first attribute experiment.
  Neither has substantial `features` coverage. Magazine has only 268 training
  users with at least five events: long-history conclusions will be limited.
- Raw Amazon files were fully downloaded from the official McAuley Lab URLs.
  Exact-record deduplication removed 575 Magazine and 1,670 Digital Music rows.
  No user k-core was applied, and no cold requests will be silently excluded.
- Freeze first Amazon block ends: 2018 / 2020 / 2021 / 2023-09-10 UTC;
  base-model inner validation begins 2016. Chosen from date/coverage profiles,
  before any ranking evaluation for these blocks. The final test is not scored
  during development. Config: `configs/amazon_magazine_replay.yaml`.
- M1a CPU wall 8.31 s; Amazon profiling wall 7.96 s. No paid services used.

## Resume commands

Run from the inner `agentic-rec/` project directory. Inspect this file and
`git status` before resuming; do not rerun final tests to tune against results.

```sh
uv sync --locked --extra yaml --extra experiments
uv run --locked --extra yaml --extra experiments python -m pytest
uv run --locked --extra yaml --extra experiments ruff check .
```

Local raw data, full predictions, models and logs remain git-ignored. Publish
only aggregate evidence and reproducible configurations, with dataset attribution.


## Live checkpoint: 2026-09-24 UTC

- Branch `codex/evidence-policy-study`; foundation merged via PR #2. GitHub also
  marks PR #1 merged because its original commits are now in the default branch.
- Real development pilot source `6c244dc`, 256 users, four plans, started at
  `logs/20260923_235144_amazon_llm_development_pilot`. It stopped after 48 recorded
  attempts when one call received HTTP 429. Its unknown usage remains reserved
  at USD 0.0035016; the fallback is retained in the outcome denominator.
- Resume source `7c26d47`, running in
  `logs/20260923_235347_amazon_llm_development_pilot_resume`. Explicit pacing:
  120,000 tokens/minute, 60 generation requests/minute, concurrency 4. No repeat
  of the 48 recorded attempts. Latency regimes are recorded; include queue time
  separately and do not pool the initial unpaced pilot as a controlled latency
  benchmark. Current budget is always read from the append-only campaign ledger.
- While this runs, paired analysis and batch replication feasibility were added.
  Analysis config `configs/amazon_pilot_analysis.yaml` refuses incomplete runs.
  The batch smoke reuses hash-identical inputs from the complete 32-call smoke,
  with a USD 0.25 cap. Batch cost is offline construction; no per-request service
  latency is inferred from batch turnaround.
- After pilot completion: run its paired analysis, inspect evidence heterogeneity
  and output noise, size the next label/validation runs, then freeze routing and
  the final test protocol. Final Amazon test quality remains unscored.


Batch smoke completed: `logs/20260924_000032_amazon_batch_smoke`, provider ID
`batch_6ab46827b00c8190b3e8f841c897c1b1`; collected results at
`logs/20260924_000757_amazon_batch_smoke_collect` (32 completed, USD 0.0362456,
139 s turnaround, service latency unknown). Roundtrip evaluator output:
`logs/20260924_000851_amazon_batch_roundtrip`. All new generation rounds remain
subject to a preflight estimate and shared USD 50 campaign cap. No new paid
round is started merely by preparing a batch bundle or recollecting its results.
Routing feature/model definitions exist but have not been fitted or evaluated;
this is not a completed learned-routing result. 68 local tests are available.


`logs/20260924_002548_amazon_user_history_profile` (`7f59558`) formalizes the
label-blind user-state coverage audit: policy training has 7,355 zero-history,
656 one-history and 261 older-history user states; validation has 2,968/247/103.
The stratified training sampler selects one request/user before grouping and
records inclusion probabilities. Routing fitting applies inverse inclusion weights;
evaluation remains population sampled. Implemented routing controls have not yet
been fit to a completed train/validation pair, and no routing efficacy is claimed.
Exact-input outcome reuse is limited to the same request/candidate snapshot; both
physical label-generation cost and logical action cost are preserved separately.
