# Asynchronous backend feasibility and output stability

All 32 real batch calls completed. The model and full prompt/schema hashes match
the original synchronous smoke. Both runs used 176,620 input and 1,152 output
tokens. Batch returned the requested `gpt-4.1-mini-2025-04-14` snapshot throughout.
Actual usage priced at the documented batch rates totals **USD 0.0362456**, below
the pre-submission USD 0.0426968 reservation and USD 0.25 round limit. This is a
priced usage estimate, not an invoice. Input/output tokens are provider counts.

Batch turnaround was 139 seconds for the complete job. Individual service latency
is not observable and is stored as null, not zero. The nominal 50% batch discount
is an API pricing property, not a routing-method improvement. Observed synchronous
prefix caching means the paid totals are not exactly in a 2:1 ratio.

Only 7/32 ranking lists exactly matched their synchronous counterparts; mean
candidate-set Jaccard was 0.7892. Thus temperature zero plus a pinned model is not
a guarantee of identical results. This comparison mixes repetition and backend
execution differences and cannot separate them. Its seven distinct users are not
an effectiveness sample. Later validation must distinguish repeat variation from
new-information gains, especially where two evidence plans yield identical input.

The input-preparation and matrix-evaluation path was validated with these already
executed results, without buying another set of generations. Preparation made 14
count-endpoint calls for 32 planned inputs, reusing counts only for hash-identical
payloads. This is token-count caching; generation outputs were not shared between
requests. Recollecting the same batch is idempotent in the USD ledger.

Code sources: submission `00d8fcf`, roundtrip implementation `ea30200`. Exact source
hashes and dirty state are in each manifest; roundtrip's untracked config was then
committed. Aggregate smoke quality is preserved solely to audit the evaluator.
The final Amazon test remains unscored.

Official API documentation: <https://developers.openai.com/api/docs/guides/batch>.
