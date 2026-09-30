"""Reconcile physical provider usage with the durable campaign ledger."""

import json
import re
from collections import defaultdict

import yaml

from .operational_accounting import incremental_polls, summarize_campaign_operations, verify_recorded_prices
from .paid_budget import PaidBudget
from .utils import digest, managed_run, write_json


def is_scheduler_child(config, child_run):
    """Fallback for older nested runs; imported checkpoints are not CPU parents."""
    experiment = child_run.replace("\\", "/").split("/")[-1].split("_", 2)[-1]
    return config.get("stage") == "batch_schedule" and bool(re.fullmatch(
        re.escape(config["experiment_name"]) + r"_[sc]\d{3}", experiment))


def reconcile_usage(entries, records):
    usage_by_id = {}
    rejected_before_generation = set()
    for row in records:
        identity = row.get("call_id")
        if not identity:
            continue
        if identity not in entries:
            raise ValueError("Recorded physical call is absent from the budget ledger")
        usage = row.get("usage")
        if (row.get("status") == "submission_rejected_before_generation"
                and row.get("generation_attempts") == 0 and usage is None
                and ((row.get("http_status") == 400 and row.get("provider_code") == "billing_hard_limit_reached")
                     or (row.get("provider_code") == "token_limit_exceeded" and row.get("rejection_stage") == "batch_validation"))):
            rejected_before_generation.add(identity)
        if identity in usage_by_id and usage_by_id[identity] != usage:
            raise ValueError("Conflicting provider usage for the same physical call")
        usage_by_id[identity] = usage
    totals = defaultdict(lambda: {"physical_attempts": 0, "pending": 0, "unknown_settled": 0,
        "known_usage_priced_usd": 0.0, "accounted_usd": 0.0, "input_tokens": 0,
        "output_tokens": 0, "cached_input_tokens": 0, "usage_observed_attempts": 0,
        "rejected_before_generation": 0})
    for identity, entry in entries.items():
        summary = totals[entry["run_id"]]
        summary["physical_attempts"] += 1
        actual = entry.get("actual_usd")
        summary["known_usage_priced_usd"] += actual or 0
        summary["accounted_usd"] += entry["reserved_usd"] if actual is None else actual
        summary["pending"] += int(entry["event"] == "reserve")
        summary["unknown_settled"] += int(entry["event"] == "settle" and actual is None)
        usage = usage_by_id.get(identity)
        if usage is not None:
            summary["usage_observed_attempts"] += 1
            summary["input_tokens"] += usage["input_tokens"]
            summary["output_tokens"] += usage["output_tokens"]
            summary["cached_input_tokens"] += (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
        elif (identity in rejected_before_generation and actual == 0
              and entry.get("status") == "submission_rejected_before_generation"):
            summary["rejected_before_generation"] += 1
        elif actual is not None:
            raise ValueError("Known physical charge lacks its provider usage record")
    return dict(totals)


def categorize_usage(per_run, names, phase_rules):
    categories = {}
    for name, row in per_run.items():
        matches = [rule["name"] for rule in phase_rules
                   if names.get(name, "").startswith(tuple(rule["experiment_prefixes"]))]
        if len(matches) != 1:
            raise ValueError(f"Paid run needs exactly one declared phase classification: {name}")
        phase = matches[0]
        if phase not in categories:
            categories[phase] = {key: 0 for key in row}
        for key, value in row.items():
            categories[phase][key] += value
    return categories


def run_resource_audit(config, config_path, root):
    settings = config["resource_audit"]
    with managed_run(config, config_path, root) as (run_dir, manifest):
        limits = config["budget"]
        ledger = PaidBudget(root / limits["ledger_path"], run_dir.name, limits["total_paid_usd"],
                            limits["per_run_paid_usd"], limits["stop_at_usd"])
        ledger_before = digest(root / limits['ledger_path'])
        entries = ledger.entries()
        if settings["require_no_pending"] and any(row["event"] == "reserve" for row in entries.values()):
            raise ValueError("A final resource audit cannot omit pending paid attempts")
        directories = sorted((root / config["logging"]["path"]).glob("*/manifest.json"))
        records, sources, nested, states, names = [], {}, set(), {}, {}
        rank_validated, repaired, preparations, management, prices = set(), set(), {}, {}, {}
        for path in directories:
            directory = path.parent
            if directory == run_dir:
                continue  # Its manifest changes on completion; do not self-reference.
            state = json.loads(path.read_text())
            states[directory.name] = state
            cfg = yaml.safe_load((directory / "config.yaml").read_text(encoding="utf-8"))
            for evidence_file in ('manifest.json', 'config.yaml', 'scheduler_state.json', 'upload.json',
                                  'submission_error.json', 'batch_status.json', 'provider_reconciliation.json'):
                file = directory / evidence_file
                if file.exists():
                    sources[str(file.relative_to(root))] = digest(file)
            names[directory.name] = cfg["experiment_name"]
            if cfg.get("runtime_source_run"):
                nested.add(directory.name)
            scheduler = directory / "scheduler_state.json"
            if scheduler.exists():
                scheduler_state = json.loads(scheduler.read_text())
                chunks = scheduler_state["chunks"]
                if cfg.get('stage') == 'batch_schedule':
                    predecessor = (json.loads((root / cfg['resume_from'].replace('\\', '/') / 'scheduler_state.json').read_text())
                                   if cfg.get('resume_from') else None)
                    management[directory.name] = {'new_scheduler_poll_invocations': incremental_polls(scheduler_state, predecessor)}
                for chunk in chunks:
                    for field in ("submit_run", "collection_run"):
                        if chunk.get(field) and is_scheduler_child(cfg, chunk[field]):
                            nested.add(chunk[field].replace("\\", "/").split("/")[-1])
            phase = cfg.get('stage')
            if cfg.get('llm', {}).get('pricing'):
                prices[directory.name] = cfg['llm']['pricing']
            elif phase == 'batch_submit':
                prices[directory.name] = cfg['batch']['pricing']
            elif phase == 'serving_resource_audit':
                frozen = json.loads((root / cfg['audit']['freeze_path'].replace('\\', '/')).read_text())
                prices[directory.name] = frozen['test_config']['llm']['pricing']
            operation = management.setdefault(directory.name, {})
            operation.update(successful_upload_receipts=int((directory / 'upload.json').exists()),
                recorded_submission_failures=int((directory / 'submission_error.json').exists()),
                successful_collection_status_receipts=int(phase == 'batch_collect' and (directory / 'batch_status.json').exists()),
                successful_batch_file_downloads=sum(int(phase == 'batch_collect' and (directory / f'batch_{kind}.jsonl').exists())
                                                    for kind in ('output', 'error')),
                recorded_metadata_reconciliations=int((directory / 'provider_reconciliation.json').exists()),
                completed_upload_recoveries=int(phase == 'batch_upload_recovery' and state['status'] == 'completed'),
                failed_upload_recoveries=int(phase == 'batch_upload_recovery' and state['status'] == 'failed'),
                queue_recovery_checkpoints=int(phase == 'batch_queue_recovery' and state['status'] == 'completed'))
            if phase in ('matrix_prepare', 'frozen_matrix_prepare'):
                resource = directory / 'resources.json'
                preparations[directory.name] = {'status': state['status'], 'count_endpoint_calls':
                    json.loads(resource.read_text()).get('count_endpoint_calls') if resource.exists() else None}
                if resource.exists():
                    sources[str(resource.relative_to(root))] = digest(resource)
            call_lookup = {}
            for file in (directory / "calls.jsonl", directory / "results.json"):
                if not file.exists():
                    continue
                rows = ([json.loads(line) for line in file.read_text().splitlines()]
                        if file.suffix == ".jsonl" else json.loads(file.read_text()))
                if not isinstance(rows, list):
                    raise ValueError("Unexpected call-record format in campaign logs")
                records.extend(rows)
                call_lookup.update({(r['request_id'], r['plan']): r['call_id'] for r in rows
                                    if r.get('call_id') and 'request_id' in r and 'plan' in r})
                sources[str(file.relative_to(root))] = digest(file)
            outcomes = directory / 'outcomes.json'
            if outcomes.exists() and call_lookup:
                for row in json.loads(outcomes.read_text()):
                    identity = call_lookup.get((row['request_id'], row['plan']))
                    if identity:
                        rank_validated.add(identity)
                        if row.get('repair_errors'):
                            repaired.add(identity)
                sources[str(outcomes.relative_to(root))] = digest(outcomes)
        if digest(root / limits['ledger_path']) != ledger_before:
            raise RuntimeError('Ledger changed during audit; discard this mixed snapshot and retry after settlement')
        per_run = reconcile_usage(entries, records)
        operations = summarize_campaign_operations(entries, records, rank_validated, repaired, preparations, management)
        categories = categorize_usage(per_run, names, settings['phase_rules'])
        roots = {name: state for name, state in states.items() if name not in nested and name != run_dir.name}
        running = [name for name, state in roots.items() if state["status"] == "running"]
        if running and settings["require_no_pending"]:
            raise ValueError("Experiment processes are still running; do not publish final resource totals")
        budget_snapshot = ledger.snapshot()
        if digest(root / limits['ledger_path']) != ledger_before:
            raise RuntimeError('Ledger changed during audit; discard this mixed snapshot and retry after settlement')
        report = {"by_phase": categories, "by_paid_run": per_run,
            "total": {key: sum(row[key] for row in per_run.values()) for key in next(iter(per_run.values()), {})},
            "ledger_snapshot": budget_snapshot,
            "operation_accounting": operations,
            "usage_pricing_verification": verify_recorded_prices(entries, records, prices),
            "experiment_compute": {"inclusive_cpu_seconds_known": sum(row.get("cpu_seconds", 0) for row in roots.values()),
                "sum_run_wall_seconds_known": sum(row.get("wall_seconds", 0) for row in roots.values()),
                "runs_with_cpu_timing": sum("cpu_seconds" in row for row in roots.values()),
                "runs_without_cpu_timing": [name for name, row in roots.items() if "cpu_seconds" not in row],
                "nested_runs_excluded_from_double_counting": sorted(nested), "running_runs": running,
                "scope": "Recorded experiment processes including failed attempts and analysis; excludes agent/tool UI, installation/download time and uninstrumented diagnostics. The current auditor is timed in its own manifest but excluded from this snapshot. Summed wall time is not elapsed campaign time."},
            "accounting": "Reserved request attempts counted once across resumed, collected and counterfactual aliases. Explicit pre-generation Batch rejections are counted separately with zero charge and no fabricated usage. Unknown usage retains its reservation. Dollar estimates use provider usage and frozen prices, not invoices.",
            "unmetered": ["Host energy consumption", "Provider-internal compute", "Network bytes"],
            "source_record_hashes": sources}
        write_json(run_dir / "campaign_resources.json", report)
        from .resource_archive import write_accounting_archive

        write_accounting_archive(run_dir / 'accounting_archive', entries, records,
            {'rank_validated': sorted(rank_validated), 'repaired': sorted(repaired), 'preparations': preparations,
             'management': management, 'names': names, 'phase_rules': settings['phase_rules'],
             'prices': {entry['run_id']: prices[entry['run_id']] for entry in entries.values()}}, report,
            {'ledger_sha256': ledger_before, 'source_run': run_dir.relative_to(root).as_posix(),
             'source_commit': manifest['git_commit'], 'interim': not settings['require_no_pending']})
        manifest.update(test_scored=False, paid_api_usd=0, llm_calls=0,
                        ledger_sha256=ledger_before, stage_status="resource_audit_complete")
        print(json.dumps(report["total"]), flush=True)
