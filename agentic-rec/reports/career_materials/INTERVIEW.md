# Interview explanation — supported results and pending claims

## 90-second explanation

我研究的是推荐请求是否值得花额外计算获取证据。不同用户的历史长度、候选排序和信息缺口不同，把所有历史与商品信息一律塞给 LLM，可能既贵又降低质量。

我先建立真实 Amazon 评论事件的时间回放流程，用全局时间边界隔离基础模型训练、策略训练、验证和测试。基础模型只用训练期数据生成 top-200 候选，各证据方案在同一份候选上比较，不补入真实目标。未召回、冷物品、失败请求都保留在分母中。

目前已完成的 3,318 用户验证显示：近期历史单次重排相对 ItemKNN 的 NDCG 差只有 +0.00061，区间跨零；充分证据反而下降 0.02656。分组结果也有差异：空历史请求的轻量重排略有收益，多事件历史组则明显受损。我又做了输入 token 完全相同的类别打乱对照，发现正确类别对应在有历史组优于打乱对应，空历史组却相反。这说明内容对应关系和请求状态有影响，但不能说增加信息普遍有效。

我已用较早时间段的 1,045 用户真实标签训练四个路由模型，并与规则和成本匹配的随机分配比较。主要预算点的验证选择全部保留基础排序；次要预算点虽减少调用，但没有证明相对规则质量无损。按预先记录的方法选择规则，目前选中不调用 LLM 的序列推荐器。强基础模型对照中，充分证据的下降依然存在；候选行打乱后表现进一步下降，说明呈现条件也需要控制。冻结的最终测试正在生成，服务延迟尚待测量，所以我不会声称已验证自适应收益。

## English explanation

“I studied when a recommendation request is worth an additional LLM call and what evidence that call should receive. I built a temporal replay pipeline with global training, policy-training, validation, and test windows. Every evidence treatment used the same retrieved candidates, and missing targets, cold items, and failed requests stayed in the denominator.

“On 3,318 validation users, a recent-history reranker did not establish an aggregate improvement. Supplying full evidence reduced NDCG@10 by 0.02656. The direction varied by history group. I then held actual input-token counts fixed while shuffling candidate-category associations. Correct alignment helped relative to corrupted alignment for users with history, but the direction reversed for empty histories. Full evidence still trailed the conventional baseline.

“I fitted four weighted utility routers from real labels for 1,045 earlier-period users. The primary validation budget selected the baseline for every request; a secondary learner used fewer calls but did not establish preserved quality against the rule. Full evidence also reduced NDCG by 0.02856 under the stronger sequence base. A separate row-order control found further losses under shuffled presentation, with identical evidence content verified against actual requests. The registered adoption rule selected the conventional sequence model. Final-test confirmation is pending, so I do not claim a validated adaptive improvement.”

## Problem and hypotheses

- **Question:** What additional evidence does a request need, and can a policy allocate evidence and model calls better than a fixed workflow at comparable measured cost?
- **H1:** Evidence can improve some requests. Current evidence: heterogeneous development effects; no aggregate recent-evidence gain established.
- **H2:** Observable request features predict useful actions. Current evidence: complete weighted real-label fitting and validation; the primary selected policy keeps all requests on the base model. Group heterogeneity alone does not prove learnability.
- **H3:** Decisions improve quality–cost tradeoffs. Current evidence: primary validation actions are identical; secondary cost savings do not establish preserved quality versus the rule or superiority versus the frozen-seed random allocation.
- **H4:** Decisions after seeing tool results justify multiple steps. No observed evidence currently establishes this; no multistep ability is claimed.

## Method and fair controls

The task predicts the next positive, previously unseen reviewed item (rating at least four). ItemKNN is the main candidate generator; popularity and a causal Transformer provide conventional controls on their own candidate pools. Comparing different retrievers measures the whole recommendation pipeline, while evidence comparisons keep the main pool fixed. The earlier MovieLens experiment uses a different multi-positive protocol and its scores are not comparable with Amazon next-item scores.

The executable action space is R0 (no LLM), R1 (latest history event plus candidate titles), R2 (up to 20 recent events plus titles), R3 (R1 plus categories), and R4 (R2 plus categories). R4 is deterministic local evidence assembly followed by **one** LLM rerank. It is not multistep planning. R2 uses the last 20 events; it is not semantic memory retrieval.

The fitted learned router estimates each action's NDCG difference from R0 using ten target-free history and base-score features. Ridge and histogram boosting are fitted on earlier policy labels, with inclusion weights for the history-enriched training sample. A dollar penalty trades expected gain against cost. Validation selects from the registered grid; final test cannot change it. Random allocation matches observed validation spending in expectation, so realized test costs must still be reported. The practical method is selected separately across conventional and routed candidates using the registered validation tolerance and simplicity rule.

## Questions to expect

**Why can empty-history requests benefit from R1?** R1 still provides candidate titles and the base-model order. For an empty history its effect is title/prior reranking, not personalization. This is a key interpretation limit.

**Why does more evidence hurt?** The controlled ablation records a difference for this prompt, data slice and model. It does not identify one universal cause. Coarse crawler categories, context distraction, review-to-preference mismatch and preservation of useful base order are plausible explanations. The equal-token control shows that correct correspondence matters differently by group; it does not remove every confound between information content and neutral token padding.

