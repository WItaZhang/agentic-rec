# Research execution checkpoint

Last updated: 2026-09-30 UTC. The full research goal remains active. The newest
checkpoint is at the bottom; historical spending/status entries are not current balances.

## Authorization and resources

- Branch: `codex/robustness-analysis`; repository default:
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
| M3 fixed evidence | complete primary validation; controls running | `72deac0`, `d8b22f6`; [complete validation](../../reports/20260925_m3_evidence_validation/README.md) | R1 overall gain unestablished; R4 −0.026559 NDCG with negative paired interval. History-state directions differ. |
| M4 routing | fitted and validation analyzed | `4ee41e1`, `adc13e6`; [routing report](../../reports/20260930_m4_routing_validation/README.md); `configs/amazon_routing_development_v2.yaml` | Primary selected validation actions all R0; secondary quality preservation unestablished. Four model hashes and every validation action reproduce offline. Practical selection: causal sequence model. |
| M5 sequential evidence | conditional | No implementation claimed | Only pursue if observations after fetching evidence can improve a decision. |
| M6 final test/report/materials | immutable freeze and target-free inputs complete; test ungenerated/unscored | `artifacts/frozen_protocol/v1`; `logs/20260930_211006_amazon_final_test_prepare` | Finish diagnostic controls without changing selection, then final test, serving/resource audit and final materials. |

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

`configs/amazon_deployment_selection_v1.yaml` records the whole-system adoption
rule before the expanded LLM validation matrix is inspected. Under the already
registered USD 0.25/1000 primary budget, compare all three conventional models
with the validation-selected fixed/rule/learned policies; among candidates within
0.002 NDCG of the best, prefer lower API spending then simpler methods. Local
compute is reported separately. This keeps the practical method choice separate
from the scientific learned-vs-rule comparison on fixed KNN candidates. The
tolerance is a selection rule, not evidence of noninferiority. Final test does
not trigger reselection or retuning.

Queue amendment for **unsubmitted** policy, sequence and content phases: maximum
shard input decreases from 800,000 to 300,000 tokens; total enqueue allowance
remains 1,800,000. The current validation batch at offset 4786 had 148/149
provider-completed requests for over ten minutes, occupying almost half the
queue while one request waited. Smaller future shards reduce the capacity tied
up by stragglers. Inference payloads, sample, prices, phase caps and completed
data do not change. Batch turnaround is not compared as serving latency. The
active validation schedule is unchanged and no slow request is dropped.

