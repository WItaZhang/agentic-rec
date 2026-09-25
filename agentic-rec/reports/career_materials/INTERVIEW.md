# Interview explanation — supported results and pending claims

## 90-second explanation

我研究的是推荐请求是否值得花额外计算获取证据。不同用户的历史长度、候选排序和信息缺口不同，把所有历史与商品信息一律塞给 LLM，可能既贵又降低质量。

我先建立真实 Amazon 评论事件的时间回放流程，用全局时间边界隔离基础模型训练、策略训练、验证和测试。基础模型只用训练期数据生成 top-200 候选，各证据方案在同一份候选上比较，不补入真实目标。未召回、冷物品、失败请求都保留在分母中。

目前已完成的 3,318 用户验证显示：近期历史单次重排相对 ItemKNN 的 NDCG 差只有 +0.00061，区间跨零；充分证据反而下降 0.02656。分组结果也有差异：空历史请求的轻量重排略有收益，多事件历史组则明显受损。我又做了输入 token 完全相同的类别打乱对照，发现正确类别对应在有历史组优于打乱对应，空历史组却相反。这说明内容对应关系和请求状态有影响，但不能说增加信息普遍有效。

因此我的方法选择以证据为准：继续比较规则、成本匹配的随机分配和学习路由；如果复杂方法没有可靠收益，就采用验证集支持的简单方法。目前路由实现和冻结协议已完成，完整训练数据与最终测试仍在等待 API 账户额度恢复。我不会把这个状态描述成已经验证了自适应收益。

## English explanation

“I studied when a recommendation request is worth an additional LLM call and what evidence that call should receive. I built a temporal replay pipeline with global training, policy-training, validation, and test windows. Every evidence treatment used the same retrieved candidates, and missing targets, cold items, and failed requests stayed in the denominator.

“On 3,318 validation users, a recent-history reranker did not establish an aggregate improvement. Supplying full evidence reduced NDCG@10 by 0.02656. The direction varied by history group. I then held actual input-token counts fixed while shuffling candidate-category associations. Correct alignment helped relative to corrupted alignment for users with history, but the direction reversed for empty histories. Full evidence still trailed the conventional baseline.

“My contribution is the controlled evaluation and the decision framework, rather than an assumed LLM gain. The next comparison is a frozen rule, a cost-matched random allocator, and a learned utility router. Those expanded routing and final-test results are not complete yet, so I would not claim a validated adaptive improvement.”

## Problem and hypotheses

- **Question:** What additional evidence does a request need, and can a policy allocate evidence and model calls better than a fixed workflow at comparable measured cost?
- **H1:** Evidence can improve some requests. Current evidence: heterogeneous development effects; no aggregate recent-evidence gain established.
- **H2:** Observable request features predict useful actions. Current status: feature extraction and learning pipeline tested, expanded real policy labels incomplete. Group heterogeneity alone does not prove learnability.
- **H3:** Decisions improve quality–cost tradeoffs. Current status: rule/random/learned comparison pending; no cost-saving claim yet.
- **H4:** Decisions after seeing tool results justify multiple steps. No observed evidence currently establishes this; no multistep ability is claimed.

## Method and fair controls

The task predicts the next positive, previously unseen reviewed item (rating at least four). ItemKNN is the main candidate generator; popularity and a causal Transformer provide conventional controls on their own candidate pools. Comparing different retrievers measures the whole recommendation pipeline, while evidence comparisons keep the main pool fixed. The earlier MovieLens experiment uses a different multi-positive protocol and its scores are not comparable with Amazon next-item scores.

The executable action space is R0 (no LLM), R1 (latest history event plus candidate titles), R2 (up to 20 recent events plus titles), R3 (R1 plus categories), and R4 (R2 plus categories). R4 is deterministic local evidence assembly followed by **one** LLM rerank. It is not multistep planning. R2 uses the last 20 events; it is not semantic memory retrieval.

