# Reproducible resource checkpoint — September 30, 2026

This is a historical snapshot of an ongoing campaign, not the final campaign total or the current account balance. Strong-sequence labels were still running; presentation generation, final-test generation and the synchronous serving audit had not started. Final test inputs were prepared without scoring targets.

Known usage-priced API cost is **USD 18.5115102**; conservative accounting including 210 pending reservations and one older unknown-usage attempt is **USD 18.8006378**. The unresolved pilot reservation is USD 0.0035016. Original authorization is USD 50, with a USD 45 planning stop.

| Phase | Known usage-priced USD | Accounted USD | Observed generations | Pending reservations | Pre-generation rejections |
|---|---:|---:|---:|---:|---:|
| batch_feasibility | 0.0362456 | 0.0362456 | 32 | 0 | 0 |
| development_pilot | 1.0458048 | 1.0493064 | 1023 | 0 | 0 |
| main_validation_labels | 7.7131224 | 7.7131224 | 6842 | 0 | 0 |
| policy_training_labels | 2.9788184 | 2.9788184 | 2612 | 0 | 56 |
| stronger_retriever_validation_labels | 5.1822522 | 5.4678782 | 4605 | 210 | 52 |
| synchronous_feasibility | 0.0693040 | 0.0693040 | 32 | 0 | 0 |
| token_matched_content_control | 1.4859628 | 1.4859628 | 956 | 0 | 0 |

## Observed usage and recovery
- Provider usage: **90,606,227 input tokens**, **579,672 output tokens**, with **4,206,848 cached input tokens already included in the input total**. All 16,102 observed physical calls were independently repriced from their frozen standard/Batch tables; the per-call difference from the ledger is exactly zero.
- 16,103 recorded generation attempts include one older unknown-usage failure. The 108 proven requests rejected before generation (56 billing, 52 queue validation) are counted separately with zero charge and no fabricated token usage.
- 13,875 token-count operations: 12,819 in completed preparation runs plus 1,056 synchronous preflights. No paid generation was needed for preparing final inputs.
- 13 completed upload recoveries reused original generation reservations. One queue-recovery checkpoint requeued only proven unexecuted inputs. The same generated output is not charged twice because it was collected, resumed or attached to several counterfactual actions.
- 125 physical outputs were repaired or replaced by a fallback among 11,498 calls with recorded ranking validation. This is coverage-limited while the sequence matrix is unevaluated. 29,223 logical history/title/category accesses are recorded for 11,498 generations; they are in-memory evidence bundles, not external HTTP tool calls.

Management counters distinguish uploads, status polling, downloads and recovery. Polling resumes subtract inherited counters. These are recorded SDK operations/receipts; pagination, transport-level exchanges and manual diagnostics outside managed runs are not completely metered. Local CPU/wall timings and their coverage are retained in [the snapshot](campaign_resources.json). Host energy, provider-internal compute and network bytes are unmetered. Batch turnaround is not online service latency. Dollar values are usage-based estimates, not invoices.

## Offline verification

The sanitized [accounting archive](../../artifacts/published/resources_checkpoint_20260930) contains physical reservation identities, token usage, zero-generation rejection records, observed operation counters and original price tables. It excludes keys, prompts, responses, review/user identifiers and provider response/batch IDs. It reconstructs known costs, unknown reservations, per-phase totals, repairs, preflights and recovery counts without private logs, datasets or API access.

```sh
uv run --locked --extra yaml --extra experiments --extra api python main.py --config configs/resource_checkpoint_archive_replay.yaml
```

Actual replay `logs/20260930_213718_resource_checkpoint_archive_replay` at `124a614` reproduced every field exactly: maximum numeric difference zero. The declared tolerance 1e-12 permits only currency summation roundoff; counts and other fields must match exactly. See [verification](verification.json).

Source audit: `logs/20260930_213606_amazon_interim_campaign_resources`, source `f5c494b`. The raw snapshot/config/manifest are preserved here. The archive is an interim snapshot with pending reservations; it must not be presented as a final complete resource audit.

## Remaining planned cost

The complete remaining-plan forecast, including entire sequence/presentation/final/serving phases without double-counting completed portions, is USD 37.5232016 at earlier observed output lengths, or USD 41.8475216 at conservative maxima. The actual ledger gate still applies before each call. Final-test predictions and quality remain unscored.