PR [#4](https://github.com/WItaZhang/agentic-rec/pull/4) passed all Python 3.11/3.12
CI jobs at head `2d81448` and merged as `9e5a604` at 01:54:57 UTC. The new
`codex/evidence-results` branch starts from that merge. Full local validation is
96 tests plus Ruff; `logs/20260924_015002_pilot_archive_reanalysis` again matches
all archived numbers exactly without API access. Main validation and the queued
content phase still own execution sessions `10259` and `67329`, respectively.
The working methods/report manuscript is now under
`reports/adaptive_evidence_study/STUDY.md`; it explicitly marks unfinished results.

## Provider-tail execution plan (2026-09-24 02:10 UTC)

Validation shard 33 remains at 148/149 completed for roughly half an hour; other
shards continue. To avoid serializing all independent work behind this tail,
the waiting content launcher may start **only when validation has no pending or
submitting shards and at most 800,000 submitted input tokens**. Its overlap
config then caps its own queue at 1,000,000 tokens. Thus both processes together
remain at or below the existing 1,800,000 allowance, and the older scheduler has
no work left to submit. If validation completes normally first, use the original
content config. No request is cancelled, excluded or resubmitted. The content
study is independent of unfinished validation quality and was specified from
the pilot before any expanded matrix analysis.

The original waiting launcher (session `67329`, PowerShell PID 25896) has not
started paid work at this checkpoint. Replace that task-owned waiting process
with the guarded launcher; never run both. Once content starts, do not launch a
third scheduler until its phase is complete. Budget estimate/cap remain unchanged.

Execution follow-up: the verified waiting process was stopped with no child
generation process or content run present. Its old session `67329` exited.
The replacement guarded launcher is session **`22026`**. Validation's delayed
shard completed all 149 requests at 02:09:53; nothing was cancelled, omitted or
retried. At 02:13, 45/48 validation shards were collected, two submitted and one
pending. The main session remains `10259`.

At `00ddcd8`, batch execution, matrix evaluation and router-data loading also
verify saved run configuration hashes, including temperature/output settings
that do not affect a token-count prompt hash. All four prepared source configs
passed this check. At `3928a95`, controller fitting saves compact derived
feature/quality/cost/inclusion-weight matrices and can refit from their verified
archives without raw reviews, models or API access. That refit pathway is tested
but has not yet run on completed expanded labels. Latest full local suite:
**98 tests and Ruff pass**. Repository Markdown relative-link check also passes.

## Checkpoint: 2026-09-25 resumed execution

- Prior sessions `10259` and `22026` are no longer live. Inspection confirms the
  main validation scheduler **completed all 48 shards**, with zero pending ledger
  reservations. The queued content phase had never started; it was not rerun.
  Campaign known cost before the new content phase is USD 8.8644768; accounted
  USD 8.8679784 includes only the pilot's USD 0.0035016 unknown settled attempt.
- Complete evaluation: `logs/20260925_071030_amazon_validation_matrix_evaluate`
  (`72deac0`); paired/group analysis: `logs/20260925_071120_amazon_validation_evidence_analysis`
  (`d8b22f6`). The 6842 physical generations cost USD 7.7131224; all usage known.
  R1 minus R0 NDCG +0.000612 [−0.002067, +0.003260]; R4 minus R0 −0.026559
  [−0.032734, −0.020497]. All 3318 users and 1480 retrieval misses remain.
- R1 gains slightly for empty histories but loses for at-least-two-event histories.
  Grid **v2** adds `recent_if_no_history` and `recent_unless_older` before router
  fitting/final test, to avoid a weak history-only rule comparator. It preserves
  v1 learner settings, penalties, budgets, primary test comparison and margin.
  This is explicitly validation-informed development, not a pre-observation rule.
  Use `configs/amazon_routing_grid_v2.yaml` for fitting and final freezing.
- Published outcomes/usage: `artifacts/published/validation_v1`.
  `logs/20260925_071447_validation_archive_reanalysis` reproduces all numeric
  statistics exactly without dataset, credentials or model access.
- **Live content scheduler session `37995`**: `logs/20260925_071014_amazon_content_control_batch`,
  normal 1.8M-token queue, 25 shards. Expected USD 1.486, maximum 1.679, cap 2.
  It started from runtime commit `64fa0c2`; child provenance records the parent.
- **Queued policy launcher session `79485`** waits for that content manifest to
  finish, then runs `configs/amazon_policy_batch.yaml`. Estimate USD 2.979, upper
  3.505, cap 6. Do not start another independent scheduler. Sequence validation
  is still prepared but unsubmitted. No final freeze/test or router fit exists yet.
- Next: analyze the content control when complete, collect/fit the policy labels,
  execute strong-retriever evidence robustness, freeze validation-only choices,
  run final test and controlled serving/failure/resource audits, finish materials.


## 2026-09-25 UTC: equal-token control complete; policy labels running

- Content execution `logs/20260925_071014_amazon_content_control_batch` completed all 25 shards / 956 calls. Every R4/S4 pair has equal actual input token counts; actual total USD 1.4859628. All returned the dated model. Report: [content control](../../reports/20260925_m3_content_control/README.md).
- Evaluation `logs/20260925_072306_amazon_content_control_evaluate` (`771f8a6`); analysis `logs/20260925_072335_amazon_content_control_analysis` (`f8630c8`). R4 minus S4 NDCG +0.022272 on the enriched diagnostic sample, but signs differ by history. R4 minus base −0.025280. No population gain or neutral-padding claim.
- Public archive `artifacts/published/content_control_v1`; offline reanalysis `logs/20260925_072511_content_control_archive_reanalysis` reproduced every number exactly, no dataset/API/model access.
- At content completion known campaign API cost USD 10.3504396, accounted USD 10.3539412 including the old uncertain 429 reservation. This is a historical snapshot; policy calls are now adding cost.
- LIVE: policy scheduler `logs/20260925_072230_amazon_policy_batch`, exec session 79485, source `f940975`, 49 shards. No duplicate submission. Estimated USD 2.9788184, upper USD 3.5053976, round cap USD 6.
- QUEUED: exec session 69278 waits for that policy scheduler to complete all shards, then launches `configs/amazon_sequence_validation_batch.yaml`. Expected USD 7.7100102, upper USD 9.0893574, cap USD 12. This estimate was communicated before execution. Do not independently submit it while the launcher lives.
- Added a deterministic executable adoption-selection stage for the already registered `amazon_deployment_selection_v1.yaml`; it will choose among all conventional and selected routed methods on the same validation requests. The final freeze can hash this decision, preventing later test-based reselection. No selection has been run yet.
- Next: evaluate complete policy matrix, fit the unchanged v2 grid, analyze selected validation routes and verify offline refitting. Finish strong-base evidence control, then freeze practical method + final-test protocol. Final test remains unscored.


## 2026-09-25: provider billing hard limit — recovery checkpoint (current)

- PR [#5](https://github.com/WItaZhang/agentic-rec/pull/5) merged at `a8dd7e7b06ee38948d75e6587f170f76f6b2e44d`; exact-head Python 3.11/3.12 CI, 101 local tests and Ruff passed. Current working branch is `codex/routing-final-study`.
- Policy scheduler `logs/20260925_072230_amazon_policy_batch` failed during shard 12 (zero-based) creation. The initial error type was BadRequestError; provider batch listing found no matching created batch. Reusing the same uploaded file and reservations returned explicit HTTP 400 / `billing_hard_limit_reached`. This is a provider billing block, not project-budget exhaustion. A popup asks the user to restore provider capacity. No new paid request should be launched before that condition is resolved.
- Sessions 79485 (policy) and 69278 (waiting sequence launcher) have exited. The strong-sequence comparison **never started**. No experiments or paid reservations are currently pending.
- The last already accepted batch completed 50/50 and was collected in `logs/20260925_073041_amazon_policy_batch_billing_collect` (`4fe109f`). Expanded policy matrix: 641/2612 physical calls completed, 1971 left. Never fit or score a partial counterfactual matrix.
- `eaea6b0` distinguishes explicit Batch billing rejection before generation from ambiguous errors. The 56 rejected reservations are settled at zero, with a rejection record and no invented token usage; uncertain network errors still retain their reservations. `3fe7d85` preserves standalone recovery-collection CPU in the resource audit.
- Durable checkpoint: `logs/20260925_073228_amazon_policy_billing_checkpoint`. The original failed scheduler and error records remain intact. Resume config: `configs/amazon_policy_batch_resume_after_billing.yaml`; it preserves 12 collected shards, then resumes at offset 641. After provider recovery, expected remaining phase USD 2.2477996, upper USD 2.6451532; original phase cap USD 6 remains.
- Latest reconciled resources: `logs/20260925_191002_amazon_interim_campaign_resources`, source `3fe7d85`; [report and blocking evidence](../../reports/20260925_resource_checkpoint/README.md). Known USD 11.0814584, conservative accounted USD 11.0849600 including the old unknown 429. Authorization remaining USD 38.9150400. Actual observed 54,402,912 input / 342,936 output / 4,206,848 cached input tokens. 9526 observed generations + one uncertain pilot attempt; 56 pre-generation rejected requests are separate.
- [Career drafts](../../reports/career_materials/README.md) now contain an evidence-backed English LaTeX snippet and bilingual interview explanation. They explicitly state development status and exclude unverified adaptive gains, final-test performance and multistep capabilities.
- Remaining sequence after account recovery: resume policy labels → complete evaluation → fit v2 grid → selected validation analysis + offline refitting → strong-base evidence study → validation-only practical method selection → freeze (including popularity and sequence extra baselines) → final test and final analyses → controlled serving audit → campaign resources/final report/career revisions.
- The research objective is not achieved. Missing external condition is account billing capacity, not additional code permission. The goal has not been marked complete or paused.


## 2026-09-25: zero-cost validation failure analysis while billing is unresolved

- Previous goal turn classified as progress: PR #6 merged as `1219777`, accounting and recovery checkpoint preserved. This continuation rechecked a clean worktree, merged PR state and absence of Python experiment processes. The user's provider-capacity response is still pending; no paid probe or submission was made.
- New implementation `994cedc` adds development-only fixed-action failure diagnostics while retaining the separate frozen final-test gate. It rejects partial/test/stratified matrices and does not substitute incomplete policy labels.
- Actual zero-call run `logs/20260925_191516_amazon_validation_failure_analysis` on all 3318 population-validation requests. [Report and deterministic cases](../../reports/20260925_validation_failures/README.md): R4 loses 388 base hits and rescues 196; R1 loses 38 and rescues 49. About 44.6% of each counterfactual single-action API cost is on unrecalled targets. These labels are diagnostic only, never policy features.
- Working study and interview drafts now include these observed failures. Grid v2, prompts, final comparison and group boundaries are unchanged. Final test remains unscored.
- Same provider billing blocker has persisted across two goal turns. Expanded policy labels remain 641/2612; no new cost, no running session, no pending paid reservation. The exact resume config remains `configs/amazon_policy_batch_resume_after_billing.yaml`. Await restored provider capacity before dependent work.


## 2026-09-30: billing restored; existing policy run resumed

- User confirmed restored provider billing capacity. New Batch submissions are accepted; the previous hard billing blocker is resolved. The original USD 50 authorization and USD 45 planning stop remain unchanged. No credentials are published.
- Current branch `codex/resumed-routing-study`, starting commit `8290a8f`. No uncommitted third-party changes or open PRs were found; PR #7 is already on the remote default branch.
- Running scheduler `logs/20260930_202213_amazon_policy_batch_resume_after_billing`, runtime commit `8290a8f`, session 25501. Config `configs/amazon_policy_batch_resume_after_billing.yaml` preserves all 12 collected shards / 641 physical outputs and starts at offset 641. Do not submit a duplicate scheduler.
- Before dispatch, remaining 1,971 requests were estimated at USD 2.2477996 with conservative maximum USD 2.6451532. Prior accounted cost USD 11.0849600; policy phase cap remains USD 6. Official dated-model pricing and Batch 50% discount were rechecked, unchanged, in `logs/budget/billing_resume_price_recheck_20260930.json`.
- Next: collect the complete policy matrix, fit registered grid v2, analyze validation choices and verify offline refitting. Then finish the strong-sequence evidence comparison and freeze the practical selection and final-test protocol. The final test is still unscored.

- Sequence launcher session 15821 waits for the above policy manifest to complete, then executes `configs/amazon_sequence_validation_batch.yaml`. Expected USD 7.7100102, maximum USD 9.0893574, cap USD 12 were communicated before queuing. Do not launch another sequence scheduler.
- `configs/amazon_final_protocol_plan_v1.yaml` records full test-user census, the unchanged registered analysis/selection rules, both extra conventional baselines and a USD 12 final phase cap before any test input preparation. Completed routing/deployment paths must be bound at actual freeze.

- Added the design's candidate-presentation robustness control before final freezing: `configs/amazon_presentation_control_prepare.yaml` uses the same 3318 validation users and fixed candidates, R1/R4 evidence, a shared per-request row permutation (seed 8675309), and unchanged aliases/schema. Original base rank remains available through candidate IDs; this isolates sensitivity to row order while retaining the base prior, not removal of prior information. Only the order annotation changes in addition to row order; token counts and output variation are reported. This exploratory control cannot select a new prompt/router or alter the registered primary comparison. Preparation is unbilled token counting; paid dispatch requires a separate preflight under the remaining campaign budget.

- A subsequent **file-upload APIConnectionError** interrupted the scheduler on shard 20 before Batch creation. It is unrelated to billing. Provider listing (94 batches) found no matching Batch. `be3311a` adds tested reconciliation using the existing payload, pending reservations, exclusive durable recovery intent and original idempotency key. Recovery `logs/20260930_202853_amazon_policy_upload_recovery` accepted all 56 reserved inputs; the original failed manifest/error remain intact. No generation was repeated.
- Replacement checkpoint `logs/20260930_202912_amazon_policy_upload_checkpoint` (source `54d41c7`); active scheduler `logs/20260930_202922_amazon_policy_batch_resume_after_upload` (source `539700f`), session **54324**. Queued sequence launcher now **98719**, waiting on this replacement parent; earlier sessions 25501/15821 exited. Resume config `configs/amazon_policy_batch_resume_after_upload.yaml`.
- Unbilled presentation preparation is running as `logs/20260930_202629_amazon_presentation_control_prepare`, session **87454**, source `66b0d46`. No presentation generations have been submitted.

- A second file-upload-only connection failure on shard 26 used the same recovery path (`logs/20260930_203245_amazon_policy_upload_recovery_s026`, 52 existing reservations). Active scheduler is now **`logs/20260930_203300_amazon_policy_batch_resume_s026`**, source `f37f7ba`, session **52252**, resume config `configs/amazon_policy_batch_resume_s026.yaml`. Prior scheduler/sequence waiting sessions 54324/98719 exited. Sequence has still not started and will be dispatched after this complete policy collection. No provider-billing recurrence.
- PR #8 records these recovery stages and row-order sensitivity implementation. Full local verification: 108 pytest tests plus Ruff passed before the final test-freeze guard was added to upload recovery; focused guards rerun below.


## 2026-09-30: infrastructure recovery and validation reporting

- PR #8 merged at `4125815` after exact-head Python 3.11/3.12 CI and no unresolved reviews. Local 108 tests + Ruff passed; the final recovery freeze guard passed focused tests. The existing validation archive reanalysis reproduced all statistics exactly and now includes a visually checked subgroup-effect figure. No new quality results are inferred from these figures.
- Third file-upload-only connection interruption: shard 41 recovered in `logs/20260930_203917_amazon_policy_upload_recovery_s041` (53 original reservations), checkpoint `logs/20260930_203922_amazon_policy_upload_checkpoint_s041`. Active policy scheduler **`logs/20260930_203956_amazon_policy_batch_resume_s041`**, source `af7a19e`, session **40151**; confirm the exact timestamped directory in `logs` before restarting. Resume config `configs/amazon_policy_batch_resume_s041.yaml`. No generation retries or additional reservations for these recoveries.
- Because upload connectivity recurred, the unstarted sequence scheduler now explicitly allows up to 20 infrastructure recoveries with 5-second backoff. Recovery is restricted to pre-creation `file_upload`/`APIConnectionError` with no HTTP status, reconciles provider metadata and keeps original reservations. Batch-creation ambiguity and generation errors still stop. The generator's zero-retry setting, candidate inputs, model and costs are unchanged. This is a transport reliability adjustment before sequence dispatch, not scientific tuning.

- Complete policy labels evaluated at `logs/20260930_204324_amazon_policy_matrix_evaluate` (`5aa4978`): 1045 users, 2612 physical calls / 4180 logical outcomes, 14,517,964 input + 94,032 output tokens, USD 2.9788184, no unknown usage. Enriched training-cohort metrics are not population estimates.
- Actual v2 fit `logs/20260930_204405_amazon_routing_development_v2` (`4ee41e1`), inverse-inclusion weighted. Under the registered tolerance, budgets 0–0.5 select all-base policies; the primary USD 0.25 comparison therefore collapses to identical actions on validation. At budget 1.5, selected learned quality 0.068006 / USD 0.04418 per 1000 versus rule 0.068681 / USD 0.63689. These are development-selected values, not final proof of cost savings with preserved quality.
- All registered budget points now receive explicitly exploratory paired learned/rule and learned/random intervals. This does not replace the primary comparison or alter grid v2. Constant paired vectors use their exact degenerate bootstrap distribution, retaining the guard against claiming noninferiority from degenerate comparisons.
- Strong-base evidence scheduler is live: `logs/20260930_204341_amazon_sequence_validation_batch`, source `5aa4978`, session 60842, 127 shards. Its first infrastructure upload recovery succeeded using the bounded mechanism. Presentation count preparation remains session 87454.

- M4 validation analysis: `logs/20260930_204625_amazon_routing_validation_analysis` (`adc13e6`), with primary and exploratory budgetwise intervals, allocation/group/cost plots. Report `reports/20260930_m4_routing_validation`. Primary validation decisions are identical all-base; at envelope 1.5 quality preservation vs the rule is unresolved (one-sided lower -0.002205 < -0.002). No primary comparison was changed.
- Public training matrices `artifacts/published/routing_training_v2` and deployment artifacts `artifacts/frozen_router/v2` preserve the actual fit. `logs/20260930_204717_amazon_routing_archive_refit` (`c02adbd`) reproduced four estimator hashes and all 25 policies' validation actions exactly; only measured inference runtime is excluded from selection-JSON equality.
- Actual registered practical selection: `logs/20260930_204723_amazon_deployment_selection` (`c02adbd`), **causal_sequence**. Freeze must bind `routing_run: artifacts/frozen_router/v2` and this completed deployment-selection run, preserving portability and the selected model. Strong-base/presentation controls must finish before final freeze; test remains unscored.
- Policy archive published at `artifacts/published/routing_validation_v2`; publication run `logs/20260930_204924_publish_routing_validation_results` (`2e43f90`). Offline statistical reanalysis is running; record its result before declaring archive verification complete.


## 2026-09-30: M4 reproducibility verified; bounded sequence queue recovery

- Offline policy outcome reanalysis `logs/20260930_204927_routing_validation_archive_reanalysis` (`2e43f90`) completed; every statistical field matches the published policy archive exactly (maximum absolute numeric difference zero). The public matrices, four fitted models, report and figures are ready for review.
- Full verification after queue recovery and paired-statistic changes: **127 pytest tests and Ruff pass**. No final-test labels were read for these changes.
- Original sequence scheduler `logs/20260930_204341_amazon_sequence_validation_batch` stopped because shard 23 was rejected by the provider's 2M enqueued-token cap. Its receipt explicitly records failed validation, no generation start/output files, zero request counts and zero batch input/output usage. All four previously accepted outstanding shards subsequently completed. No capacity purchase or new permission is needed.
- Recovery code `86010c8` requires that exact provider evidence and immutable shard bindings before releasing only the 52 unexecuted reservations (USD 0.0715056). Original unknown-result records and ledger events remain intact; recovery adds proof, records zero generation attempts without fabricating per-request token measurements, and is idempotent after interruption.
- Recovery checkpoint `logs/20260930_205929_amazon_sequence_queue_checkpoint` lowers only queued input allowance from 1.8M to 1.2M. Resume `logs/20260930_205938_amazon_sequence_validation_batch_resume_queue` (`effad47`), session **52809**, preserves every accepted/collected shard and requeues shard 23 once. Config `configs/amazon_sequence_validation_batch_resume_queue.yaml`. Do not launch a second Batch scheduler.
- After collecting the previous accepted shards, known campaign cost was **USD 14.7910646**, conservative accounted **14.7945662** including the older unresolved pilot reservation. This is a historical snapshot; remaining sequence calls continue to add cost. Whole sequence estimate/cap remains USD 7.7100102 / 12; no scientific input or generation retry policy changed.
- Presentation preparation `logs/20260930_202629_amazon_presentation_control_prepare`, session 87454, remains unbilled token counting. Paid presentation execution must wait for sequence completion and an exact full-phase preflight. Then analyze both controls, freeze the already selected sequence method plus registered routing comparisons, and run the untouched final test and serving audit.

- PR [#9](https://github.com/WItaZhang/agentic-rec/pull/9) merged at `9698a04` after exact-head Python 3.11/3.12 CI, 127 local tests, Ruff and no unresolved reviews. Twelve public archive files were also checked against their actual committed Git blob hashes. Current work continues on `codex/final-controls`; this milestone does not complete the research objective.

- Before either remaining control is scored, `ada4acf` adds paired retriever-sensitivity analysis: compare each action relative to its own frozen base, then compare those differences across the same users. It reads completed published development archives and retains cold/retrieval misses. Cross-retriever effects include changed candidate membership/order and are explicitly not pure evidence or routing gains. `configs/amazon_retriever_robustness.yaml` fixes all plans and existing history boundaries.


## 2026-09-30: final selection freeze and label-free preparation ordering

- Presentation preparation completed all 6,636 physical inputs / 36,481,625 input tokens. Before queuing paid execution: expected USD **7.4874418** using the earlier observed 36-token output length, conservative maximum **8.8252594**, configured cap **9**. Queue launcher session **38021** waits for the complete sequence scheduler, then runs `configs/amazon_presentation_control_batch.yaml`; it exits without dispatch if the predecessor fails. No parallel Batch scheduler is permitted.
- Planning adjustment before test access: freeze the completed validation choices now, while the remaining diagnostic controls run. Their declared purpose is sensitivity analysis, not selecting a different prompt, grid or deployment candidate. This is stricter about subsequent adaptation and permits slow, target-free input preparation in parallel. **Final paid generation and scoring still wait for completed control analyses.** The earlier planning template is preserved; `configs/amazon_final_freeze.yaml` records the changed execution order and rationale. No test labels have been scored.
- The actual registered adoption decision is preserved byte-for-byte in `artifacts/frozen_selection/v1`; the final freeze binds it and `artifacts/frozen_router/v2` for portable reproduction. All existing final parameters, full-user-census sampling, primary budget/comparison, 0.002 tolerance and conventional baseline fingerprints are unchanged.
- Current source tests: 129 pytest tests and Ruff pass. No sequential acquisition/stopping implementation or positive routing effect is inferred from these changes.

- Immutable final freeze completed at `logs/20260930_210942_amazon_final_protocol_freeze` (`dfc5836`), published byte-for-byte under `artifacts/frozen_protocol/v1`. Its executable config relocates only the freeze reference and passed the full frozen-field verification. Final target-free preparation is **`logs/20260930_211006_amazon_final_test_prepare`**, source `90f61f3`, session **23408**: census of **3572 users**, one predetermined request per user from 4012 eligible events. No test generations or quality scores exist yet. Source config `configs/amazon_final_test_prepare.yaml`.

- PR [#10](https://github.com/WItaZhang/agentic-rec/pull/10) merged at `2202db5` after exact-head Python 3.11/3.12 CI and no unresolved review threads. `e3bd18c` verifies the actual public freeze on Linux without private logs/credentials and resolves historical Windows path separators without changing frozen bytes. Prompts now preserve their hash-bearing bytes on checkout. Current branch `codex/control-results`.
- Checkpoint at 2026-09-30T21:15:48.878053+00:00: sequence shards {'collected': 49, 'submitted': 4, 'pending': 74}; final target-free preparation running. Known usage-priced API USD 16.3138580; accounted including pending/unknown reservations USD 16.6068006 against USD 50. These are running snapshots, not final campaign totals. Live sessions remain 52809 (sequence), 38021 (queued presentation), 23408 (final preparation). No final generation or quality scoring has started.


## 2026-09-30: final inputs complete; full remaining-cost forecast

- Previous continuation made concrete progress: M4 publication and two checked PR merges, proven zero-generation queue recovery, immutable validation-only freeze, and real target-free final preparation. This continuation confirmed sessions 52809/38021/23408 live before further work; no process was restarted based only on a state file.
- Final preparation **completed** at `logs/20260930_211006_amazon_final_test_prepare` (`90f61f3`): all 3572 users, 14288 logical action inputs, **7460 physical calls**, **41007040 provider-counted input tokens**. Candidate, route, extra-baseline and call-bundle hashes were rechecked. No generation or test quality scoring occurred.
- Final dispatch config `configs/amazon_final_test_batch.yaml`: estimate **USD 8.416256**, conservative reservation maximum **9.920192**, round cap **12**. The gate remains completion/analysis of both diagnostics; do not launch it while the other Batch scheduler is running. Preflight `logs/budget/final_preflight_20260930.json`.
- Bound serving config `configs/amazon_serving_audit.yaml` preserves the registered 128 validation users, eight methods, concurrency 1, two CPU threads, automatic provider-prefix cache accounting, no application output caching, and unchanged timeout/retry limits. Its target-free plan is 1024 requests / 256 LLM generations, 1404971 input tokens; expected uncached **USD 0.576734**, maximum **0.6799532**, existing cap **2.5**. This is an estimate, not a latency result. Run after other CPU-intensive experiment work.
- Using the accounted pre-sequence subtotal USD 13.3327596, plus entire sequence/presentation/final/serving phases (never adding paid portions twice), projected campaign total is **USD 37.5232016** at estimated output lengths, or **USD 41.8475216** at conservative maxima. This includes the old uncertain pilot reservation and is below the USD 45 planning stop / USD 50 authorization. Ledger guards still apply to every actual call; these estimates are not invoices.
- Sequence and queued presentation handles remain 52809 and 38021. No further permissions or funds are needed at this checkpoint. No final conclusion is inferred from unscored inputs.

- Updated the interim English LaTeX project excerpt to include completed weighted routing, and saved a standalone `reports/career_materials/resume_preview.tex` with an explicit development-stage notice. The native editor open was queued; its compiler returned `Unable to find standard directories for platform` before a source diagnostic. Source and diagnostic are preserved, no PDF or successful compilation claimed. This tool-environment limitation does not block actual recommendation experiments. Recheck when finalizing the source; do not install a TeX distribution as a workaround.


## 2026-09-30: operational costs and offline accounting verified

- `247f211` adds deduplicated token-preflight, local evidence-access and rank-repair accounting, plus upload/collection/recovery receipts and incremental scheduler polling. It rejects a ledger that changes mid-audit; the snapshot excludes its own mutable manifest. Partial coverage is reported explicitly while a collected matrix has not yet been evaluated. In-memory evidence bundles are not called external HTTP tools.
- Real interim audit `logs/20260930_212917_amazon_interim_campaign_resources` validated the counters. `57e9ec8` then introduced a sanitized accounting archive; replay `logs/20260930_213527_amazon_accounting_replay_checkpoint` reproduced all fields exactly without raw data, credentials or network calls.
- `f5c494b` independently reprices each observed generation using its frozen standard/Batch prices, including cached-input billing. Audit `logs/20260930_213606_amazon_interim_campaign_resources` verified **16102 observed calls with zero per-call discrepancy**. Historical known USD **18.5115102**, accounted **18.8006378** with 210 pending and one unknown settled request. The 108 proven pre-generation rejections are separate; no zero-token usage was invented.
- Published [resource snapshot](../../reports/20260930_resource_checkpoint/README.md) and sanitized archive `artifacts/published/resources_checkpoint_20260930`; replay `logs/20260930_213718_resource_checkpoint_archive_replay` (`124a614`) has maximum numerical difference **zero**. Its config is `configs/resource_checkpoint_archive_replay.yaml`. This is explicitly interim, not a final resource total; final audit still requires no pending/running experiment.
- Latest local verification: **136 tests and Ruff pass**. The published accounting replay is now also a Python 3.11/3.12 CI check. Prompt, model, utility grid, group thresholds, quality tolerance and final selection remain frozen and unchanged.
- The standalone English excerpt source is saved, but the native compiler's platform-directory error still prevents verified compilation. The optional preview does not block research execution; no compiled PDF is claimed.


## 2026-09-30: robustness results continuation

- PR [#11](https://github.com/WItaZhang/agentic-rec/pull/11) merged at `fd9149f` after exact-head Python 3.11/3.12 CI, including public accounting replay, and no unresolved review issues. Current branch `codex/robustness-results`.
- Revalidated the original sequence scheduler (session 52809) and queued presentation launcher (38021); both remain live. No duplicate process was started. Final preparation is completed and frozen; no final generation or scoring has run.
- The strong-retriever offline replay configuration binds the archive path already registered by the paired robustness analysis. Diagnostic findings cannot change frozen final choices.

- At 22:06 UTC, the original sequence run had 126/127 shards collected; shard 119 had 50/51 provider requests completed, zero failed, and remained `in_progress`. The last unfinished request is retained; the scheduler and queued presentation launcher are alive. No duplicate generation or partial-matrix evaluation is authorized by this checkpoint.
- Label-free inspection of the immutable final decisions confirms all 3,572 primary-budget learned/rule/random/fixed decisions are R0. At secondary envelope 1.5, the learned policy assigns 3,329 R0 / 96 R1 / 96 R2 / 23 R3 / 28 R4; these are already frozen inference decisions, not test-quality findings. The primary comparison will retain its degenerate-result guard; no policy is retuned to force activity.
- Latest checkpoint `logs/CURRENT_CHECKPOINT.json` binds active handles, fresh ledger totals, final-input location and frozen action counts. Presentation dispatch remains automatic only after complete sequence collection. Next concrete step: evaluate the completed sequence matrix, publish/reanalyze its derived archive, then run the registered cross-retriever paired sensitivity analysis.


## 2026-09-30: bounded overlap around one slow provider tail

- Direct provider listing confirms the only active Batch is the known 51-request sequence shard, with 50 completed / zero failed. Every sequence shard has already been submitted, so its remaining queued input can only decrease. Waiting on one slow asynchronous request was blocking independent diagnostics.
- Stopped queued launcher session 38021 (exit 1 from explicit interrupt) before any presentation directory or child dispatch existed. It must **not** be resumed. The original sequence scheduler 52809 remains untouched, retaining the final request and its reservation.
- New unstarted config `configs/amazon_presentation_control_batch_overlap_tail.yaml` lowers presentation inflight input to 900,000. Together with the entire outstanding sequence shard (299,596 tokens), aggregate queued input is at most **1,199,596**, below the already adopted 1.2M cap. Provider listing, local state guard and cost preflight are saved in `logs/budget/presentation_tail_overlap_preflight.json`.
- Presentation input, models, seeds, budget and generation retries are unchanged: expected USD 7.4874418, maximum 8.8252594, cap 9. Only submission scheduling changes. This replaces the earlier single-scheduler gate for this bounded tail; final test still waits for both complete diagnostic analyses. No partial matrix is scored.

- Presentation dispatch is now live at `logs/20260930_220737_amazon_presentation_control_batch_overlap_tail`, runtime source `faff7ac`, session **56214**, 123 shards. One file-upload-only recovery completed with the original 55 reservations and no generation retry. The earlier queued launcher 38021 is terminal and must not be restarted. Sequence scheduler 52809 is still waiting on its retained tail.
- Added [delivery evidence audit](../../reports/adaptive_evidence_study/DELIVERY_AUDIT.md), distinguishing verified development evidence from pending final, serving and reporting work.
- Final quality-cost plotting now includes both frozen conventional baselines at zero API cost with their own-candidate-pool labels and user-bootstrap marginal quality intervals. This display-only addition does not change method selection, pairwise comparisons or frozen inference. Offline final archive reanalysis regenerates the same complete plot. Full local **136 tests and Ruff pass**; final rendering still awaits actual final outcomes.

- PR [#12](https://github.com/WItaZhang/agentic-rec/pull/12) merged as `4c1acf3` after exact-head Python 3.11/3.12 push/PR checks, 136 local tests/Ruff, and no unresolved reviews. Current branch `codex/robustness-analysis`. Live experimental handles remain 52809 and 56214; this verified running state is not an external-permission blocker or completion of the research goal.
