# 03 · 实现设计

[返回设计入口](README.md) · [上一篇：数据协议](02-data-and-evaluation.md) · [下一篇：实验](04-experiments.md)

本文件中的目录、接口、配置与命令是**拟实现设计**。不要将示例视为当前仓库已有 API。现有 MovieLens 实验与本设计的对应关系见 [路线图](05-roadmap.md)。

## 1. 现有组件的复用与适配

| 现有位置（相对 `agentic-rec/`） | 当前能力 | 本方案的处理 |
|---|---|---|
| `agentic_rec/core/types.py` | 用户、交互、推荐列表等基础类型 | 新增受限的请求视图；不把含未来事件的完整 `User` 交给策略 |
| `agentic_rec/tools/builtin.py` | 历史、属性、检索、过滤、排序工具 | 加时间检查与固定候选适配器；保留原结构示例行为 |
| `agentic_rec/planning/` | 多种规划流程 | 复用执行骨架；新增请求级策略，后续再接逐步控制器 |
| `agentic_rec/memory/` | 多种记忆组织 | 添加来源、历史水位、去重与预算；第一版先用确定性选择 |
| `agentic_rec/llm/base.py` | 文本接口，调用数/字符数统计 | 增加结构化调用结果与 usage；字符不能当 token |
| `agentic_rec/llm/http.py` | 真实模型 HTTP 适配 | 保留提供方 usage、响应标识、延迟、重试及错误信息 |
| `agentic_rec/evaluation/` | 排序/模拟指标 | 复用可验证的纯指标，新增用户宏平均与分母审计 |
| PR #1 的 `src/` | 真实数据实验分层 | 作为 ML 实验入口；通过 adapter 调用参考框架 |

当前 `search`/`retrieve` 会写候选总线，`filter` 的空交集可能回退到更广的集合。因此不能仅在报告中写“候选固定”就认为约束成立；需要单独的只读候选视图和输出校验。

不要把实验逻辑全部塞进原合成数据 CLI。参考框架继续支持现有 TOML 示例；真实实验由 YAML 驱动，身份和产物分开。

## 2. 推荐目录

```text
agentic-rec/
├── .python-version
├── pyproject.toml
├── uv.lock
├── configs/
│   ├── ml100k_popularity.yaml           # 已有 PR 中的工程基线
│   ├── ml100k_itemknn.yaml              # 拟新增
│   ├── amazon_<domain>_pilot.yaml       # 拟新增；每份文件包含完整配置
│   └── amazon_<domain>_adaptive.yaml
├── data/
│   ├── raw/                            # 只读原始数据，不提交
│   ├── processed/                      # 清洗事件、分割、候选与标签清单
│   └── staging/                        # 证据缓存、下载中间文件、索引缓存
├── logs/
│   └── YYYYMMDD_HHMMSS_<experiment>/
├── reports/                            # 经筛选的聚合结果与图，不存原始运行转储
├── src/
│   ├── data.py                         # 加载、schema 校验、时间切分
│   ├── feature.py                      # 纯特征变换，无 I/O 和模型调用
│   ├── model.py                        # 基础模型、路由模型定义，无训练循环
│   ├── trainer.py                      # 训练、评估编排、保存/加载检查点
│   ├── protocol.py                     # 请求构造、可见性与候选约束
│   ├── evidence.py                     # 证据库查询、来源与预算化选择
│   ├── policy.py                       # 规则/固定/学习策略的推理接口
│   ├── adapter.py                      # 实验对象到现有 Agent/LLM 接口
│   ├── telemetry.py                    # 调用计量、usage 与失败记录
│   ├── metrics.py                      # 纯指标函数、聚合、bootstrap
│   └── utils.py                        # 配置、路径、种子、日志与哈希
├── main.py                             # 加载 config → 构建依赖 → 调 trainer
├── agentic_rec/                        # 原有参考框架
└── tests/                              # 离线协议测试与受控适配器测试
```

这是职责建议，不要求预先创建全部空文件。先实现一个可运行的阶段，再按需求增加模块。规模增长后可将 `model.py`、`trainer.py` 拆为包，但模型定义与训练逻辑仍分离。

## 3. 核心数据对象

### 3.1 请求与标签隔离

```python
# 接口草案，尚未实现
@dataclass(frozen=True)
class RequestView:
    request_id: str
    user_id: str
    prediction_time: int
    history_snapshot_id: str
    candidate_snapshot_id: str
    protocol_id: str

@dataclass(frozen=True)
class EvaluationTarget:
    request_id: str
    target_item_id: str
    target_event_id: str
```

`EvaluationTarget` 仅由评估器加载。控制器构造函数不接收标签路径，工具查询不能访问标签目录。生成标签的离线训练作业与在线形态的策略推理使用不同入口。

### 3.2 候选视图

