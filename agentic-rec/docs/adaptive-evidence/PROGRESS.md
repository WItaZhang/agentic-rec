# Research execution checkpoint

Last updated: 2026-09-24 UTC. The full research goal remains active. The newest
checkpoint is at the bottom; historical spending/status entries are not current balances.

## Authorization and resources

- Branch: `codex/validation-study-results`; repository default:
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
| M2 real LLM | pilot completed and analyzed | `7c26d47`, `d6b41bf`; [pilot report](../../reports/20260924_m2_development_pilot/README.md) | 1024 attempts, one retained 429 fallback. Recent evidence has no established aggregate gain; full evidence is directionally worse. Same-input output noise can inflate oracle headroom. |
| M3 fixed evidence | expanded validation running | `59ff478`, `453746d`; 1045-user policy bundle and 3318-user validation bundle | Exact input sharing within requests; immutable candidates; real batch cost accounting. Strong-base and content controls are being prepared. |
| M4 routing | implemented, not yet fitted | `d672712` precommits the selection grid; `59460f5` adds final-test gates | Rules, cost-calibrated random control, weighted Ridge/boosting policies; wait for complete matrices before fitting/selection. |
| M5 sequential evidence | conditional | No implementation claimed | Only pursue if observations after fetching evidence can improve a decision. |
| M6 report and career materials | planned | Claim ledger tied to completed results | Strong baseline, statistics, ablations, limitations and honest LaTeX. |

Initial M2 checkpoint (superseded by the live checkpoints below): durable paid-call
accounting, target-free R1–R4 evidence, real API smoke, then a variance-sized pilot.
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

## Pilot completion and next checkpoint: 2026-09-24 00:40 UTC

- The resumed 256-user pilot is complete, with 1024 attempts and one retained
  HTTP 429 fallback. Known pilot USD 1.0458048; accounted USD 1.0493064.
  Campaign known USD 1.1513544; accounted USD 1.154856; no pending generation.
- Paired analysis source `d6b41bf`, run `logs/20260924_004054_amazon_pilot_analysis`.
  R1 minus R0 NDCG +0.001965, 95% CI [-0.006972, +0.010661]; no established gain.
  Full evidence has lower mean quality, with wide uncertainty. Same-input
  repetitions reveal output noise that can inflate a label-aware oracle.
- Curated report: `reports/20260924_m2_development_pilot/README.md`.
- Next prepared bundles: `configs/amazon_policy_matrix_prepare.yaml` (all 917
  warm states plus 128 cold states, inverse inclusion fitting weights) and
  `configs/amazon_validation_matrix_prepare.yaml` (all 3318 validation users).
  Exact input counts precede paid submission; same-request identical inputs
  share one physical generation. Phase caps USD 6 and USD 12 respectively.
- Final Amazon test remains unscored. Routing remains implemented but unfitted.
  74 tests and Python 3.11/3.12 CI passed at `d6b41bf`. Follow this checkpoint
  rather than the superseded running-pilot note above.

## Expanded validation and reproducibility correction

- Validation input bundle `logs/20260924_004459_amazon_validation_matrix_prepare`
  is complete: 3318 users, 13272 logical actions, 6842 physical requests, 908
  exact token-count queries. Preflight 37,580,364 input tokens; estimated USD
  7.7131 at 36 output tokens without cache; maximum reserved USD 9.0925.
  Config `configs/amazon_validation_batch.yaml` caps this phase at USD 12.
- Scheduler `logs/20260924_005144_amazon_validation_batch` submitted its first
  146 calls (`batch_6ab4742b02588190bdf3e76b72748346`). The second shard failed
  payload comparison before reservations/upload; it made no paid request.
- Root cause: summing ItemKNN rows selected from a string set permits floating
  point reduction order to vary across processes. Auditing all 3318 validation
  users found six changed score vectors, maximum absolute difference 1.39e-17,
  zero changed candidate orders and zero changed top-10 rankings.
- Fix: canonical sorted row reduction for future retrieval; batch submission
  consumes the immutable saved candidate snapshot and verifies its file and
  prompt hashes. Existing completed/prepared observations are preserved. This
  is an execution/provenance fix, with no result-driven candidate replacement.
- A recovery checkpoint records proof that shard 2 was never reserved/submitted,
  marks that shard pending, and retains shard 1's provider ID. Resume config:
  `configs/amazon_validation_batch_resume.yaml`; no generation is repeated.
- Frozen-test gates and policy analysis are implemented and tested, but no final
  freeze, test generation or test score exists yet. Selection grid was committed
  before expanded validation outputs at `d672712`. Latest checks: 81 tests pass.

## Checkpoint: 2026-09-24 01:20 UTC

- Active validation scheduler: `logs/20260924_005558_amazon_validation_batch_resume`.
  It resumes the first provider batch; shard 2's pre-submit failure is documented
  without duplicate reservations. At 01:19, 18/48 shards were collected, two
  submitted, and 28 pending. Known campaign USD 3.958511; accounted USD 4.3468392
  includes pending reservations and the pilot's USD 0.0035016 unknown attempt.
  Never interpret pending reservations as already invoiced spending.
