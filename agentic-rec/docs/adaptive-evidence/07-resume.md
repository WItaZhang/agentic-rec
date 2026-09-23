# 07 · 完成后的简历与成果表述

[返回设计入口](README.md) · [上一篇：相关工作](06-related-work.md)

**以下是未来完成对应工作后的英文模板，不是当前成果声明。** 本设计提交没有训练控制器，也没有产生推荐提升或成本下降结果。`X`、`Y` 和方括号内容都必须由真实实验替换。

## 1. 推荐算法简历：主版本

项目名建议使用 **Adaptive Evidence Acquisition for Agentic Recommendation**。一页简历可用三条，分别交代任务与方法、实验能力、量化结果。

适用前提：完成真实数据协议、学习请求级路由、必要对照与最终实验报告。以下使用的是请求级路由表述，不隐含逐步停止已经实现。

```latex
\begin{cvitems}
\item Built an agentic recommendation pipeline that augments sequential recommendations with selectively retrieved user-history and item evidence, using a learned routing policy to allocate computation across requests.

\item Evaluated evidence sources and routing strategies through temporal holdouts, component ablations, and budget-matched comparisons against single-pass LLM reranking and fixed workflows.

\item Reduced average inference cost by X\% versus [named baseline], with the NDCG@10 difference within a prespecified non-inferiority margin of [epsilon] on [dataset/category].
\end{cvitems}
```

第三条只有在相应统计结论成立时使用。推理成本要定义清楚：提供方金额、输入 token、输出 token、GPU 时间都不是同一个指标。若只有 token 统计，写具体的 token 指标，不写模糊的 cost。

第二条的 `budget-matched` 也要求实际资源预算相近且已报告差异；只限制相同工具步数时，改为 `controlled-budget comparisons` 并说明预算定义。

## 2. 更适合一页简历的两条版本

如果结果支持质量在预设容差内保持、且输入 token 降低，可以压缩成：

```latex
\begin{cvitems}
\item Developed a learned evidence-routing policy for agentic recommendation, selecting user-history and item information per request; reduced average input tokens by X\% versus [baseline] while maintaining NDCG@10 within a prespecified tolerance on [dataset].

\item Conducted temporal evaluations, evidence ablations, and user-group analyses, identifying [specific, replicated finding] and quantifying its impact on ranking quality and inference cost.
\end{cvitems}
```

这里的 `[specific, replicated finding]` 必须是实际发现。例如你可能最后发现长期历史仅在某类前缀中有帮助，也可能发现它普遍增加噪声；不能在实验前选一个听起来更好的结论。

## 3. 根据最终结果替换结果条

### A. 相同预算下质量提高

```latex
\item Improved NDCG@10 by X\% relative to [baseline] at a comparable measured inference budget on [dataset], with gains concentrated in [validated user group].
```

只有做过并验证分组结论时保留最后半句。相对提升与绝对提升应在报告中都有原始值。

### B. 质量在容差内、资源降低

```latex
\item Reduced average input tokens by X\% and P95 latency by Y\% versus [baseline], while keeping NDCG@10 within a prespecified tolerance on [dataset].
```

只有真实测量过两项资源时才同时写；如果缓存/并发条件不同，不做这个延迟对比。

### C. 更简单的方法胜出

```latex
\item Compared fixed and adaptive evidence acquisition under controlled budgets, finding that [validated simpler method] offered the best measured quality--cost tradeoff on [dataset].
```

这一结果仍体现实验判断能力。写清楚最佳范围和对照集合，避免把有限比较扩展为普遍最优。

## 4. 只有完成逐步控制后才使用的版本

```latex
\item Developed an evidence-acquisition controller that selects history and item-information tools and stops gathering evidence based on the observed context and remaining inference budget.
```

如果只是预先选择 R0–R4，使用 `learned routing policy`。如果动作由规则决定，使用 `rule-based controller`。使用 LightGBM 或其他具体模型，必须与最终实现一致。

## 5. 实现完成但尚无可信量化优势

完成了系统和对照，但收益不明确时，可以写：

```latex
\begin{cvitems}
\item Built a reproducible agentic recommendation pipeline with temporally filtered evidence, fixed retrieval candidates, and per-request token and latency accounting.
\item Benchmarked fixed and adaptive evidence acquisition against conventional recommendation and single-pass LLM reranking, analyzing component effects, user groups, and failure cases.
\end{cvitems}
```

这些句子也要求相应工作实际完成。当前只有设计文档时，不使用过去式把计划当作成果。

## 6. 成果证据表

在最终报告中为每句简历建立记录：

| 简历内容 | 最低证据 |
|---|---|
| learned routing policy | 训练代码、训练/验证边界、特征 schema、检查点、推理路径 |
| temporal evaluation | protocol ID、时间可见性测试、请求和候选清单 |
| comprehensive ablations | 预定义消融矩阵、完成的配置与结果；未做的实验不能算在内 |
| X% quality improvement | 原始指标、基线、相对值计算、样本数、配对不确定性 |
| X% token/cost reduction | 所有调用的 usage、计价方式、失败与重试、离线开销的单独说明 |
| maintained quality | 验证期确定的容差、单侧统计判断与最终测试结果 |
| finding about a user group | 预定义组界限、样本量、组内对照、重复或稳健性检查 |
| dynamic stopping | 工具返回后发生决策的轨迹、停止消融和固定策略对照 |

## 7. 面试时应能回答的问题

1. 为什么用 Agent？单次给足信息的 LLM 表现怎样？
2. 目标没被召回时，Agent 能改善什么？主指标如何计算？
3. 控制器的训练标签哪里来，如何避免看见测试答案？
4. 用户画像、商品评论、历史缓存如何避免未来信息泄漏？
5. 哪个证据源真正有用，结论是否只是因为输入更长？
6. 规则、随机和学习路由分别怎样？复杂度是否值得？
7. 训练标签生成花了多少资源，服务时节省多少，何时收回成本？
8. 最典型的失败是什么？哪些结果否定了最初的直觉？

能用自己的结果回答这些问题，比在项目描述里堆砌工具名更有说服力。