```text
CandidateSnapshot
  snapshot_id
  request_id
  item_ids[]                 # 不可变成员
  base_scores[]
  base_order[]
  display_order[]            # 可做共享的呈现顺序消融
  local_alias_to_item_id     # 模型只看到 c001 等局部别名
  model_checkpoint_hash
  catalog_snapshot_hash
  content_hash
```

将成员资格与当前排序分开存储。Agent 可以返回新的排序，不能原地改变成员集合。历史物品证据与候选商品使用不同字段，避免历史工具无意扩展候选。

### 3.3 证据对象

```text
EvidenceRecord
  evidence_id
  request_id
  kind                      # recent_history / long_history / metadata / review
  subject_ids[]
  source_event_ids[]
  source_max_timestamp      # 对事件证据必填
  visibility_basis          # timestamped / snapshot_assumed_static
  snapshot_id
  selection_rule_version
  text_or_structured_payload
  truncated
  missing_fields[]
```

证据构造器负责时序检查；模型不能自行决定某条未来信息“看起来可以用”。无时间戳的元数据必须经过字段白名单，不能通用地跳过检查。

### 3.4 策略接口

```python
# 接口草案，尚未实现
class EvidencePolicy(Protocol):
    def decide(self, state: PolicyState) -> PolicyDecision: ...

class EvidenceStore(Protocol):
    def fetch(self, request: RequestView, action: EvidenceAction) -> EvidenceBatch: ...

class Reranker(Protocol):
    def rank(self, request: RequestView,
             candidates: CandidateSnapshot,
             evidence: EvidenceBundle,
             budget: BudgetState) -> RankingResult: ...
```

规则、随机、固定和学习策略实现同一个 `decide`。请求级方案路由只调用一次，逐步控制器在每个允许的状态变化后调用。`PolicyDecision` 应有有限 action 类型、受约束参数、策略版本和短原因标签，不依赖自由文本解释解析。

## 4. LLM 与计量接口

现有公开 `complete()` 返回字符串。可以保留其兼容接口，在内部新增结构化 `CompletionResult`，或增加一个实验适配器；不要为了计量破坏全部结构示例。

```text
CompletionResult
  text
  provider
  requested_model
  response_model
  provider_request_id
  system_fingerprint        # 提供方返回时记录
  usage:
    input_tokens
    output_tokens
    cached_input_tokens
    reasoning_tokens
    reported_total_tokens
    source                  # provider / tokenizer_estimate / unavailable
  elapsed_ms
  status                    # success / timeout / rate_limited / parse_error / ...
```

缺失字段为 `null`，不是 0。明确 cached/reasoning token 是否已包含在输入/输出总数中，避免重复计费；不同提供方的 usage 语义需要适配器单独记录。

每次尝试都生成 span，包括最终抛错的请求。`calls` 不能只统计成功响应。重试、修复、规划、反思、摘要与 embedding 等调用分别标记角色。

### 4.1 Span 与请求汇总

```json
{
  "schema_version": "planned-v1",
  "run_id": "example-only",
  "request_id": "q-example",
  "span_id": "s-example",
  "parent_span_id": null,
  "component": "rerank",
  "attempt": 1,
  "status": "not_executed",
  "input_tokens": null,
  "output_tokens": null,
  "usage_source": "unavailable",
  "latency_ms": null,
  "estimated_usd": null,
  "price_table_id": null
}
```

这是 schema 示例，没有实际调用或费用。详细 prompt 默认保存在本地受控日志中，公共报告只发布必要、允许分享的样本。结构化动作、输入证据 ID、结果及简短原因标签足以支撑审计，无需依赖隐藏推理文本。

### 4.2 请求预算

`BudgetState` 至少记录：剩余工具步数、已知 token 使用、预计最终调用额度、已知金额、预算是否可准确计算。

- 支持每请求上限和整轮实验上限。
- token 无法精确获知时记录估计类型，用保守的输出上限预留；不能宣称严格实际金额上限已被证明。
- 超时/重试也可能产生费用，日志不能丢失这些尝试。
- 缺失价格、usage 或模型信息时禁止生成精确美元节省结论。
- 并发下采用中心预算预留/结算，避免多个请求同时超出总预算。

## 5. YAML 配置草案

以下仅展示所需字段，**不是当前可运行配置**。`null` 为实现/预注册前必须解决的值；解析器应在运行前失败，而不是自动补一个隐藏默认值。

