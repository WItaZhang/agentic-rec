# Interview explanation — measured evidence and limits

## 90-second explanation

这个项目研究一个实际问题：推荐时，哪些请求值得多花一次模型调用，又应该给模型看哪些信息？用户历史、候选质量和信息缺口不同，统一给所有请求堆更多上下文，可能既贵又降低质量。我把不调用 LLM 也作为合法选择。

我用 70,922 条去重后的 Amazon 评论事件建立推荐回放。按全局时间隔离基础模型训练、策略训练、验证和测试；先由常规模型找出 200 个候选，再让不同证据方案比较同一批候选。真实目标不补进候选，没召回、冷物品、调用失败都留在指标分母里。

我比较了热门、ItemKNN、因果 Transformer，四种单次 LLM 证据方案，以及固定、规则、随机和学习策略。学习器在较早时期的 1,045 用户上学习每种动作的质量增量，验证集选择参数。3,572 用户冻结测试中，充分证据相对 ItemKNN 的 NDCG 下降约 0.01526；主预算档下所有选中策略都保留基础排序，没有学习优势。较高预算档的学习器只对 243 个请求调用 LLM，出现探索性 NDCG 信号，但它原本比随机对照多花约 22%。我额外做了明确标注为事后的等期望费用诊断，NDCG 差仍约 +0.0030，命中率差异仍不确定。

因此最终保留验证阶段选定的常规序列模型，不在看过测试后换成点估计最高的方法。项目价值是一个能审计证据、时间可见性、调用成本和统计不确定性的研究流程，以及清楚说明何时复杂方案不值得采用。它实现的是请求级证据选择，没有宣称多步 Agent 或线上点击率提升。

## English explanation

“I studied when a recommendation request justifies an LLM call and which evidence the call should receive. I built a temporal pipeline on 70,922 deduplicated Amazon review events, with separate global windows for base training, policy training, validation and testing. Evidence treatments shared the same retrieved top-200 candidates, and retrieval misses, cold items and failures remained in the denominator.

“I compared popularity, ItemKNN and a causal Transformer, four single-call evidence configurations, fixed workflows, rules, random allocation and learned utility routers. Four router models were fitted on real action outcomes for 1,045 earlier-period users. Parameters, budget points and deployment selection were frozen on 3,318 validation users before scoring 3,572 test users.

“On the frozen test, full evidence reduced NDCG@10 by 0.01526 versus ItemKNN. The primary policies all retained the base ranking, so there was no primary learning advantage. A secondary learner called the LLM on 243 requests and showed an exploratory ranking-quality signal. Because it spent about 22% more than the frozen random sample, I separately reported a post-evaluation, cost-only alignment sensitivity. Its NDCG difference remained about +0.0030, while the hit-rate difference was unresolved. I retained the validation-selected sequence recommender rather than reselecting on test results. The contribution is an auditable quality–cost study, not a claim that more agent complexity always wins.”

## Problem, hypotheses and design

| Hypothesis | Test | Supported interpretation |
|---|---|---|
| Requests need different evidence | R0–R4 matrix and fixed history groups | Effects vary; no-history gains are not personal-history gains; warm groups are small |
| Content matters beyond input length | 478-user control with exactly matched actual input tokens and shuffled category associations | Correspondence matters within this enriched cohort; corrupted context is not neutral padding |
| Features can allocate useful calls | Four weighted utility models, seven rules, frozen random allocation and five budgets | Primary policies degenerate to R0; secondary NDCG signal is exploratory, HR unresolved |
| Findings survive a stronger base | Same-user R0–R4 study on causal-sequence candidates | Full evidence remains harmful on validation; cross-retriever changes include candidates/order |
| Another decision after a tool result is useful | Conditional gate assessed on development evidence | No actionable intermediate decision established; sequential acquisition/stopping not measured |

The target is the next positively rated, previously unseen reviewed item, not an online click. R0 retains the base ranking; R1 adds the latest history event and titles; R2 supplies up to 20 events and titles; R3/R4 add categories to R1/R2. R4 is local evidence assembly followed by one LLM call. R2 is a bounded history window, not semantic memory retrieval.

The router predicts action NDCG increments over R0 from ten target-free history/base-score features. Ridge and histogram boosting use complete earlier-period action labels and inverse-inclusion weights for history-enriched sampling. A cost penalty trades predicted gain against dollars. Validation searches the declared grid and picks the cheapest candidate within a 0.002 quality tolerance. That decision tolerance is not statistical equivalence. Practical all-method selection is separate from the scientific within-KNN routing comparison.

## Questions to expect

**What is agentic here?** A controller chooses whether to invoke a model and which evidence bundle to acquire for each request. Execution is bounded and inspectable. No repeated post-tool reasoning, reinforcement learning, autonomous browsing, reflection or generated summary is claimed.

**What are the main final numbers?** ItemKNN NDCG/HR is 0.045767/0.103024; recent evidence 0.045513/0.100784; full evidence 0.030512/0.071109. Full−base NDCG is −0.015255 [−0.020532, −0.009929]. The validation-selected sequence model scores 0.047393/0.105823 on its own candidates. Sequence−KNN +0.001626 [−0.000143, +0.003411] is unresolved on test; I do not call it a proven test winner. [Final report](../20261001_final_test/README.md).

**Did learning beat rules and random allocation?** Not in the primary comparison: all choose R0. The frozen secondary learner has NDCG 0.048531 at USD 0.061353/1,000 Batch requests versus rule 0.046261 at USD 0.627485 and random 0.045879 at USD 0.050385. Nominal NDCG intervals exclude zero, but the random comparison is not equal cost and HR intervals cross zero. This is a secondary signal, not an overall adaptive-system win.

