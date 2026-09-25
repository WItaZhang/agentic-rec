# Resource checkpoint and provider billing block

The project is **unfinished**. OpenAI rejected a new Batch creation with HTTP 400, `billing_hard_limit_reached`; see the [redacted provider response](provider_rejection.json). The user's USD 50 project authorization is unchanged. An authorization to spend is not the same as an available provider-account balance. No account credit purchase or limit increase was performed.

All already submitted batches have been collected. There are no running experiment processes or pending paid reservations. The expanded policy-label matrix has **641 / 2,612 physical calls completed**, not a complete matrix; it has not been used for fitting or selected-outcome analysis. Strong-sequence evidence, expanded routing, frozen final test and controlled serving latency remain unexecuted. The final method is not selected.

## Reconciled actual resources

This is a timestamped interim audit, not the cost of the completed planned project. [Full reconciliation](campaign_resources.json), [config](config.yaml), [source manifest](manifest.json). Run: `logs/20260925_191002_amazon_interim_campaign_resources`, source `3fe7d85`.

| Phase | Model-generation requests with observed usage | Known usage-priced USD |
|---|---:|---:|
| Synchronous feasibility | 32 | 0.0693040 |
| Batch feasibility | 32 | 0.0362456 |
| Development pilot | 1,023 | 1.0458048 |
| Complete population evidence validation | 6,842 | 7.7131224 |
| Equal-token content control | 956 | 1.4859628 |
| Expanded policy labels, incomplete | 641 | 0.7310188 |
| **Total** | **9,526** | **11.0814584** |

- One earlier pilot 429 has unknown usage and retains USD **0.0035016**. Total accounted amount is **USD 11.0849600**; remaining authorization **USD 38.9150400**, of which USD 33.9150400 is below the USD 45 planning stop.
- Actual observed input tokens: **54,402,912**, including **4,206,848** cached input tokens; output tokens: **342,936**. Unknown pilot usage is not imputed as zero.
- 56 other reserved requests were rejected at Batch creation, before any model generation. They are recorded separately with a zero charge and **no fabricated token-usage record**. The original error and a subsequent explicit HTTP 400 rejection, plus a provider batch-list reconciliation, support this classification. There was no accepted duplicate batch. The 56 requests remain to be generated when resources become available.
- 9,583 reservation records therefore comprise 9,526 observed generations, one uncertain pilot generation, and 56 requests rejected before generation. Do not call all 9,583 successful LLM calls.
- Recorded inclusive experiment CPU time: **2,298.34375 seconds**. Sum of recorded run wall times: **11,576.586 seconds**. These exclude agent/UI time, installs/downloads and uninstrumented diagnostics. Four older runs lack CPU timing. Nested batch children are not double counted; standalone recovery collection remains included. Wall-time sums are not elapsed campaign duration.
- No cloud rental. Energy, provider-internal compute and network bytes are unmetered. Prices are frozen published-price estimates from real usage, not reconciled invoices. Batch turnaround is not serving latency.

These expenses are primarily **offline experiment and label construction**. Per-request counterfactual API costs appear in the evidence reports. Controller training and controlled service latency cannot be filled with guessed numbers while the corresponding experiments are incomplete.

## Exact recovery

The [checkpoint evidence](recovery_evidence.json) retains the original failed scheduler without rewriting its history. It keeps 12 collected shards and marks only the rejected shard as unsubmitted. Remaining phase estimate: approximately USD **2.2477996**, maximum reservation **2.6451532**, within the original USD 6 phase allowance. There is no reason to repeat completed calls.

Minimal external recovery condition: restore usable OpenAI account credit/hard-limit capacity for the existing credential, or supply another authorized funded OpenAI credential file. The user has been asked via a popup. Do not publish credentials or retry new paid requests before that condition is resolved.

On the existing local workspace, resume with:

```powershell
uv run --locked --extra yaml --extra experiments --extra api python main.py --config configs/amazon_policy_batch_resume_after_billing.yaml
```

This config references `logs/20260925_073228_amazon_policy_billing_checkpoint`. The private `logs/` directory is needed for **resuming this run**; a fresh clone can reproduce the already completed public analyses independently using the archive configs. Do not run a second scheduler against the same checkpoint concurrently.

After complete collection: evaluate the policy matrix, fit grid v2, publish/verify offline refitting, run the queued strong-sequence comparison (not yet started), choose the practical method on validation, then freeze final test. The original sequence waiting launcher stopped when policy failed; it must be deliberately restarted after recovery. No schedulers are currently left running.

Completed deliverables remain available: [population evidence](../20260925_m3_evidence_validation/README.md), [content control](../20260925_m3_content_control/README.md), [working study](../adaptive_evidence_study/STUDY.md), and [accurate interim résumé/interview drafts](../career_materials/README.md). None assert final adaptive gains.
