# Evidence-backed career materials — interim

These materials describe completed engineering and **development** experiments as of 2026-09-30. They do not present an unfinished research project as finished. The previous billing block is resolved. Complete weighted routing validation and the stronger-base evidence control are available; the presentation control, frozen final test and controlled serving audit are still pending. Update this directory after those stages complete; do not silently replace “validation” with “test.”

- [English LaTeX project description](resume_project.tex), a fragment requiring `hyperref` in the enclosing résumé.
- [Standalone LaTeX preview](resume_preview.tex), with a visible development-status notice. It embeds the fragment so the built-in editor needs no additional project files. The native compiler currently fails with “Unable to find standard directories for platform”; compilation/layout are unverified, and no PDF is claimed. See [compiler status](latex_compile_status.json).
- [Interview explanation and questions](INTERVIEW.md).
- [Working study](../adaptive_evidence_study/STUDY.md), [population validation](../20260925_m3_evidence_validation/README.md), [equal-token diagnostic](../20260925_m3_content_control/README.md).

| Claim | Evidence | Boundary |
|---|---|---|
| Real temporal recommendation pipeline | Amazon profile, replay and sequence reports; frozen model artifacts | Review-event proxy; one category; no online CTR experiment |
| 70,922 valid deduplicated reviews | `20260923_232442_amazon_training_profile`: 71,497 input rows, 575 exact duplicates | Not 70,922 training examples; global cutoffs create disjoint windows |
| 3,318-user fixed-candidate evidence comparison | `20260925_071030_amazon_validation_matrix_evaluate`, 6,842 physical generations | 13,272 logical actions share identical same-request inputs; not 13,272 independent calls |
| Full evidence lowers NDCG by 0.02656 | R4−R0, 95% paired interval [−0.03273, −0.02050] | Validation estimate, absolute metric units, not percent or final-test generalization |
| Full-evidence loss persists with a stronger base | [3,318-user sequence control](../20260930_strong_base_evidence/README.md): R4−R0 −0.028562, nominal paired interval [−0.034887, −0.022317] | Fixed candidates within each retriever; cross-retriever changes include candidates/order and different output realizations |
| Exactly equal token count control | 478 actual R4/S4 token pairs match, 956 generations | Stratified diagnostic; corrupted correspondence is not neutral padding |
| Weighted policy learning | [1,045 policy users; four estimators](../20260930_m4_routing_validation/README.md), complete real labels and inverse-inclusion weights | Primary validation comparison collapses to R0; secondary quality preservation versus the rule is unestablished |
| Offline statistical reproducibility | Public pilot, validation and content-control archives reproduce all values exactly | Regenerating LLM outputs is stochastic and requires paid access; this is exact analysis replay |

Do **not** currently claim: learned routing beats rules/random, a deployed adaptive recommendation system, quality-preserving cost reduction, optimal stopping, multistep reasoning, semantic long-memory retrieval, or final-test improvement. The complete router fit reproduces all four estimator hashes and all 25 validation action vectors offline. At the primary budget, selected validation actions are all base; this is not a population equivalence or learning-gain claim. Cost and latency claims await the remaining controlled runs.

For a shorter résumé, retain bullets 1 and 2. The negative result is useful when framed as model selection and rigorous evaluation, not as an improvement that did not occur.
