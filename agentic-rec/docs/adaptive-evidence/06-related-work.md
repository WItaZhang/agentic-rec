# 06 · 相关工作与研究边界

[返回设计入口](README.md) · [上一篇：路线图](05-roadmap.md) · [下一篇：简历](07-resume.md)

资料核对日期：2026-09-23。本页用于定位工作和选择评估方法，不是完整文献综述，也不构成“本项目方法新颖”的证明。

## 1. 最相关的系统与基准

| 工作 | 已有内容 | 对本项目的意义 |
|---|---|---|
| [InteRecAgent / RecAI](https://github.com/microsoft/RecAI/tree/main/InteRecAgent)，[论文](https://doi.org/10.1145/3731446) | 以 LLM 规划连接查询、召回、排序等工具 | 参考工具边界和固定工作流；简化移植需标为 adaptation，不能冒称完整复现 |
| [ChainRec](https://arxiv.org/abs/2602.10490)，[全文](https://arxiv.org/html/2602.10490v1) | 学习工具选择、调用顺序和停止，训练中已有工具步数成本惩罚 | 自适应与成本感知本身已有直接相关工作；本项目重点在轻量控制、实际计量与真实候选的实证验证 |
| [AgentRecBench 最终 NeurIPS 2025 论文](https://papers.neurips.cc/paper_files/paper/2025/file/e2d6f7249add096e26679eade1b4cc6f-Paper-Datasets_and_Benchmarks_Track.pdf)，[数据](https://huggingface.co/datasets/SGJQovo/AgentRecBench) | Amazon、Goodreads、Yelp 上的工具推荐任务，包括冷启动和兴趣变化场景 | 可作为标准化的第二评估；其每任务 1 正例 + 19 未交互候选属于采样重排，与真实召回协议分开报告 |
| [τ-Rec 论文](https://arxiv.org/abs/2606.10156)，[代码](https://github.com/nbharaths/tau-rec) | 结构化模拟会话任务及约束/工具使用评估 | 适合作为后续交互可靠性评估；模拟任务成功不能替代真实行为排序质量 |

建议阅读顺序：先了解 InteRecAgent 的工具分工，再读 ChainRec 的状态、动作、训练目标和实验协议，然后看 AgentRecBench 的数据构造。对 ChainRec 的作者代码可用性需要在实现阶段重新核对；本次检查未确认可直接运行的作者实现。

## 2. 数据和评估依据

| 来源 | 需要关注的内容 |
|---|---|
| [Amazon Reviews 2023 官方站点](https://amazon-reviews-2023.github.io/) | 数据 schema、品类、时间戳、元数据字段和来源条件 |
| [Amazon 官方切分说明](https://amazon-reviews-2023.github.io/data_processing/0core.html) | 按用户切分与绝对时间切分的区别；前缀历史的构造 |
| [GroupLens MovieLens 数据集](https://grouplens.org/datasets/movielens/100k/) | 现有工程基础的数据、引用和使用说明 |
| [Ji et al., temporal leakage analysis](https://arxiv.org/abs/2010.11060) | 仅按用户留出最后事件不一定阻止跨用户未来信息进入训练 |
| [Krichene & Rendle, On Sampled Metrics for Item Recommendation](https://research.google/pubs/on-sampled-metrics-for-item-recommendation/) | 随机负采样指标与完整排序指标可能给出不同模型比较结论 |
| [How Reliable Is Your Simulator?](https://arxiv.org/html/2403.16416v1) | 对话历史和模拟回复可能泄漏推荐目标，模拟成功需要单独审计 |

相关论文能说明某种风险值得检查，不能替代对本仓库实现的测试。这里的四段切分、工具接口、实验矩阵和阶段门槛是本项目建议的设计，不是某一篇论文的原样方案。

## 3. 可以主张什么

完成相应实现与实验后，可以根据证据主张：

- 实现了带时间可见性与固定候选约束的 Agentic 推荐实验系统。
- 比较了不同证据方案、单次重排、固定工作流与自适应策略。
- 学习了请求级证据路由，或进一步学习了逐步取证和停止。
- 在明确的数据、模型与预算条件下测得质量和资源使用的变化。
- 发现某类证据的收益集中于某些请求，或复杂策略未优于简单方法。

## 4. 暂时不能主张什么

- “首次提出预算感知 Agentic 推荐”：相关思路已有先例，需要更完整的新颖性论证。
- “提升线上 CTR/转化”：离线评论预测没有真实曝光随机实验。
- “解决兴趣漂移”：前缀分布差异只是代理，需要更具体定义和验证。
- “数值复现多个论文”：当前结构配方与 mock 测试不等于原论文训练/数据结果。
- “动态多步规划”：只实现一次请求级方案选择时不成立。
- “无损降本”：需要预先定义质量容差、统计支持和完整资源计量。
- “泛化到多个领域/模型”：只测试一个品类或一个 LLM 时不成立。

## 5. 未来若希望发展成论文

先完成本设计的可复现实验，再判断是否出现一个足够具体的新问题。例如：真实召回缺失如何改变 Agent 的有效调用空间，证据收益能否在跨时间段迁移，或者哪些可观测特征可以稳定预测信息价值。

这些只是可能的研究线索。需要扩大文献核对、建立针对性基线，并用独立实验检验，才能讨论正式研究贡献。作为求职项目，清楚的问题、可靠实现与可信结论已经是独立的价值。