- Completed input bundles: policy at `logs/20260924_004459_amazon_policy_matrix_prepare`
  (2612 physical requests, estimate USD 2.9788, upper 3.5054); sequence validation
  at `logs/20260924_005821_amazon_sequence_validation_prepare` (6842, estimate
  7.7100, upper 9.0894); category control at `logs/20260924_010156_amazon_content_control_prepare`
  (956, estimate 1.4860, upper 1.6787). These three generation phases have **not**
  started. Configs `amazon_policy_batch.yaml`, `amazon_sequence_validation_batch.yaml`
  and `amazon_content_control_batch.yaml` are ready. Do not concurrently launch
  independent batch schedulers against the shared provider enqueue allowance.
- The category control selects all 350 warm validation user states plus 128
  cold states, with one request/user before grouping. Analyze the groups, not an
  unweighted population estimate. R4/S4 input tokens match exactly on all 478
  requests. S4 permutes candidate/category alignment only and retains history.
- Same-sample conventional comparison: `logs/20260924_010938_amazon_validation_baselines`,
  source `7e1fbf5`; sequence minus KNN NDCG +0.002167 [0.000173, 0.004190], 3318
  users including 418 cold targets. This supersedes a prior zero cold-count
  metadata omission; quality numbers did not change. See the M3 baseline report.
- Public pilot outcomes and real usage are in `artifacts/published/pilot_v1`.
  `logs/20260924_011719_pilot_archive_reanalysis` reproduced every analysis value
  exactly without raw data, credentials, models or API access. Small frozen
  base weights are also checked in. Ten archived/model file hashes were checked
  against Git blobs; artifact newline conversion is disabled for portability.
- Long-lived scheduler runtime source is parent commit `453746d`. Its child
  manifests can show later filesystem commits while their Python functions
  remain imported from the parent. `run_family_provenance.json` records this
  distinction without changing old manifests. New schedulers explicitly carry
  parent runtime provenance into child manifests.
- Routing, final freeze, final test and synchronous serving audit remain
  unexecuted. The serving audit plan fixes 128 validation users, concurrency one,
  no output reuse, automatic prefix caching recorded, and a USD 2.5 cap. Main
  random seed is 1729; secondary seeds and exact randomized-policy expectations
  are declared before expanded LLM validation quality is inspected.
- Next: collect the complete validation matrix, then analyze all users. Run the
  policy label phase to assess/fit routing if supported, execute the content and
  sequence controls, freeze all choices, and only then prepare final test inputs.
  No external input or new authorization is currently required.

Reproduction follow-up: an isolated environment without the OpenAI package found
a 1.39e-17 discrepancy in two zero-history mean fields. Group aggregation now
sorts request IDs. Archive verification keeps all counts/structure exact and
declares a 1e-14 absolute floating tolerance; it rejects looser tolerances above
1e-12. The earlier exact-match run remains valid historical evidence, but is not
claimed as a cross-process guarantee. Predictions, paired intervals and conclusions
are unchanged. The isolated rerun passes after this correction.

## Checkpoint: 2026-09-24 01:43 UTC

- PR [#3](https://github.com/WItaZhang/agentic-rec/pull/3) passed both CI jobs and
  merged as `958b145`. New branch `codex/validation-study-results` starts there;
  `d64d6f9` adds prespecified final conventional baselines on their own candidate
  pools. Neither final input preparation nor final scoring has occurred.
- The main validation scheduler remains active: 34/48 shards collected at the
  latest inspection. It still uses parent runtime commit `453746d`; no active
  input, candidate, inference setting, or reservation was changed.
- Subsequent batches will reserve/settle a complete shard with one locked ledger
  scan and durable append, avoiding a full growing-ledger scan per request.
  Denial writes no reservations; wrong-owner/duplicate settlements fail closed;
  all measured overages are recorded before stopping. Existing ledger format,
  campaign caps and interrupted-call reservations are preserved. 93 tests and
  Ruff pass. This does not change model inputs or paid-call selection.
- Next remains complete-matrix analysis, necessary policy/content/strong-base
  controls, validation-only selection, then a frozen final test and resource
  audit. No current external blocker or request for additional budget exists.

The token-matched content control is queued in local execution session `67329`.
It waits for the validation scheduler's completed manifest and starts
`configs/amazon_content_control_batch.yaml`; a failed parent prevents launch.
Estimated USD 1.486, upper USD 1.679, round cap USD 2. Do not independently start
another scheduler while this queued process owns the next queue slot.

The post-test failure audit now separates cold/retrieval misses, lost/rescued
baseline hits, API failure and ranking repair. Case selection is deterministic
within each class and does not prefer the largest loss. It exports public product
metadata and historical ratings, no user IDs or review text, and makes no model
call. It has not run: the final test is still untouched. The serving audit also
includes the frozen causal-sequence model at zero additional API cost, under the
same request sampling, CPU and concurrency conditions as the other methods.

At `f195317`, all three frozen conventional models were evaluated on the same
3318 validation users: `logs/20260924_014748_amazon_three_validation_baselines`.
Popularity NDCG is 0.063170, KNN 0.066556, sequence 0.068723. KNN minus
Popularity is +0.003385 [0.000663, 0.006196]; the earlier KNN/sequence comparison
reproduces exactly. Include both Popularity and causal_sequence in the final
freeze's additional_baselines dictionary, and in the serving audit template.
These are separate candidate pools, not evidence-routing effects.
