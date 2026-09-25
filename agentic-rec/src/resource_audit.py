"""Reconcile physical provider usage with the durable campaign ledger."""

import json
import re
from collections import defaultdict

import yaml

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
                and row.get("generation_attempts") == 0 and row.get("http_status") == 400
                and row.get("provider_code") == "billing_hard_limit_reached" and usage is None):
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


def run_resource_audit(config, config_path, root):
    settings = config["resource_audit"]
    with managed_run(config, config_path, root) as (run_dir, manifest):
        limits = config["budget"]
        ledger = PaidBudget(root / limits["ledger_path"], run_dir.name, limits["total_paid_usd"],
                            limits["per_run_paid_usd"], limits["stop_at_usd"])
        entries = ledger.entries()
        if settings["require_no_pending"] and any(row["event"] == "reserve" for row in entries.values()):
            raise ValueError("A final resource audit cannot omit pending paid attempts")
        directories = sorted((root / config["logging"]["path"]).glob("*/manifest.json"))
        records, sources, nested, states, names = [], {}, set(), {}, {}
        for path in directories:
            directory = path.parent
            state = json.loads(path.read_text())
            states[directory.name] = state
            cfg = yaml.safe_load((directory / "config.yaml").read_text(encoding="utf-8"))
            names[directory.name] = cfg["experiment_name"]
            if cfg.get("runtime_source_run"):
                nested.add(directory.name)
            scheduler = directory / "scheduler_state.json"
            if scheduler.exists():
                chunks = json.loads(scheduler.read_text())["chunks"]
                for chunk in chunks:
                    for field in ("submit_run", "collection_run"):
                        if chunk.get(field) and is_scheduler_child(cfg, chunk[field]):
                            nested.add(chunk[field].replace("\\", "/").split("/")[-1])
            for file in (directory / "calls.jsonl", directory / "results.json"):
                if not file.exists():
                    continue
                rows = ([json.loads(line) for line in file.read_text().splitlines()]
                        if file.suffix == ".jsonl" else json.loads(file.read_text()))
                if not isinstance(rows, list):
                    raise ValueError("Unexpected call-record format in campaign logs")
                records.extend(rows)
                sources[str(file.relative_to(root))] = digest(file)
        per_run = reconcile_usage(entries, records)
        categories = {}
        for name, row in per_run.items():
            matches = [rule["name"] for rule in settings["phase_rules"]
                       if names.get(name, "").startswith(tuple(rule["experiment_prefixes"]))]
            if len(matches) != 1:
                raise ValueError(f"Paid run needs exactly one declared phase classification: {name}")
            phase = matches[0]
            if phase not in categories:
                categories[phase] = {key: 0 for key in row}
            for key, value in row.items():
                categories[phase][key] += value
        roots = {name: state for name, state in states.items() if name not in nested and name != run_dir.name}
        running = [name for name, state in roots.items() if state["status"] == "running"]
        if running and settings["require_no_pending"]:
            raise ValueError("Experiment processes are still running; do not publish final resource totals")
        report = {"by_phase": categories, "by_paid_run": per_run,
            "total": {key: sum(row[key] for row in per_run.values()) for key in next(iter(per_run.values()), {})},
            "ledger_snapshot": ledger.snapshot(),
            "experiment_compute": {"inclusive_cpu_seconds_known": sum(row.get("cpu_seconds", 0) for row in roots.values()),
                "sum_run_wall_seconds_known": sum(row.get("wall_seconds", 0) for row in roots.values()),
                "runs_with_cpu_timing": sum("cpu_seconds" in row for row in roots.values()),
                "runs_without_cpu_timing": [name for name, row in roots.items() if "cpu_seconds" not in row],
                "nested_runs_excluded_from_double_counting": sorted(nested), "running_runs": running,
                "scope": "Recorded experiment processes including failed attempts and analysis; excludes agent/tool UI, installation/download time and uninstrumented diagnostics. Summed wall time is not elapsed campaign time."},
            "accounting": "Reserved request attempts counted once across resumed, collected and counterfactual aliases. Explicit pre-generation Batch rejections are counted separately with zero charge and no fabricated usage. Unknown usage retains its reservation. Dollar estimates use provider usage and frozen prices, not invoices.",
            "unmetered": ["Host energy consumption", "Provider-internal compute", "Network bytes"],
            "source_record_hashes": sources}
        write_json(run_dir / "campaign_resources.json", report)
        manifest.update(test_scored=False, paid_api_usd=0, llm_calls=0,
                        ledger_sha256=digest(root / limits["ledger_path"]), stage_status="resource_audit_complete")
        print(json.dumps(report["total"]), flush=True)
