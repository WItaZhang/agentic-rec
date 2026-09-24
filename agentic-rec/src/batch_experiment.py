"""Explicitly reserved asynchronous replication; batch turnaround is not service latency."""

import hashlib
import json
from pathlib import Path

from .data import load_amazon_metadata, load_amazon_reviews
from .evidence import build_prompt
from .llm_experiment import choose_views, load_frozen_knn
from .openai_adapter import load_key
from .paid_budget import PaidBudget, usage_cost
from .replay import make_candidates
from .utils import digest, managed_run, write_json


def client_for(config, root):
    from openai import OpenAI

    if config["base_url"] != "https://api.openai.com/v1" or config["max_retries"] != 0:
        raise ValueError("Unauthorized batch endpoint or implicit retries")
    return OpenAI(api_key=load_key(root / config["credential_file"]), base_url=config["base_url"],
                  max_retries=0, timeout=config["timeout_seconds"])


def run_batch_submit(config, config_path, root):
    import tiktoken
    import yaml

    if config["budget"]["total_paid_usd"] > 50:
        raise ValueError("Budget exceeds authorization")
    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["batch"]["source_run"]
        original = yaml.safe_load((source / "config.yaml").read_text())
        if original["evaluation"]["partition"] == "test":
            raise ValueError("Batch smoke cannot access test")
        original_calls = [json.loads(line) for line in (source / "calls.jsonl").read_text().splitlines()]
        if json.loads((source / "manifest.json").read_text())["status"] != "completed":
            raise ValueError("Replication requires a complete original run")
        for path, checksum in (("raw_path", "sha256"), ("metadata_path", "metadata_sha256")):
            if digest(root / original["data"][path]) != original["data"][checksum]:
                raise ValueError("Input checksum changed")
        events, _ = load_amazon_reviews(root / original["data"]["raw_path"])
        views, _, _ = choose_views(events, original)
        views = {view.request_id: view for view in views}
        metadata = load_amazon_metadata(root / original["data"]["metadata_path"], ["title", "categories"])
        model = load_frozen_knn(root, original["retriever"])
        tokenizer = tiktoken.get_encoding(original["evidence"]["tokenizer"])

        def truncate(text, limit):
            tokens = tokenizer.encode(text, disallowed_special=())
            return tokenizer.decode(tokens[:limit]), len(tokens) > limit

        instructions = (root / original["evidence"]["prompt_path"]).read_text(encoding="utf-8")
        budget_config = config["budget"]
        budget = PaidBudget(root / budget_config["ledger_path"], run_dir.name, budget_config["total_paid_usd"],
                            budget_config["per_run_paid_usd"], budget_config["stop_at_usd"])
        prepared = []
        for old in original_calls:
            view = views[old["request_id"]]
            snapshot = make_candidates(view, model, original["retriever"]["candidate_count"],
                original["protocol"]["positive_rating"], original["retriever"]["model_hash"])
            messages, schema, _, evidence = build_prompt(view, snapshot, metadata, old["plan"],
                                                         original["evidence"], truncate, instructions)
            common = {"model": original["llm"]["model"], "input": messages,
                      "text": {"format": {"type": "json_schema", "name": "ranking", "strict": True, "schema": schema}}}
            fingerprint = hashlib.sha256(json.dumps(common, sort_keys=True).encode()).hexdigest()
            if fingerprint != old["prompt_sha256"] or evidence["candidate_hash"] != old["evidence"]["candidate_hash"]:
                raise ValueError("Replication payload differs from original")
            price = config["batch"]["pricing"]
            if price["model"] != common["model"]:
                raise ValueError("Batch price/model mismatch")
            reserve = usage_cost({"input_tokens": old["preflight_input_tokens"]
                                  + original["llm"]["input_reservation_margin_tokens"],
                                  "output_tokens": original["llm"]["max_output_tokens"]}, price)
            prepared.append({"custom_id": f"{old['request_id']}_{old['plan']}", "method": "POST", "url": "/v1/responses",
                "body": {**common, "store": False, "temperature": original["llm"]["temperature"],
                         "max_output_tokens": original["llm"]["max_output_tokens"]},
                "reserved_usd": reserve, "original_call_id": old["call_id"], "prompt_sha256": fingerprint})
        upper = sum(row["reserved_usd"] for row in prepared)
        write_json(run_dir / "preflight_budget.json", {"calls": len(prepared), "upper_bound_usd": upper,
                                                       "accounting_before": budget.snapshot()})
        print(f"Batch replication preflight: {len(prepared)} calls; upper USD {upper:.6f}", flush=True)
        if upper > budget_config["per_run_paid_usd"] or upper + budget.snapshot()["campaign_accounted_usd"] > budget_config["stop_at_usd"]:
            raise ValueError("Batch estimate exceeds authorization")
        reservations = {}
        for row in prepared:
            custom_id = row["custom_id"]
            reservations[custom_id] = {"call_id": budget.reserve(row["reserved_usd"],
                {"custom_id": custom_id, "kind": "batch_replication"}), "reserved_usd": row["reserved_usd"],
                "original_call_id": row["original_call_id"], "prompt_sha256": row["prompt_sha256"]}
            write_json(run_dir / "reservations.json", reservations)
        batch_input = run_dir / "batch_input.jsonl"
        with batch_input.open("w", encoding="utf-8") as stream:
            for row in prepared:
                stream.write(json.dumps({k: row[k] for k in ("custom_id", "method", "url", "body")}) + "\n")
        client = client_for(original["llm"], root)
        try:
            with batch_input.open("rb") as stream:
                uploaded = client.files.create(file=stream, purpose="batch")
            write_json(run_dir / "upload.json", {"file_id": uploaded.id})
            batch = client.batches.create(input_file_id=uploaded.id, endpoint="/v1/responses", completion_window="24h",
                                          metadata={"research_run": run_dir.name})
        except Exception as error:
            write_json(run_dir / "submission_error.json", {"type": type(error).__name__,
                "recovery": "Do not resubmit blindly; list batches and match metadata.research_run before reconciling reservations"})
            raise RuntimeError("Batch submission uncertain; retained reservations and redacted error") from None
        write_json(run_dir / "submission.json", batch.model_dump())
        manifest.update(batch_id=batch.id, batch_status=batch.status, stage_status="submitted_not_evaluated",
                        source_run=config["batch"]["source_run"], test_scored=False)
        print(f"Submitted {batch.id}: {batch.status}; batch completion is separate from submission", flush=True)


