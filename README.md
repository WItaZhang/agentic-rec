# Projects

| Directory | What it is |
|---|---|
| [`agentic-rec/`](agentic-rec/) | A real-data study of adaptive evidence and LLM-call allocation, alongside a survey of agentic recommender systems and a modular reference framework. |

## Adaptive evidence research

[Adaptive Evidence Acquisition for Agentic Recommendation](agentic-rec/docs/adaptive-evidence/README.md) studies when additional user-history or item evidence is worth its computation cost. The real Amazon temporal pipeline, conventional and LLM baselines, fixed/rule/random/learned evidence allocation, component controls and paired development analyses have run. Published [results and limitations](agentic-rec/reports/adaptive_evidence_study/STUDY.md) include null and negative findings; adaptive improvement is not assumed.

The [presentation control](agentic-rec/reports/20261001_presentation_control/README.md) and stronger-base diagnostic are complete. The frozen final test is running; final quality, controlled serving latency and campaign accounting are not complete. See the [delivery audit](agentic-rec/reports/adaptive_evidence_study/DELIVERY_AUDIT.md) for evidence and remaining requirements, or [reproduce the public statistics](agentic-rec/docs/adaptive-evidence/REPRODUCE.md) offline without API access. The original design remains available in Chinese; implemented scope and results are recorded separately.
