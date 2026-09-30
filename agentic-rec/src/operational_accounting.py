"""Stateless operation counters; physical calls remain the deduplication unit."""

import hashlib
import json

from .paid_budget import usage_cost


def incremental_polls(state, predecessor=None):
    previous = (predecessor or {}).get('poll_calls', 0)
    current = state.get('poll_calls', 0)
    if not isinstance(current, int) or not isinstance(previous, int) or not 0 <= previous <= current:
        raise ValueError('Scheduler polling counter regressed across resume')
    return current - previous


def verify_recorded_prices(entries, records, prices):
    usages = {}
    for row in records:
        if row.get('call_id') and row.get('usage') is not None:
            identity = row['call_id']
            if identity in usages and usages[identity] != row['usage']:
                raise ValueError('Conflicting usage in price verification')
            usages[identity] = row['usage']
    differences, measured = [], []
    for identity, usage in usages.items():
        entry = entries[identity]
        actual = entry.get('actual_usd')
        estimate = usage_cost(usage, prices[entry['run_id']])
        if actual is None or estimate != actual:
            raise ValueError('Recorded charge differs from observed usage and its frozen pricing')
        differences.append(abs(estimate - actual))
        measured.append(estimate)
    return {'physical_calls_repriced': len(usages), 'recomputed_known_usd': sum(measured),
            'maximum_per_call_difference_usd': max(differences, default=0),
            'scope': 'Provider token usage times the recorded dated-model standard/Batch price table, not invoice reconciliation. '
                     'Unknown usage and explicit pre-generation zero-charge rejections remain separate.'}


def summarize_operations(entries, records, rank_validated, repaired):
    generations, count_calls, evidence = {}, {}, {}
    count_only = {}
    validated, repairs = set(rank_validated), set(repaired)
    for row in records:
        identity = row.get('call_id')
        counts = row.get('count_endpoint_calls', 0)
        if not isinstance(counts, int) or counts < 0:
            raise ValueError('Invalid recorded preflight count')
        if not identity:
            if counts:
                if row.get('generation_attempts', 0) or row.get('usage') is not None:
                    raise ValueError('A generation record cannot omit its reserved physical identity')
                # Resumed journals can contain the exact original count-only error.
                key = row.get('record_identity_sha256') or hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
                count_only[key] = counts
            continue
        if identity not in entries:
            raise ValueError('Operation record missing its budget reservation')
        count_calls[identity] = max(counts, count_calls.get(identity, 0))
        attempts = row.get('generation_attempts', int(row.get('usage') is not None))
        if attempts not in (0, 1):
            raise ValueError('One reserved physical call must represent at most one generation')
        generations[identity] = max(attempts, generations.get(identity, 0))
        tools = (row.get('evidence') or {}).get('tool_calls')
        if tools is not None:
            if not isinstance(tools, int) or tools < 0:
                raise ValueError('Invalid local evidence-access counter')
            if identity in evidence and evidence[identity] != tools:
                raise ValueError('Shared physical call has conflicting local evidence access')
            evidence[identity] = tools
        if 'repair_errors' in row:
            validated.add(identity)
            if row['repair_errors']:
                repairs.add(identity)
    if not repairs <= validated or not validated <= set(entries):
        raise ValueError('Ranking-validation identity is not a reserved physical call')
    generated = {identity for identity, attempts in generations.items() if attempts}
    return {
        'physical_generation_attempts_recorded': len(generated),
        'generation_status_failures_or_incomplete': sum(entries[i].get('status') != 'completed' for i in generated),
        'synchronous_token_count_calls_with_reserved_identity': sum(count_calls.values()),
        'count_only_error_operations': sum(count_only.values()),
        'generated_calls_with_local_evidence_counter': len(generated & set(evidence)),
        'logical_local_evidence_accesses_for_generations': sum(evidence[i] for i in generated & set(evidence)),
        'generated_calls_with_ranking_validation': len(generated & validated),
        'physical_outputs_repaired_or_replaced_by_fallback': len(generated & repairs),
        'scope': 'Physical IDs deduplicate resumed, collected and counterfactual aliases. '
                 'Local evidence counters describe history/title/category accesses, not external HTTP tool calls '
                 'or all offline prompt constructions. Repair count includes fallback validation. '
                 'Coverage counts disclose calls not yet evaluated or older calls without matching evidence/ranking records. '
                 'Exact copied count-only error rows are deduplicated; token-count-only requests have no generation reservation.'}


def summarize_campaign_operations(entries, records, rank_validated, repaired, preparations, management):
    operations = summarize_operations(entries, records, rank_validated, repaired)
    operations.update(matrix_preparation_token_count_calls_known=sum(r['count_endpoint_calls'] or 0 for r in preparations.values()),
        preparation_runs=preparations,
        preparation_runs_without_complete_count=[name for name, row in preparations.items() if row['count_endpoint_calls'] is None],
        management_by_run={name: row for name, row in management.items() if any(row.values())},
        management_totals={key: sum(row.get(key, 0) for row in management.values())
                           for key in {k for row in management.values() for k in row}},
        management_scope='Recorded SDK operations/receipts, not total HTTP requests. Pagination, transport-level exchanges '
                         'and manual provider diagnostics outside managed runs are not fully metered. '
                         'Resume polling totals subtract inherited counters; recollection can repeat downloads but not generation charges.')
    operations['token_count_operations_known'] = sum(operations[key] for key in (
        'synchronous_token_count_calls_with_reserved_identity', 'count_only_error_operations',
        'matrix_preparation_token_count_calls_known'))
    return operations
