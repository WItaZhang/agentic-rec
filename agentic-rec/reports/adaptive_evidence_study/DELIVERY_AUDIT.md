# Delivery evidence audit

Checkpoint: 2026-10-01 UTC. **The research objective is not complete.** This audit
links acceptance requirements to observed evidence and identifies work still
required. A running job, implemented interface or planned configuration is not
evidence of a completed experiment. See [the execution record](../../docs/adaptive-evidence/PROGRESS.md)
for exact commits and immutable run directories.

| Requirement | Current evidence | Status / remaining work |
|---|---|---|
| Preserve and reproduce the existing MovieLens foundation | [M0/M1 record](../../docs/adaptive-evidence/PROGRESS.md), [real comparison](../20260923_m1a_baselines/README.md); two identical popularity reproductions; original PR commits retained on default | Verified. Multi-positive MovieLens metrics remain separate from Amazon single-target metrics. |
| Real data, global time boundaries and realistic candidate retrieval | [Data profile](../20260923_m1b_amazon_profile/README.md), [event replay](../20260923_m1c_amazon_replay/README.md), checksummed inputs and frozen models | Verified on development runs. Final execution must preserve the same protocol. |
| Isolation of current labels, strict past history, immutable candidates and full denominators | `tests/test_protocol.py`, replay/evidence/freeze tests, complete matrix checks in `src/batch_matrix.py`; no target insertion; cold and unrecalled requests retained | Implemented and tested. Final result archives must also cover every frozen request. |
| Conventional recommenders | [Same-user comparison](../20260924_m3_validation_baselines/README.md): popularity, ItemKNN and causal sequence model | Development complete. All three are bound into final inputs; final scores pending. |
| Real recent/full-evidence LLM and fixed-workflow controls | [3,318-user validation](../20260925_m3_evidence_validation/README.md), real provider usage and public outcome archive | Complete. R1/R4 are one-call workflows; local evidence assembly is not multistep model reasoning. |
| Rule, budget-calibrated random and learned routing | [Weighted routing validation](../20260930_m4_routing_validation/README.md); four estimator hashes and all selected actions reproduced offline | Development complete. Frozen final predictions exist; final outcomes pending. |
| Component ablations and evidence-content control | R0–R4 population matrix and [478-user equal-token alignment control](../20260925_m3_content_control/README.md) | Complete. Correct versus corrupted alignment is not a neutral-padding control or a population estimate. |
| Robustness after strengthening the base recommender | Same 3,318 validation users, frozen causal-sequence pool, R0–R4; paired interaction specification `configs/amazon_retriever_robustness.yaml` | [Complete strong-base report](../20260930_strong_base_evidence/README.md), public outcomes and exact offline reanalysis verified; paired cross-retriever sensitivity executed. |
| Candidate-row presentation sensitivity | Fixed candidates/content, R1/R4, shared target-independent row permutation | [Complete presentation report](../20261001_presentation_control/README.md): 6636 exact normalized input pairs, all 123 shards, paired analysis, public archive and zero-difference offline replay. Aliases retain base-rank information; annotation changes too. |
| Conditional multistep acquisition and stopping | Request-level routing is implemented; [pre-final scope decision](STUDY.md#sequential-scope-decision-before-final-scoring) records why development controls do not establish an actionable post-tool benefit | Scope decided: retain request-level selection. Multistep superiority/ineffectiveness and adaptive stopping remain unmeasured; no performance claim. |
| Validation-only choice and untouched final test | [Immutable freeze](../../artifacts/frozen_protocol/v1/freeze.json), [practical selection](../../artifacts/frozen_selection/v1/deployment_selection.json), target-free preparation of 3,572 users | Freeze/input hashes and complete diagnostic gate verified. Final generation is running at `logs/20261001_004350_amazon_final_test_batch` (session 91054); no final scoring yet. Diagnostic results did not change the frozen method. |
| Paired uncertainty, fixed groups and honest quality claims | User-paired bootstrap, 10,000 resamples, history boundaries and 0.002 margin fixed before test; degenerate-comparison guard | Development analyses verified. Final paired analysis remains required. Identical policies cannot establish noninferiority from a zero-width interval. |
| Typical failures and applicability limits | [Development failure audit](../20260925_validation_failures/README.md): hit losses/rescues, cold/retrieval failures, deterministic cases; snapshot/pretraining caveats in [study](STUDY.md) | Development complete. Final attribution and examples must be added from actual final outputs. |
| Actual tokens, attempts, repairs, offline label/controller costs | [Interim resource report](../20260930_resource_checkpoint/README.md), sanitized accounting archive and exact offline repricing | Checkpoint verified, not final totals. Final audit must have no pending/running experiments and disclose the uncertain pilot charge and measurement coverage. |
| Comparable mean/P95 serving latency and per-request cost | `configs/amazon_serving_audit_extended.yaml`: 128 validation users, eleven methods including frozen secondary routes, concurrency one, fixed CPU/rate/timeout/retry/cache conditions | Configured and preflighted, **not executed**. Batch turnaround must not be substituted for service latency. |
| Runnable, modular, config-driven code and locked environment | Separated `src/` modules, `configs/`, read-only raw data, timestamped `logs/`, committed `uv.lock`; 168 local tests/Ruff pass; exact-head Python 3.11/3.12 push/PR CI and presentation/other archive replays pass on PR #18 | Verified for the current implementation. New changes require appropriate checks before merge. |
| Public reproducible metrics, plots and source/run provenance | Public development outcome/route/accounting archives; [reproduction instructions](../../docs/adaptive-evidence/REPRODUCE.md) | Development artifacts verified. Strong-base robustness is published and verified. Presentation results are now published and replayed. Final/serving/final-resource results and final reproduction entry points remain to publish. |
| Complete report and quality–cost comparison | [Working study](STUDY.md) and linked milestone reports | Incomplete until final results, serving costs and full campaign accounting are incorporated. |
| English résumé LaTeX and interview materials match evidence | [Development career draft](../career_materials/README.md), standalone source and saved compiler diagnostic | Rewrite using final results. Native compiler currently fails before source diagnostics; no compiled PDF is claimed or required for the requested LaTeX source. |
| GitHub, design status and handoff are synchronized | PRs #1–#18 merged; current work is on `codex/final-results`; `logs/CURRENT_CHECKPOINT.json` tracks live handles and budget | Current checkpoint is recoverable. Remaining result changes must be reviewed, checked and merged before completion. |

The registered primary-budget policies choose R0 for all final requests. This is
visible from frozen decisions without reading target labels; it is not a final
quality result and does not justify changing the comparison. Secondary budget
policies, fixed evidence methods and conventional baselines still require the
complete final experiment. The practical method was selected as
`causal_sequence` on validation and must not be reselected after test scoring.

Final completion requires replacing every pending entry with direct evidence from
the executed run or a justified conditional-scope decision. Budget availability,
passing tests and successful artifact verification alone do not prove the research
questions have been answered.