**Why is the new cost-matched comparison exploratory?** It was added after observing test cost drift. Costs/actions alone calibrate expected spend, preserving the learner's non-R0 mixture. Still, the investigation was motivated by observed test results. Learned−expected random NDCG is +0.002997 [0.001036, 0.005105], HR +0.001693 [−0.001321, 0.004721]. Intervals condition on saved costs and model outputs, not uncertainty of a future calibration. No original comparison or adoption choice changed. A confirmatory claim needs independent replication.

**Why can R1 help users without history?** It still provides titles and base order. Their small final gain +0.000560 is title/prior reranking, not personalization. The ≥2-history effect is −0.043716 [−0.080291, −0.008058]; the one-history effect is imprecise. Group heterogeneity alone does not prove predictable individual utility.

**Why does more evidence hurt?** This result is for a fixed prompt, model and sparse dataset. Coarse categories, context distraction, preference ambiguity and displacement of a useful base prior are plausible explanations, not established hidden causes. Equal-token correspondence controls one content effect, but does not compare information with neutral padding. I retained the negative result instead of tuning the final prompt until it became positive.

**Does the conclusion survive a stronger recommender?** On 3,318 validation users, full evidence minus the sequence base is −0.028562 [−0.034887, −0.022317]; recent evidence −0.002855 [−0.006230, +0.000434]. Within each retriever candidates are fixed; cross-retriever effects also change composition/order and output draws. [Strong-base report](../20260930_strong_base_evidence/README.md).

**Could the model follow the displayed ranking?** Row permutation lowers R1 NDCG by 0.010127 and R4 by 0.021811 on validation. All 6,636 logical pairs have matching normalized transmitted content apart from declared row order/annotation. Aliases still retain base rank, the annotation adds eight tokens, and generation dates/output noise differ. This shows presentation sensitivity, not isolated causal position bias. [Presentation report](../20261001_presentation_control/README.md).

**How did you prevent leakage?** Base weights/catalog stop before 2018; policy labels are from 2018–2020, validation 2020–2021, test 2021 onward. Tied events are predicted before updates. Current target/review/rating cannot enter prompts or features. Candidate fingerprints/actions are saved before labels are read; the target is never inserted. Historical feedback is used only after visibility, and cached responses require identical request-visible inputs.

**What visibility risk remains?** Titles/categories come from a later crawler snapshot and are assumed static. Possible model pretraining exposure is not excluded. Dynamic prices/average ratings/counts are omitted. Temporal interaction isolation does not remove metadata/pretraining limits.

**What did failures show?** Test KNN misses 1,949/3,572 targets, including 685 cold items; reranking cannot recover them. R4 loses 305 base hits and rescues 191; R1 loses 43 and rescues 35. R4 spends USD 3.003855 counterfactually on absent targets. These are retrospective labels, unavailable to routing. [Hash-selected cases](../20261001_final_test/failure_cases.json) include Good Housekeeping falling out from base rank 3 and an empty-history Food Network Magazine rising from rank 11 to 10. Examples show behavior, not hidden reasoning.

**Does crossing zero mean no loss?** No. Preservation requires the frozen one-sided noninferiority test against margin 0.002. Recent evidence fails it. Identical policies have degenerate zero differences: identical evaluated behavior is not evidence that learning helps.

**Why not more steps?** The route made this conditional on useful intermediate decisions. Development did not establish that value, and outcome-aware oracles include output noise: 118/489 pilot repeated-input groups changed ranking even at temperature zero. The scope decision preceded final scoring. It does not prove multistep methods ineffective or claim adaptive stopping.

**How are resources counted?** Actual provider input/output/cached tokens, durable attempt reservations, failures and repairs. Physical calls are deduplicated across same-request exact-input reuse and resumptions. Offline labels/training are separate from per-request expense. Batch discount is not routing savings. The synchronous audit fixes concurrency, timeout/retry/cache/CPU rules and separates overall from generation-branch mean/P95. Final accounted expense is USD 37.3749584, including a retained USD 0.0035016 unknown pilot reserve. There are 182,255,677 known input and 1,181,412 output tokens. In the 128-user serving audit, selected sequence mean/P95 is 5.023/8.369 ms; recent/full mean is 3.112/3.229 seconds including research-budget bookkeeping and pacing. The secondary learner has only four generated requests, so its conditional latency tail is descriptive. [Final resource report](../20261001_final_resources/README.md) records all scopes and coverage gaps.

**What can someone reproduce?** Public archives reproduce frozen statistics/plots without data download or credentials. Original data/config/model hashes support temporal replay; new LLM generations require paid access and are not bitwise reproducible. Offline router refitting reproduces four estimator hashes and 25 validation action vectors. [Commands and privacy boundaries](../../docs/adaptive-evidence/REPRODUCE.md).

## Limits and next independent experiment

One sparse Amazon category, review-event selection instead of impression logs, a frozen catalog, static crawler metadata, one model snapshot and one output realization constrain generalization. Development exploration and secondary comparisons have nominal intervals. No production deployment, CTR uplift, optimal stopping or general quality-preserving cost reduction was demonstrated.

A useful follow-up would preregister the selective-evidence signal on a new domain/time window and repeated model draws, with matched actual-cost controls and stronger retrieval coverage. It would not retune this test. The practical method stays the validation-selected causal sequence model.
