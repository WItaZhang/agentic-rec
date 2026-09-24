"""Publish compact derived outcomes and replay their analysis without API access."""

import gzip
import json
import math

import yaml

from .evidence_analysis import analyze_matrix, draw_cost_quality
from .policy_analysis import evaluate_decisions, plot_policies
from .utils import digest, managed_run, write_json

CALL_FIELDS = ("request_id", "plan", "call_id", "status", "prompt_sha256", "actual_known_usd", "reserved_usd",
    "usage", "generation_attempts", "counterfactual_generation_attempts", "rate_queue_ms", "generation_latency_ms",
    "total_latency_ms", "returned_model", "count_endpoint_calls", "reused_generation", "canonical_id")


def numeric_reproduction(actual, expected, tolerance):
    if not 0 <= tolerance <= 1e-12:
        raise ValueError("Reanalysis tolerance must only accommodate floating-point roundoff")
    differences = []

    def visit(a, b):
        if type(a) is not type(b):
            return False
        if isinstance(a, dict):
            return a.keys() == b.keys() and all(visit(a[key], b[key]) for key in a)
        if isinstance(a, list):
            return len(a) == len(b) and all(visit(x, y) for x, y in zip(a, b, strict=True))
        if isinstance(a, float):
            differences.append(abs(a - b))
            return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance
        return a == b

    matches = visit(actual, expected)
    return {"matches": matches, "absolute_float_tolerance": tolerance,
            "max_absolute_float_difference": max(differences, default=0),
            "non_float_fields": "exact"}


def public_outcomes(rows):
    # Preserve lexical user order so fixed-seed paired bootstrap draws are identical.
    mapping = {user: f"user_{index:08d}" for index, user in enumerate(sorted({r["user_id"] for r in rows}))}
    allowed = {"request_id", "plan", "ranking", "repair_errors", "status", "candidate_hash", "service_latency_ms",
               "history_count", "cold_item", "ndcg", "hr", "candidate_recall"}
    return [{**{key: row[key] for key in allowed if key in row}, "user_id": mapping[row["user_id"]]} for row in rows]


def dump_compressed(path, value, lines=False):
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in value) if lines else json.dumps(value, sort_keys=True)
    path.write_bytes(gzip.compress(payload.encode(), mtime=0))


def run_publish_results(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["publication"]["matrix_run"]
        analysis_source = root / config["publication"]["analysis_run"]
        status = json.loads((source / "manifest.json").read_text())
        analyzed = json.loads((analysis_source / "manifest.json").read_text())
        if status["status"] != "completed" or analyzed["status"] != "completed":
            raise ValueError("Only complete experiments and analyses can be published")
        destination = root / config["publication"]["output_path"]
        if destination.exists():
            raise ValueError("Use a new archive path; never overwrite published evidence")
        destination.mkdir(parents=True)
        rows = json.loads((source / "outcomes.json").read_text())
        calls = [json.loads(line) for line in (source / "calls.jsonl").read_text().splitlines()]
        kind = config["publication"]["kind"]
        if kind == "evidence":
            settings = yaml.safe_load((analysis_source / "config.yaml").read_text(encoding="utf-8"))["analysis"]
        elif kind == "policy":
            settings = json.loads((analysis_source / "analysis_settings.json").read_text())
            prepared = root / status["prepared_run"]
            decision_file = prepared / "routing_decisions.json"
            if digest(decision_file) != status["routing_decisions_sha256"]:
                raise ValueError("Policy decisions changed before publication")
            (destination / "routing_decisions.json").write_bytes(decision_file.read_bytes())
        else:
            raise ValueError("Unknown publication analysis kind")
        dump_compressed(destination / "outcomes.json.gz", public_outcomes(rows))
        dump_compressed(destination / "calls.jsonl.gz", [{key: row[key] for key in CALL_FIELDS if key in row} for row in calls], lines=True)
        write_json(destination / "analysis_settings.json", settings)
        (destination / "expected_analysis.json").write_bytes((analysis_source / "analysis.json").read_bytes())
        (destination / "source_manifest.json").write_bytes((source / "manifest.json").read_bytes())
        if (source / "resources.json").exists():
            (destination / "resources.json").write_bytes((source / "resources.json").read_bytes())
        write_json(destination / "archive_manifest.json", {"status": "completed", "kind": kind,
            "test_scored": status.get("test_scored", False), "source_run": config["publication"]["matrix_run"],
            "analysis_run": config["publication"]["analysis_run"],
            "source_outcomes_sha256": digest(source / "outcomes.json"), "source_calls_sha256": digest(source / "calls.jsonl"),
            "files": {p.name: digest(p) for p in sorted(destination.iterdir()) if p.is_file()},
            "privacy": "Per-artifact user ordinals preserve ordering; request IDs link same requests. No review text, prompts, keys or response IDs.",
            "calls_scope": "Actual provider usage, including repeated/shared/failed attempts; not newly executed calls"})
        manifest.update(test_scored=False, publication_path=config["publication"]["output_path"],
                        archive_sha256=digest(destination / "archive_manifest.json"), paid_api_usd=0)
        print(f"Published derived artifacts: {destination.relative_to(root)}", flush=True)


def run_archive_analysis(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["archive_path"]
        record = json.loads((source / "archive_manifest.json").read_text())
        if record["status"] != "completed":
            raise ValueError("Archive is incomplete")
        for name, checksum in record["files"].items():
            if "/" in name or "\\" in name or digest(source / name) != checksum:
                raise ValueError("Archive file changed or filename is unsafe")
        rows = json.loads(gzip.decompress((source / "outcomes.json.gz").read_bytes()))
        calls = [json.loads(line) for line in gzip.decompress((source / "calls.jsonl.gz").read_bytes()).decode().splitlines()]
        settings = json.loads((source / "analysis_settings.json").read_text())
        if record["kind"] == "evidence":
            result = analyze_matrix(rows, calls, settings)
            draw_cost_quality(result, run_dir)
        elif record["kind"] == "policy":
            decisions = json.loads((source / "routing_decisions.json").read_text())
            plans = sorted({r["plan"] for r in rows})
            result, _ = evaluate_decisions(rows, calls, decisions, plans, settings)
            plot_policies(result, run_dir)
        else:
            raise ValueError("Unknown archive kind")
        expected = json.loads((source / "expected_analysis.json").read_text())
        comparison = numeric_reproduction(result, expected, config["absolute_float_tolerance"])
        if not comparison["matches"]:
            write_json(run_dir / "mismatched_analysis.json", result)
            raise ValueError("Published outcomes do not reproduce the archived numeric analysis within the declared roundoff tolerance")
        write_json(run_dir / "analysis.json", result)
        manifest.update(test_scored=record["test_scored"], numerical_reproduction=comparison,
                        archive_sha256=digest(source / "archive_manifest.json"), paid_api_usd=0, llm_calls=0)
        print(f"Analysis reproduced: {comparison}; no dataset, credential or model access", flush=True)