The planned learned router estimates each action's NDCG difference from R0 using ten target-free history and base-score features. Ridge and histogram boosting are fitted on earlier policy labels, with inclusion weights for the history-enriched training sample. A dollar penalty trades expected gain against cost. Validation selects from the registered grid; final test cannot change it. Random allocation matches observed validation spending in expectation, so realized test costs must still be reported. The practical method is selected separately across conventional and routed candidates using the registered validation tolerance and simplicity rule.

## Questions to expect

**Why can empty-history requests benefit from R1?** R1 still provides candidate titles and the base-model order. For an empty history its effect is title/prior reranking, not personalization. This is a key interpretation limit.

**Why does more evidence hurt?** The observed ablation establishes a treatment effect for this prompt, data slice and model. It does not identify one universal cause. Coarse crawler categories, context distraction, review-to-preference mismatch and preservation of useful base order are plausible explanations. The equal-token control shows that correct correspondence matters differently by group; it does not remove every confound between information content and neutral token padding.

**Is the oracle gain evidence for a learning policy?** No. It chooses actions using true outcomes and includes model-output noise. In the pilot, 118 of 489 same-request repeated-input groups changed ranking even at temperature zero. A deployable router never sees current targets or counterfactual quality.

**How do you prevent leakage?** Base weights and item catalog stop at the base cutoff. History events must be strictly earlier than the prediction timestamp; tied events become visible only after their predictions. Candidate snapshots and route choices are saved before labels are consulted. Current review text, current rating and target ID cannot enter prompts or routing features. Earlier feedback is allowed only when it has become causally visible.

**What is the largest remaining visibility risk?** Product titles/categories come from a later crawler snapshot. They are treated as static, not historically timestamped attributes. This assumption and possible model pretraining contamination must remain explicit. Dynamic price, average rating and review-count fields are excluded.

**Why keep unrecalled and cold targets?** Reranking cannot recover a target absent from candidates. Dropping such requests would overstate end-to-end quality and hide wasted calls. In population validation, 1,480 of 3,318 targets were not retrieved, including 418 cold targets. These labels can explain failures after evaluation; they cannot guide routing at prediction time.

**What did failure analysis reveal?** The [completed validation audit](../20260925_validation_failures/README.md) shows that full evidence loses 388 original base hits while rescuing 196; recent evidence loses 38 while rescuing 49. Approximately 44.6% of each scheme's measured API cost is spent on unrecalled targets. An empty-history example drops *Family Handyman* from base rank five, while another promotes *Food Network Magazine* from rank eleven to five. These fixed-hash selected cases illustrate mixed effects; they neither explain the model's private reasoning nor prove that a router can identify the useful calls.

**Does a confidence interval crossing zero mean no loss?** No. It means the experiment did not establish a difference at that precision. A quality-preservation claim requires the registered one-sided noninferiority test against a 0.002 NDCG margin. The validation selection tolerance is a decision rule, not a statistical equivalence claim.

**How is cost measured?** Provider input/output/cached-token usage and persistent attempt reservations, including failures. Batch labeling is offline construction cost; it is separated from counterfactual per-request API cost, controller training and local CPU. Batch turnaround is not serving latency. Mean/P95 service latency requires the separate fixed-concurrency synchronous audit, which has not yet run.

**Why not deploy the most complicated method?** Complexity needs demonstrated benefit against conventional models, simple rules and budget-matched random controls. Negative results can justify a simpler deployment method. The final choice must be frozen on validation before reporting test behavior.

**What can somebody reproduce now?** Exact offline statistics, plots and paired intervals from the published derived archives, with checksum verification and no credentials. Frozen base models and configs also support real-data replay. New LLM outputs are not promised to be bit-for-bit identical. Complete router refitting and final-test artifacts will only be claimed after their actual execution.

## Limitations to state without prompting

One Amazon category, sparse histories, review events rather than online impressions, frozen catalog, static-metadata assumption, one dated LLM snapshot, noisy outputs, and nominal development intervals after exploration. The enriched content-control average is not a population estimate. No production uplift, latency improvement, general multi-step value or final adaptive gain has been established.

Before converting this into a final interview story, add the completed policy comparison, strong-base evidence result, frozen test, representative failures, measured service latency, reconciled campaign cost, and the actual chosen method. Preserve null and negative results.
