# Final campaign cost and real synchronous service measurements

The campaign has **no pending reservations or running experiment roots** at the final audit snapshot. Known provider usage is priced at **USD 37.3714568**; an earlier unknown pilot attempt retains its **USD 0.0035016** worst-case reservation. Total accounted expense is **USD 37.3749584**, leaving **USD 12.6250416** of the authorized USD 50. The planning stop was USD 45. No rental, additional credit purchase or paid service was added.

These are measured usage charges under the recorded model price tables, **not an invoice reconciliation**. Unknown usage is not assigned fabricated zero tokens. Campaign ledger and per-phase reductions differ only by floating summation roundoff; reported rounded dollars agree.

## Offline research and construction expense

| Phase | Observed-usage generations | Unknown-usage generations | Rejected before generation | Known USD | Accounted USD |
|---|---:|---:|---:|---:|---:|
| Synchronous feasibility | 32 | 0 | 0 | 0.069304 | 0.069304 |
| Batch feasibility | 32 | 0 | 0 | 0.036246 | 0.036246 |
| Development pilot | 1,023 | 1 | 0 | 1.045805 | 1.049306 |
| Main validation labels | 6,842 | 0 | 0 | 7.713122 | 7.713122 |
| Policy-training labels | 2,612 | 0 | 56 | 2.978818 | 2.978818 |
| Stronger-retriever validation | 6,842 | 0 | 52 | 7.710010 | 7.710010 |
| Equal-token content control | 956 | 0 | 0 | 1.485963 | 1.485963 |
| Candidate presentation control | 6,636 | 0 | 0 | 7.487442 | 7.487442 |
| Frozen final labels | 7,460 | 0 | 0 | 8.416256 | 8.416256 |
| Synchronous serving measurement | 382 | 0 | 0 | 0.428491 | 0.428491 |
| **Total** | **32,817** | **1** | **108** | **37.371457** | **37.374958** |

Before the serving audit, known research expense was USD 36.942966 (accounted USD 36.9464676). These costs include collecting all counterfactual actions and scientific controls, not merely executing the ultimately selected method. Controller label construction alone cost USD 2.9788184. Its four timed model-fit blocks used **7.9375 CPU seconds / 16.0683 wall seconds**, including first-use estimator imports; feature construction took **41.57 ms** for policy users and **100.99 ms** for validation users. The complete controller-development process used **14.1875 CPU seconds**, including selection/analysis overhead. These are overlapping scopes and must not be added together. [Fit resource record](controller_fit_resources.json).

## Measured tokens, operations and failures

- **182,255,677 input tokens**, of which **5,310,720 were cached**; **1,181,412 output tokens**. Cached tokens are a subset of input, not extra input. These totals cover the 32,817 attempts with observed usage; one pilot attempt remains unknown.
- **32,818 physical generation attempts**, plus **108 explicit pre-generation Batch rejections** = **32,926 reserved request attempts**. All resumed/collected/shared aliases deduplicate by original reservation ID. The 56 billing and 52 queue rejections have confirmed zero generation charges but no invented usage records.
- One generation failure/incomplete outcome; **208 unique physical outputs repaired or replaced by deterministic fallback**. Local validation and evidence counters cover all 32,818 generation attempts. No generation retries were used to improve outputs; upload-only infrastructure recovery is a different operation.
- **14,257 known token-count endpoint operations**: 12,819 during matrix preparation and 1,438 attached to synchronous attempts. No count-only errors or incomplete preparation count records at this snapshot.
- **82,462 local evidence-access counts** attached to generated calls: history/title/category accesses, not HTTP requests and not every offline prompt construction.
- Recorded management operations: **514 upload receipts**, **515 collection-status receipts**, **513 file downloads**, **2,026 new scheduler polls**, **61 metadata reconciliations**, **55 completed / 6 failed upload recoveries**, **56 submission-failure records**, and **one queue-recovery checkpoint**. These are overlapping categories and must not be summed as unique failed HTTP requests. Pagination, SDK transport exchanges and unmanaged provider diagnostics are not fully metered.
- Separate LLM planning, reflection, summarization and API embedding calls are **zero because those components were not executed**. Learned routing and evidence assembly run locally. The sequence model has local item embeddings; their compute belongs to base-model training, not zero-cost API embeddings.

Repricing every observed physical generation from its actual tokens and recorded standard/Batch prices matches the per-call charge exactly. The old uncertain pilot reserve is retained rather than silently cleared. The final audit includes failed runs and the Windows atomic-state recovery receipt; the recovered status poll is counted once.

## Real serving audit

The registered extended audit uses **128 validation users**, eleven methods and a fixed target-free job permutation (seed 314159). It scores no recommendation quality and reads no final-test labels. All **1,408 method requests / 382 generation attempts** completed, with **zero failures and zero ranking repairs**.

Conditions: local Ryzen 5800H CPU, two numerical-library threads, concurrency one, warm resident models, identical frozen inference settings, 60-second timeout, zero retry, 120,000 tokens/minute and 60 requests/minute. Application output reuse is disabled. Provider prefix caching is automatic and recorded; the realized cache pattern depends on this interleaved workload and cannot be assumed for different traffic. Other project training/heavy analysis was paused during measurement. Ordinary host activity was not isolated as in a dedicated benchmark server.