```yaml
schema_version: planned-v1
experiment_name: amazon_adaptive_evidence_pilot
seed: 42
protocol:
  id: amazon_next_positive_unseen_v1
  timezone: UTC
  positive_rating: 4
  exclude_previously_interacted: true
  history_update: after_timestamp_batch
  aggregation: user_macro
data:
  dataset: amazon_reviews_2023
  category: null
  raw_path: data/raw/amazon/
  processed_path: data/processed/amazon/
  staging_path: data/staging/amazon/
  input_manifest: null
  base_train_end: null
  policy_train_end: null
  validation_end: null
  test_end: null
  metadata_policy: static_allowlist
  allowed_metadata_fields: [title, categories, features]
  excluded_snapshot_fields: [price, average_rating, rating_number]
model:
  retriever: itemknn
  retriever_checkpoint: null
  candidate_count: 100
  top_k: 10
  candidate_membership: frozen
  candidate_display_order: base_rank
controller:
  mode: fixed_route              # 首轮比较固定方案，之后再改 learned_route
  route: recent
  routes: [base, recent, recent_long, recent_metadata, full]
  model_type: null
  checkpoint: null
  utility_cost_measure: estimated_usd
  utility_lambda: null
  feature_schema: null
evidence:
  recent_event_limit: 20
  long_event_limit: 20
  selector: deterministic
  duplicate_policy: source_id
  item_reviews_enabled: false
  snapshot_metadata_assumption: declared_static
llm:
  enabled: false                 # 明确启用并填写预算后才可调用
  provider: null
  model: null
  endpoint: null
  prompt_file: null
  prompt_hash: null
  temperature: 0
  max_output_tokens: null
  timeout_seconds: null
  max_attempts: 1
  repair_attempts: 0
budget:
  total_usd: null
  total_calls: null
  per_request_token_cap: null
  per_request_tool_steps: 3
  price_table: null
  reserve_final_call: true
train:
  stage: evaluate_fixed_routes
  policy_model_hyperparameters: {}
  normalization_artifact: null
evaluation:
  request_manifest: null
  primary_metric: ndcg_at_10
  secondary_metrics: [hr_at_10, candidate_recall_at_100]
  paired_bootstrap_unit: user
  bootstrap_repetitions: 2000
  confidence_level: 0.95
  quality_noninferiority_margin: null
  fallback: base_order
runtime:
  concurrency: 1
  cache_mode: cold
logging:
  root: logs
  store_raw_prompts: false
  spans: true
  git_provenance: true
```

`M=100`、历史 20 条和 bootstrap 2000 次仅为初始建议；实际配置在开发阶段决定。每份实验 YAML 应完整描述运行，若后续引入继承，要把最终展开配置也写入日志。

认证密钥可以来自明确记录的环境变量例外，例如提供方 API key；它们不属于实验超参数且绝不写入配置副本。模型、endpoint、温度、预算、路径与切分仍由 YAML 决定，不能偷偷受环境变量或 CLI 覆盖。

## 6. 环境与运行入口

ML 实验使用 `uv` 管理；`uv.lock` 是环境依据，需要提交。新增依赖通过 `uv add`，按照用途放入实验 extra 或开发组，避免破坏参考框架的轻量安装方式。具体 extra 名以实现提交为准。

现有 PR 合入/选用后，可以按其文档执行 `uv sync --locked --extra yaml`。本计划新增的路由训练和回放命令尚未实现。

未来入口保持单一配置选择：

```text
# 目标用法，待实现相应配置与阶段后才可运行
uv run python main.py --config configs/<complete_experiment>.yaml
```

`main.py` 只加载与连接模块。数据变换、训练、API 调用、指标和报告生成不写在入口里。

## 7. 每次运行的产物

```text
logs/YYYYMMDD_HHMMSS_<experiment>/
├── config.yaml                 # 实际展开配置，不含密钥
├── manifest.json               # Git、lock、输入、候选、prompt、模型版本/hash
├── run.log                     # stdout/stderr
├── metrics.json                # 总体、分组、分母、失败数
├── predictions.jsonl           # 请求/排序/方案/状态；不放未来证据
├── spans.jsonl                 # 所有尝试、工具、计量与预算
├── evidence_manifest.jsonl     # 来源 ID、水位、选择器版本
├── model/                      # 本轮产生的检查点
├── statistics.json             # bootstrap 和预定义比较
└── failure.json                # 仅失败时，含阶段与可恢复信息
```

`data/processed/` 保存可复用的清洗/切分/候选清单，`data/staging/` 保存缓存，`logs/` 保存本轮运行产物。源代码目录不承载这些输出。

同秒并发运行不能覆盖目录，可使用原子创建并追加稳定唯一后缀。恢复运行必须核对配置、候选和模型哈希，跳过已经完成的 request/method/repeat 键，记录恢复事件；不能把部分失败静默丢掉。

## 8. 验证策略

优先写会影响结论的测试：时间泄漏、候选不变、标签隔离、已知指标、失败计费、回退分母、缓存水位、预算停止、可复现抽样。

Mock LLM 用于协议和控制流测试，不能验证真实模型的记忆、反思或排序收益。受控 HTTP 响应 fixture 用于检查 usage 解析与重试；真实提供方的小样本冒烟测试单独记录，不进入默认离线 CI。

一次文档变更不要求训练模型。本方案的实现提交应按改动范围运行离线测试、静态检查和相应小规模实验，再考虑扩大样本。
