# Real OpenAI protocol smoke (not an effectiveness experiment)

32 actual GPT-4.1-mini-2025-04-14 Responses calls on eight policy-period requests
(seven distinct users; history strata may contain different requests of one user).
All calls completed. Provider usage: 176,620 input and 1,152 output tokens;
frozen-price bill estimate USD 0.069304, below the USD 0.424346 upper estimate and
USD 1 round cap. This is usage-priced cost, not a reconciled provider invoice.
The token-count endpoint matched the response input usage on all 32 calls.
One ranking contained a duplicate ID; deterministic repair was used and logged.
No generation retries, hidden planning, summary, embedding or reflection calls.

Latency at concurrency 1, no application cache: mean 1,652.72 ms, P95 3,361.54 ms,
including token-count request and evidence construction but excluding shared
candidate retrieval in this initial smoke. Automatic provider prefix caching was
observed and counted. Later experiments include retrieval and use concurrency 4;
these smoke latencies are not compared as if the environments were identical.

This stratified convenience sample validates cost, schema, evidence and repair
plumbing only. The metrics JSON is retained for completeness; it supports no
population improvement claim. Final test labels remain unscored. Source 2791754.

Next development pilot uses 256 uniformly hash-sampled users with one eligible
request per user. Recent evidence is one event, full history is up to 20; this
pre-test adjustment follows the training profile's sparse histories (three recent
events would make almost all long-history additions empty). Four calls/request,
fixed ItemKNN top-200, max input 12,000, 256 max output tokens, concurrency 4.
Conservative round upper USD 5.386240, cap USD 6; observed smoke suggests much less.
Measure paired variance and history groups before fixing larger sample sizes.