**Does the conclusion survive a stronger conventional model?** The [completed sequence-base control](../20260930_strong_base_evidence/README.md) uses the same 3,318 validation users and fixes that model's own candidate pool across R0–R4. Full evidence minus the sequence base is −0.028562 NDCG, nominal paired interval [−0.034887, −0.022317]. Recent evidence minus base is −0.002855 [−0.006230, +0.000434], so its benefit and quality preservation are both unestablished. The full-evidence loss persists, but cross-retriever changes also include candidate composition, ordering and different output realizations; this is not a pure embedding ablation.

**Could the LLM be relying on the displayed ranking?** The [completed presentation control](../20261001_presentation_control/README.md) keeps all candidate identities and verifies the actual evidence content for 6,636 logical input pairs. Shuffled versus ordered presentation lowers R1 NDCG by 0.010127 [−0.013134, −0.007267] and R4 by 0.021811 [−0.026460, −0.017283]. This supports sensitivity to this presentation condition. It does not isolate pure position bias: the order annotation also changes, every input has eight more tokens, alias IDs still encode base rank, and generation dates/output noise can confound the comparison. No-history results cannot be called personalized-history gains. I did not alter the frozen final method using this diagnostic.

**Why stop at request-level routing?** The original route made multistep acquisition conditional on a demonstrated useful decision after observing an intermediate tool result. Completed development controls do not establish that benefit. The [recorded scope decision](../adaptive_evidence_study/STUDY.md#sequential-scope-decision-before-final-scoring) therefore retains request-level evidence selection. It does not prove multistep methods are ineffective; post-tool policies, adaptive stopping and their comparison with one-call full evidence remain unmeasured.

**Is the oracle gain evidence for a learning policy?** No. It chooses actions using true outcomes and includes model-output noise. In the pilot, 118 of 489 same-request repeated-input groups changed ranking even at temperature zero. A deployable router never sees current targets or counterfactual quality.

**How do you prevent leakage?** Base weights and item catalog stop at the base cutoff. History events must be strictly earlier than the prediction timestamp; tied events become visible only after their predictions. Candidate snapshots and route choices are saved before labels are consulted. Current review text, current rating and target ID cannot enter prompts or routing features. Earlier feedback is allowed only when it has become causally visible.

**What is the largest remaining visibility risk?** Product titles/categories come from a later crawler snapshot. They are treated as static, not historically timestamped attributes. This assumption and possible model pretraining contamination must remain explicit. Dynamic price, average rating and review-count fields are excluded.

**Why keep unrecalled and cold targets?** Reranking cannot recover a target absent from candidates. Dropping such requests would overstate end-to-end quality and hide wasted calls. In population validation, 1,480 of 3,318 targets were not retrieved, including 418 cold targets. These labels can explain failures after evaluation; they cannot guide routing at prediction time.

**What did failure analysis reveal?** The [completed validation audit](../20260925_validation_failures/README.md) shows that full evidence loses 388 original base hits while rescuing 196; recent evidence loses 38 while rescuing 49. Approximately 44.6% of each scheme's measured API cost is spent on unrecalled targets. An empty-history example drops *Family Handyman* from base rank five, while another promotes *Food Network Magazine* from rank eleven to five. These fixed-hash selected cases illustrate mixed effects; they neither explain the model's private reasoning nor prove that a router can identify the useful calls.

**Does a confidence interval crossing zero mean no loss?** No. It means the experiment did not establish a difference at that precision. A quality-preservation claim requires the registered one-sided noninferiority test against a 0.002 NDCG margin. The validation selection tolerance is a decision rule, not a statistical equivalence claim.

**How is cost measured?** Provider input/output/cached-token usage and persistent attempt reservations, including failures. Batch labeling is offline construction cost; it is separated from counterfactual per-request API cost, controller training and local CPU. Batch turnaround is not serving latency. Mean/P95 service latency requires the separate fixed-concurrency synchronous audit, which has not yet run.

**Why not deploy the most complicated method?** Complexity needs demonstrated benefit against conventional models, simple rules and budget-matched random controls. Negative results can justify a simpler deployment method. The final choice must be frozen on validation before reporting test behavior.

**What can somebody reproduce now?** Exact offline statistics, plots and paired intervals from the published derived archives, with checksum verification and no credentials. Frozen base models and configs also support real-data replay. New LLM outputs are not promised to be bit-for-bit identical. Complete router refitting now reproduces all four model hashes and all 25 policies' validation actions without raw data or API access. Final-test artifacts remain pending.

## Limitations to state without prompting

One Amazon category, sparse histories, review events rather than online impressions, frozen catalog, static-metadata assumption, one dated LLM snapshot, noisy outputs, and nominal development intervals after exploration. The enriched content-control average is not a population estimate. No production uplift, latency improvement, general multi-step value or final adaptive gain has been established.

Before converting this into a final interview story, add the frozen test, representative final failures, measured service latency and reconciled campaign cost. The stronger-base and presentation controls are complete and linked above. The pending serving audit includes both the primary all-base routes and the already frozen active secondary routes; rare generation-branch latency will retain its observation count. The validation-only choice is the causal sequence recommender; it must not be reselected after test. Preserve null and negative results.
