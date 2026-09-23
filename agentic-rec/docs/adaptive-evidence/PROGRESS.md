# Research execution checkpoint

Last updated: 2026-09-23 UTC. The full research goal remains active.

## Authorization and resources

- Branch: `codex/adaptive-evidence-research`; repository default:
  `claude/agentic-recommendation-survey-9afqks`.
- Paid API authorization: **USD 0 total / USD 0 per run**. No cloud rental.
  No paid calls have been made. Stop before any positive-priced request.
- Available local hardware: Ryzen 7 5800H (8 cores / 16 threads), 14.89 GB RAM,
  AMD integrated graphics; no CUDA GPU detected. CPU experiments are the default.
- Cached real model: `Qwen/Qwen2.5-1.5B-Instruct`, revision
  `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, including 3.09 GB weights.
  Availability is verified; inference feasibility and quality are not yet verified.
- No environment API credentials were detected by variable name. Secret values
  were not inspected. Additional budget/permission requests use the task popup.

## Initial audit

- Default branch at `1cacbc738529499a6c979d4f52f0dd0c4254e71d`: reference
  framework and eight adaptive-evidence design documents; all eight read.
- PR [#1](https://github.com/WItaZhang/agentic-rec/pull/1) is open, not merged,
  has no reviews/comments, and its Python 3.11/3.12 CI passed.
- Preserved its original commits `965081d` and `ad35806` by merging its branch
  into this task's branch. The existing PR was not rewritten or merged remotely.
- Fresh isolated clone; no other person's uncommitted project work was touched.

## Milestones

| Stage | Status | Implementation / evidence | Finding / next action |
|---|---|---|---|
| M0 audit and reproduction | validated | Original `ad35806`; local runs `logs/20260923_231823_ml100k_popularity` and `logs/20260923_231847_ml100k_popularity` | Both reproduce original metrics; 42 tests and Ruff pass. Preserve fixed-history, multi-positive protocol as `ml100k_fixed_history_multipositive_v0`. |
| M1a conventional models | in progress | Upcoming ItemKNN validation grid | Freeze validation selection before test; include cold/warm subgroups and paired uncertainty. |
| M1b Amazon coverage | in progress | Downloading complete Magazine_Subscriptions and Digital_Music review files | Select using training-only coverage and compute requirements; do not select on test quality. |
| M1c event replay | planned | Four global time blocks and fixed candidates | Separate target labels and timestamp-batch history updates. |
| M2 real LLM | planned | Zero-paid local feasibility path | Measure actual tokenizer counts and all computation; no mock performance claims. |
| M3–M4 evidence and routing | planned | Conditional on usable evidence variation | Keep fixed, rule and random controls; no obligation to retain a failed complex method. |
| M5 sequential evidence | conditional | No implementation claimed | Only pursue if observations after fetching evidence can improve a decision. |
| M6 report and career materials | planned | Claim ledger tied to completed results | Strong baseline, statistics, ablations, limitations and honest LaTeX. |

## Decisions and limitations

- The user's full-route authorization supersedes the design's instruction to stop
  after one milestone. Changes remain small and independently reviewable.
- M0 test NDCG@10 = 0.25981395087250847, Recall@10 = 0.07377170290648945.
  These are **multi-positive window** metrics, not next-item metrics.
- 235/315 test users have no training history; 454 cold-item positives remain
  misses. This substantially limits what personalization can improve in v0.
- The original input SHA-256 matches the official file; all 100,000 rows used.
- The existing reference framework's mutable candidate tools and character
  counters are unsuitable for claims about fixed-candidate/token-cost research.

## Resume commands

Run from the inner `agentic-rec/` project directory. Inspect this file and
`git status` before resuming; do not rerun final tests to tune against results.

```sh
uv sync --locked --extra yaml --extra experiments
uv run --locked --extra yaml --extra experiments python -m pytest
uv run --locked --extra yaml --extra experiments ruff check .
```

Local raw data, full predictions, models and logs remain git-ignored. Publish
only aggregate evidence and reproducible configurations, with dataset attribution.
