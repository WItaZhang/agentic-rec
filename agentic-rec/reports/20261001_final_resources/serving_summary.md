# Observed synchronous service measurements

Warm resident models; same validation users and interleaved methods. Replay summarizes saved observations, not new timings.

| Method | Requests | Calls | Mean ms | P95 ms | Generation-branch mean ms | Generation-branch P95 ms | API USD/1,000 |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 128 | 0 | 5.709 | 8.205 | not observed | not observed | 0.000000 |
| causal_sequence | 128 | 0 | 5.023 | 8.369 | not observed | not observed | 0.000000 |
| full | 128 | 128 | 3229.286 | 4403.190 | 3229.286 | 4403.190 | 1.897309 |
| learned | 128 | 0 | 6.722 | 10.350 | not observed | not observed | 0.000000 |
| learned_1.5 | 128 | 4 | 100.765 | 21.618 | 2759.065 | 3732.105 | 0.051394 |
| popularity | 128 | 0 | 1.080 | 1.582 | not observed | not observed | 0.000000 |
| random | 128 | 0 | 5.655 | 8.234 | not observed | not observed | 0.000000 |
| random_1.5 | 128 | 7 | 124.506 | 1002.769 | 2173.782 | 2458.540 | 0.028381 |
| recent | 128 | 128 | 3112.006 | 4315.427 | 3112.006 | 4315.427 | 0.736125 |
| rule | 128 | 0 | 5.598 | 8.075 | not observed | not observed | 0.000000 |
| rule_1.5 | 128 | 115 | 2785.327 | 4104.982 | 3099.597 | 4135.062 | 0.634375 |

Overall summaries retain zero-call requests. Rare generation-branch percentiles are descriptive and may rest on very few observations.
Automatic provider prefix-cache usage is recorded separately; application output reuse is disabled. Batch prices and turnaround are not substituted here.