| Method | LLM calls / 128 | Mean service ms | P95 service ms | Conditional LLM-branch mean ms | Conditional LLM-branch P95 ms | Actual API USD/1,000 |
|---|---:|---:|---:|---:|---:|---:|
| Popularity | 0 | 1.080 | 1.582 | not observed | not observed | 0 |
| ItemKNN | 0 | 5.709 | 8.205 | not observed | not observed | 0 |
| Causal sequence, selected method | 0 | 5.023 | 8.369 | not observed | not observed | 0 |
| Recent evidence | 128 | 3,112.006 | 4,315.427 | 3,112.006 | 4,315.427 | 0.736125 |
| Full evidence | 128 | 3,229.286 | 4,403.190 | 3,229.286 | 4,403.190 | 1.897309 |
| Primary rule | 0 | 5.598 | 8.075 | not observed | not observed | 0 |
| Primary random | 0 | 5.655 | 8.234 | not observed | not observed | 0 |
| Primary learned | 0 | 6.722 | 10.350 | not observed | not observed | 0 |
| Secondary rule 1.5 | 115 | 2,785.327 | 4,104.982 | 3,099.597 | 4,135.062 | 0.634375 |
| Secondary random 1.5 | 7 | 124.506 | 1,002.769 | 2,173.782 | 2,458.540 | 0.028381 |
| Secondary learned 1.5 | 4 | 100.765 | 21.618 | 2,759.065 | 3,732.105 | 0.051394 |

The learned secondary overall P95 is below its mean because only 4/128 requests call the model. Its conditional P95 rests on **four observations**, and random's on seven: these are descriptive quantiles, not stable tail guarantees. This measurement does not establish quality preservation or a matched-cost learner-versus-random result. Its users, cache behavior and standard pricing differ from the final-test Batch quality–cost table; do not combine them into one purported observed frontier.

Service latency includes retrieval, routing/features, prompt construction, token-count requests, pacing, generation, budget-ledger bookkeeping and ranking validation. It is not just provider generation time. For recent/full methods, mean count-endpoint latency is **248.42/256.17 ms**, rate queue **330.25/482.21 ms**, and generation network/response work **1,069.27/1,139.15 ms**. The unseparated remainder after these and measured retrieval/routing/evidence components is **1,454.97/1,337.12 ms**; it includes the durable budget accounting, SDK and local validation overhead. No profile isolates all of that remainder as one cause. This research implementation is not an optimized production-serving benchmark. Per-record timings are retained in the public archive.

Actual service-audit usage is **1,844,123 input / 13,752 output / 1,103,872 cached input tokens**, USD **0.4284908**. The pre-run estimate was USD 0.7596524 assuming no cache; upper bound USD 0.9136748, configured phase cap USD 2.5. The difference is measured caching, not a policy improvement. Whole-run warmup/setup and service execution used **562.140625 CPU seconds / 1,240.7865343 wall seconds**; startup is excluded from request latencies but included in this run total.

## Local compute coverage and limits

The audit snapshot records **6,836.09375 inclusive CPU seconds** (about 1.899 CPU hours) across **116 root runs with CPU timing** and **38,342.0213 summed run-wall seconds** (about 10.651 hours). It excludes 1,079 nested runs from double counting. Sum of wall times is not elapsed campaign duration; it omits time between runs and may include overlapping roots.

Four older root records lack CPU timing: the two original MovieLens popularity reproductions, the first MovieLens baseline comparison, and a validation recovery checkpoint. Their missing CPU seconds cannot be reconstructed and are not reported as zero. The totals also exclude coding-agent/UI/tool work, dependency/data installation, uninstrumented diagnostics, and later archive/CI replays. Host energy, network bytes and provider-internal compute are unmetered. Local CPU hours are not converted to a fictitious cloud bill. This is a disclosed measurement-coverage limit, not a claim of complete host resource accounting.

## Provenance and zero-call reproduction

| Record | Source |
|---|---|
| Actual synchronous run | `logs/20261001_024610_amazon_serving_audit_extended`, source `a4a39be` |
| Public serving archive | `artifacts/published/serving_v1`; publication `logs/20261001_030826_publish_serving_results`, source `f2d1d20` |
| Serving replay | `logs/20261001_030827_serving_archive_replay` (Python 3.11), `logs/20261001_031149_serving_archive_replay` (3.12); numeric difference zero |
| Settled campaign audit | `logs/20261001_030844_amazon_campaign_resources`, source `cd5b96c`; `require_no_pending: true` |
| Public accounting archive | `artifacts/published/resources_final_v1`, non-interim snapshot |
| Accounting replay | `logs/20261001_031105_final_resource_archive_replay` (3.11), `logs/20261001_031148_final_resource_archive_replay` (3.12), source `d724ece` |

```powershell
uv run --locked --extra yaml --extra experiments --extra api python main.py --config configs/serving_archive_replay.yaml
uv run --locked --extra yaml --extra experiments --extra api python main.py --config configs/final_resource_archive_replay.yaml
```

These commands recompute saved observations; they do not regenerate model calls or simulate latency. Financial replay maximum difference is **zero on Python 3.11** and **2.1316282072803006e-14 USD on 3.12**, below the unchanged 1e-12 tolerance. All nonfloating fields match exactly. Serving replay is exact on both, with tolerance 1e-14. A new paid serving measurement is optional and requires authorized credentials and a fresh budget estimate; it is not needed to verify this report.

[Full campaign record](campaign_resources.json), [observed service resources](serving_resources.json), [machine-generated service table](serving_summary.md), [controller fit resources](controller_fit_resources.json), [3.11 accounting verification](accounting_replay_verification.json), [3.12 verification](accounting_replay_python312.json). Public archives omit prompts, reviews, raw user IDs, keys and provider response/Batch IDs. Reservation IDs remain solely to audit physical-call deduplication.
