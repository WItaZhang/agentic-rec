# Research execution checkpoint

Last updated: 2026-09-25 UTC. The full research goal remains active. The newest
checkpoint is at the bottom; historical spending/status entries are not current balances.

## Authorization and resources

- Branch: `codex/evidence-results`; repository default:
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
