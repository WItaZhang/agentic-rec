# Evidence-backed career materials

The LaTeX and interview text use the **completed frozen-test** results, with primary, secondary and post-evaluation evidence distinguished. They do not claim production deployment or multistep reasoning. Serving and final campaign resource claims are linked separately from the quality results; their current completion state is in the [delivery audit](../adaptive_evidence_study/DELIVERY_AUDIT.md).

- [English LaTeX project description](resume_project.tex): pasteable fragment; enclosing résumé needs `hyperref`.
- [Standalone preview source](resume_preview.tex): embeds the same fragment for the built-in editor. Compilation/layout remains unverified until the final source is checked; the previous native compiler failed before source diagnostics. No PDF is claimed. [Compiler record](latex_compile_status.json).
- [Chinese and English interview explanation](INTERVIEW.md): problem, hypotheses, design, comparisons, findings, failures and limits.
- [Consolidated study](../adaptive_evidence_study/STUDY.md) and [frozen final results](../20261001_final_test/README.md).

| Claim | Direct evidence | Boundary |
|---|---|---|
| 70,922 deduplicated Amazon events | [Training-only data profile](../20260923_m1b_amazon_profile/README.md): 71,497 rows minus 575 duplicates | Not all are training examples; global windows are disjoint |
| Real temporal pipeline and immutable top-200 candidates | Checked raw/model/input hashes, protocol and label-isolation tests | Review-event proxy; static crawler metadata and possible pretraining exposure remain limitations |
| Four utility estimators from 1,045 earlier users | [Routing report](../20260930_m4_routing_validation/README.md), offline refit matches four hashes and 25 validation policy actions | Trained with history-stratum weights; no primary learning gain |
| 3,318 validation / 3,572 frozen test users | Separate time windows, prelabel request sampling, frozen selection artifact and complete final archive | These are independent users within each partition; don't treat action rows as independent samples |
| Full evidence lowers final NDCG by 0.01526 | R4−R0 = −0.015255, paired 95% interval [−0.020532, −0.009929] | Absolute metric units, not 1.526% relative or an online outcome |
| Validation-selected sequence model retained | `artifacts/frozen_selection/v1/deployment_selection.json`; test NDCG 0.047393 | Test difference versus KNN is unresolved; not declared the test winner |
| Content and strong-base controls | [478-user equal-token study](../20260925_m3_content_control/README.md), [strong-base study](../20260930_strong_base_evidence/README.md) | Corrupted correspondence is not neutral padding; stratified diagnostic is not population-representative |
| Presentation sensitivity | [6,636 normalized input-pair proof](../20261001_presentation_control/README.md) | Row annotation, eight tokens, aliases, generation dates/output noise limit causal interpretation |
| Exploratory secondary routing signal | [Frozen and cost-aligned comparisons](../20261001_final_test/README.md) | Original random cost mismatches by 21.77%; post-evaluation sensitivity is conditional/exploratory, HR uncertain |
| Offline reproducibility | Public input/outcome/usage archives and zero-call replay commands | Analysis reproduction is distinct from bitwise regeneration of stochastic LLM outputs |

The résumé deliberately emphasizes implementation, protocol rigor and a defensible negative finding. The secondary positive signal belongs in a nuanced interview explanation, not an unqualified headline. Do not claim optimal stopping, quality-preserving savings, a deployed recommendation service, semantic long-memory retrieval or general adaptive-policy superiority. For a shorter résumé retain the first two bullets.
