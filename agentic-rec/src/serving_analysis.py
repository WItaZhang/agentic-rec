"""Publish/replay measured service records; replay does not simulate new latency."""

import gzip
import json

import numpy as np

from .metrics import service_latency_summary
from .result_archive import dump_compressed, numeric_reproduction
from .utils import digest, managed_run, verified_run_config, write_json

PUBLIC_FIELDS = ("request_id", "method", "action", "retriever", "history_count", "status",
    "actual_known_usd", "reserved_usd", "generation_attempts", "count_endpoint_calls", "usage",
    "repair_errors", "service_ms", "retrieval_ms", "feature_and_policy_ms", "evidence_ms",
    "count_latency_ms", "rate_queue_ms", "generation_latency_ms", "total_latency_ms",
    "client_thread_cpu_seconds", "preflight_input_tokens", "http_status", "error_code")


def public_serving_records(records):
    return [{key: row[key] for key in PUBLIC_FIELDS if key in row} for row in records]


def summarize_serving(records, methods, users):
    if not records or len(set(methods)) != len(methods) or users < 1:
        raise ValueError("Nonempty unique methods and requests required")
    keys = [(r["request_id"], r["method"]) for r in records]
    ids = {q for q, _ in keys}
    if len(ids) != users or len(set(keys)) != len(keys) or set(keys) != {(q, method) for q in ids for method in methods}:
        raise ValueError("Incomplete or duplicated serving matrix; keep every request and method")
    summary = {}
    for method in methods:
        rows = [r for r in records if r["method"] == method]
        cost = [r["actual_known_usd"] if r["actual_known_usd"] is not None else r["reserved_usd"] for r in rows]
        summary[method] = {"requests": len(rows), **service_latency_summary(rows),
            "mean_api_usd": float(np.mean(cost)), "generation_attempts": sum(r["generation_attempts"] for r in rows),
            "count_endpoint_calls": sum(r["count_endpoint_calls"] for r in rows),
            "input_tokens": sum((r.get("usage") or {}).get("input_tokens", 0) for r in rows),
            "output_tokens": sum((r.get("usage") or {}).get("output_tokens", 0) for r in rows),
            "cached_tokens": sum(((r.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens", 0) for r in rows),
            "repairs": sum(bool(r["repair_errors"]) for r in rows),
            **{f"mean_{key}": float(np.mean([r.get(key, 0) for r in rows]))
               for key in ("retrieval_ms", "feature_and_policy_ms", "evidence_ms", "rate_queue_ms", "generation_latency_ms")}}
    return summary


def write_serving_table(summary, path):
    lines = ["# Observed synchronous service measurements", "",
        "Warm resident models; same validation users and interleaved methods. Replay summarizes saved observations, not new timings.", "",
        "| Method | Requests | Calls | Mean ms | P95 ms | Generation-branch mean ms | Generation-branch P95 ms | API USD/1,000 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    def latency(value):
        return "not observed" if value is None else f"{value:.3f}"

    for name, row in summary.items():
        lines.append(f"| {name} | {row['requests']} | {row['generation_attempts']} | "
            f"{latency(row['mean_service_ms'])} | {latency(row['p95_service_ms'])} | "
            f"{latency(row['mean_generation_service_ms'])} | {latency(row['p95_generation_service_ms'])} | "
            f"{1000 * row['mean_api_usd']:.6f} |")
    lines.extend(["", "Overall summaries retain zero-call requests. Rare generation-branch percentiles are descriptive and may rest on very few observations.",
        "Automatic provider prefix-cache usage is recorded separately; application output reuse is disabled. Batch prices and turnaround are not substituted here.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run_serving_archive(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        if config["stage"] == "publish_serving":
            source = root / config["source_run"]
            status = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
            saved = verified_run_config(source)
            if saved["stage"] != "serving_resource_audit" or status["status"] != "completed" or status.get("quality_scored") is not False:
                raise ValueError("Only a completed resource-only serving audit can be published")
            records = [json.loads(line) for line in (source / "calls.jsonl").read_text(encoding="utf-8").splitlines()]
            expected = json.loads((source / "resources.json").read_text(encoding="utf-8"))
            methods = list(expected["methods"])
            users = expected["methods"][methods[0]]["requests"]
            public = public_serving_records(records)
            actual = summarize_serving(public, methods, users)
            verification = numeric_reproduction(actual, expected["methods"], config["absolute_float_tolerance"])
            if not verification["matches"]:
                raise ValueError("Public service records do not reproduce the observed summary")
            destination = root / config["archive_path"]
            destination.mkdir()  # Never overwrite observed evidence.
            dump_compressed(destination / "calls.jsonl.gz", public, lines=True)
            write_json(destination / "resources.json", expected)
            (destination / "config.yaml").write_bytes((source / "config.yaml").read_bytes())
            (destination / "source_manifest.json").write_bytes((source / "manifest.json").read_bytes())
            write_json(destination / "archive_manifest.json", {"status": "completed", "kind": "serving",
                "source_run": config["source_run"], "source_calls_sha256": digest(source / "calls.jsonl"),
                "source_resources_sha256": digest(source / "resources.json"),
                "files": {p.name: digest(p) for p in sorted(destination.iterdir())},
                "scope": "Recompute observed warm-model latency/cost summaries; no new timing experiment or quality evaluation",
                "privacy": "No review/user IDs, prompts, rankings, response text, keys or provider call/response IDs"})
        else:
            source = root / config["archive_path"]
            record = json.loads((source / "archive_manifest.json").read_text(encoding="utf-8"))
            if record["status"] != "completed" or record["kind"] != "serving":
                raise ValueError("A complete service archive is required")
            for name, checksum in record["files"].items():
                if "/" in name or "\\" in name or digest(source / name) != checksum:
                    raise ValueError("Service archive changed")
            public = [json.loads(line) for line in gzip.decompress((source / "calls.jsonl.gz").read_bytes()).decode().splitlines()]
            expected = json.loads((source / "resources.json").read_text(encoding="utf-8"))
            methods = list(expected["methods"])
            actual = summarize_serving(public, methods, expected["methods"][methods[0]]["requests"])
            verification = numeric_reproduction(actual, expected["methods"], config["absolute_float_tolerance"])
            if not verification["matches"]:
                raise ValueError("Service measurements do not reproduce")
        write_json(run_dir / "methods.json", actual)
        write_serving_table(actual, run_dir / "summary.md")
        write_json(run_dir / "verification.json", verification)
        manifest.update(test_scored=False, quality_scored=False, paid_api_usd=0,
                        latency_remeasured=False, numerical_reproduction=verification)
        print(f"Observed service statistics reproduced: {verification}; no API or simulated latency", flush=True)
