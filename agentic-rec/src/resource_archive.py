"""Replay measured financial/operation accounting without private logs or credentials."""

import gzip
import hashlib
import json
import math

from .operational_accounting import summarize_campaign_operations
from .resource_audit import categorize_usage, reconcile_usage
from .utils import digest, managed_run, write_json

RECORD_FIELDS = ('call_id', 'status', 'usage', 'generation_attempts', 'count_endpoint_calls',
                 'provider_code', 'http_status', 'rejection_stage', 'repair_errors')
LEDGER_FIELDS = ('run_id', 'event', 'reserved_usd', 'actual_usd', 'status',
                 'provider_code', 'reconciliation_evidence_sha256')


def compact_operation_records(records):
    compact = {}
    for row in records:
        if not row.get('call_id') and not row.get('count_endpoint_calls'):
            continue
        result = {key: row[key] for key in RECORD_FIELDS if key in row}
        if not row.get('call_id'):
            result['record_identity_sha256'] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        if 'tool_calls' in (row.get('evidence') or {}):
            result['evidence'] = {'tool_calls': row['evidence']['tool_calls']}
        compact.setdefault(json.dumps(result, sort_keys=True), result)
    return list(compact.values())


def write_accounting_archive(destination, entries, records, settings, report, provenance):
    destination.mkdir()
    values = {'ledger_entries': {key: {k: row[k] for k in LEDGER_FIELDS if k in row} for key, row in entries.items()},
              'operation_records': compact_operation_records(records), 'settings': settings}
    for name, value in values.items():
        (destination / f'{name}.json.gz').write_bytes(gzip.compress(json.dumps(value).encode(), mtime=0))
    write_json(destination / 'expected_accounting.json', {key: report[key] for key in
        ('by_paid_run', 'by_phase', 'total', 'operation_accounting')})
    write_json(destination / 'archive_manifest.json', {**provenance, 'status': 'completed',
        'files': {p.name: digest(p) for p in destination.iterdir()},
        'scope': 'Recompute usage, USD and operation summaries; CPU timings are separately observed, not rerun here.',
        'privacy': 'No prompts, response text, review/user IDs, keys, provider response IDs or provider batch IDs. '
                   'Physical reservation IDs remain to verify deduplication. Preparation/management counters retain source-run names.'})


def compare_accounting(actual, expected, tolerance):
    if not 0 <= tolerance <= 1e-12:
        raise ValueError('Only floating-point summation tolerance is allowed')
    differences = []

    def visit(a, b):
        if type(a) is not type(b):
            return False
        if isinstance(a, dict):
            return a.keys() == b.keys() and all(visit(a[k], b[k]) for k in a)
        if isinstance(a, list):
            return len(a) == len(b) and all(visit(x, y) for x, y in zip(a, b, strict=True))
        if isinstance(a, float):
            differences.append(abs(a - b))
            return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance
        return a == b

    return {'matches': visit(actual, expected), 'max_absolute_float_difference': max(differences, default=0),
            'absolute_float_tolerance': tolerance, 'non_float_fields': 'exact'}


def run_accounting_replay(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        path = root / config['archive_path']
        archive = json.loads((path / 'archive_manifest.json').read_text())
        if archive['status'] != 'completed':
            raise ValueError('Incomplete accounting archive')
        for name, checksum in archive['files'].items():
            if '/' in name or '\\' in name or digest(path / name) != checksum:
                raise ValueError('Accounting archive changed')
        data = {key: json.loads(gzip.decompress((path / f'{key}.json.gz').read_bytes()))
                for key in ('ledger_entries', 'operation_records', 'settings')}
        entries, records, settings = [data[key] for key in ('ledger_entries', 'operation_records', 'settings')]
        usage = reconcile_usage(entries, records)
        result = {'by_paid_run': usage, 'by_phase': categorize_usage(usage, settings['names'], settings['phase_rules']),
                  'total': {key: sum(row[key] for row in usage.values()) for key in next(iter(usage.values()), {})},
                  'operation_accounting': summarize_campaign_operations(entries, records, settings['rank_validated'],
                      settings['repaired'], settings['preparations'], settings['management'])}
        expected = json.loads((path / 'expected_accounting.json').read_text())
        verification = compare_accounting(result, expected, config['absolute_float_tolerance'])
        write_json(run_dir / 'verification.json', verification)
        if not verification['matches']:
            raise ValueError('Financial or operation counters do not reproduce')
        write_json(run_dir / 'accounting.json', result)
        manifest.update(test_scored=False, paid_api_usd=0, llm_calls=0, interim=archive['interim'],
                        numerical_reproduction=verification, archive_sha256=digest(path / 'archive_manifest.json'))
        print(f'Accounting reproduced: {verification}; no dataset, credentials or network requests', flush=True)
