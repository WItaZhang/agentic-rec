# Recomputable experiment outputs

`pilot_v1` contains real development-pilot outcomes, recorded attempt usage and
the exact analysis settings. It is not a final-test result. Source hashes and
all archived file hashes are in `archive_manifest.json`.

```sh
uv run --locked --extra yaml --extra experiments python main.py --config configs/pilot_archive_reanalysis.yaml
```

This regenerates the tables, user-bootstrap intervals and plot with no raw-data,
model, credential or API access. Numerical equality with the archived analysis
is required. This was actually verified at
`logs/20260924_011719_pilot_archive_reanalysis`; source/output provenance remains
in the archive. Compressed files preserve exact JSON floats and ordering.

User IDs are replaced with per-artifact ordinals preserving their original sort
order, so seeded bootstrap draws remain identical. Ordinals must not be used to
join users across different archives; stable request IDs identify repeated
requests. No review text, input prompts, credential values or provider response
IDs are published. Candidate item identifiers in rankings are derived outputs
from Amazon Reviews 2023, attributed in the reproduction guide.

Actual offline generation counts and spend must be deduplicated by `call_id`.
Logical plans can share one physical outcome at the same request. Failed calls
and unknown usage reservations are retained. Replaying these files is analysis,
not a new generation experiment or an online latency measurement.

`.gitattributes` disables newline conversion for artifacts so their recorded
checksums survive checkout on both Windows and Unix systems.
