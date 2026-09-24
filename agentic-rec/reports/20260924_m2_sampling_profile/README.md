# Label-blind user-state coverage

Source `7f59558`; this run reads only development-period request histories and
performs no ranking evaluation. It selects one hash-random request per user before
counting history strata. The final test is excluded.

| Period | Users | No history | One event | At least two events |
|---|---:|---:|---:|---:|
| Policy training | 8,272 | 7,355 | 656 | 261 |
| Validation | 3,318 | 2,968 | 247 | 103 |

These are states of sampled requests, not permanent user categories. The event-level
zero-history percentages in the earlier replay report have a different denominator.
Uniform small user samples will contain very few opportunities for extra historical
evidence. Future policy-label sampling can include every warm user-state plus a
random cold-state sample, with inverse inclusion weights for fitting. Evaluation
must retain the population distribution and all cold/OOV/missed/failed cases.

Select the one request per user *before* stratifying, so a user cannot enter two
strata. The seven-user/eight-request protocol smoke did not impose that restriction;
it remains an engineering smoke, not a population study. Exact quotas and final
sample sizes will be recorded after the variance pilot, before final testing.