def parse_batch_line(row):
    response = row.get("response")
    if not response or response.get("status_code") != 200:
        return {"custom_id": row["custom_id"], "status": "batch_error", "usage": None, "text": "",
                "error_code": (row.get("error") or {}).get("code")}
    body = response["body"]
    text = "".join(part.get("text", "") for item in body.get("output", [])
                   for part in item.get("content", []) if part.get("type") == "output_text")
    return {"custom_id": row["custom_id"], "status": body["status"], "usage": body.get("usage"),
            "text": text, "response_id": body.get("id"), "returned_model": body.get("model")}


def run_batch_collect(config, config_path, root):
    import yaml

    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["batch_run"]
        submitted_config = yaml.safe_load((source / "config.yaml").read_text())
        original = yaml.safe_load((root / submitted_config["batch"]["source_run"] / "config.yaml").read_text())
        submission = json.loads((source / "submission.json").read_text())
        client = client_for(original["llm"], root)
        batch = client.batches.retrieve(submission["id"])
        write_json(run_dir / "batch_status.json", batch.model_dump())
        manifest.update(batch_id=batch.id, batch_status=batch.status, stage_status="status_only", test_scored=False)
        if batch.status not in ("completed", "failed", "expired", "cancelled"):
            print(f"Batch {batch.status}: {batch.request_counts.model_dump()}", flush=True)
            return
        lines = []
        for kind in ("output", "error"):
            file_id = getattr(batch, f"{kind}_file_id")
            if file_id:
                content = client.files.content(file_id).text
                (run_dir / f"batch_{kind}.jsonl").write_text(content, encoding="utf-8")
                lines.extend(json.loads(line) for line in content.splitlines())
        results = {row["custom_id"]: parse_batch_line(row) for row in lines}
        if len(results) != len(lines):
            raise ValueError("Duplicate batch custom IDs")
        reservations = json.loads((source / "reservations.json").read_text())
        budget_config = submitted_config["budget"]
        budget = PaidBudget(root / budget_config["ledger_path"], source.name, budget_config["total_paid_usd"],
                            budget_config["per_run_paid_usd"], budget_config["stop_at_usd"])
        # Retry collection is safe: identical settlements are checked instead of charged twice.
        previous = budget.entries()
        for custom_id, reservation in reservations.items():
            row = results.setdefault(custom_id, {"custom_id": custom_id, "status": "missing_batch_result",
                                                "usage": None, "text": ""})
            actual = usage_cost(row["usage"], submitted_config["batch"]["pricing"]) if row["usage"] else None
            row.update(call_id=reservation["call_id"], actual_known_usd=actual,
                       reserved_usd=reservation["reserved_usd"], latency_mode="batch_turnaround_only")
            old = previous[reservation["call_id"]]
            if old["event"] == "reserve":
                budget.settle(reservation["call_id"], actual, row["status"])
            elif old["actual_usd"] != actual or old["status"] != row["status"]:
                raise ValueError("Batch settlement changed unexpectedly")
        write_json(run_dir / "results.json", list(results.values()))
        write_json(run_dir / "resources.json", {"budget": budget.snapshot(),
            "known_usd": sum(row["actual_known_usd"] or 0 for row in results.values()),
            "batch_turnaround_seconds": (batch.completed_at - batch.created_at) if batch.completed_at else None,
            "service_latency_ms": None, "service_latency_reason": "Not observable from asynchronous batch API"})
        manifest.update(stage_status="collected", source_run=str(Path(config["batch_run"])), results=len(results))
        print(f"Collected {len(results)} batch results; {budget.snapshot()}", flush=True)
