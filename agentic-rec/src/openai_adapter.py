"""Responses backend: no hidden retries; reservations precede every generation attempt."""

import hashlib
import json
import re
import time

from .paid_budget import usage_cost


def load_key(path):
    keys = re.findall(r"sk-[A-Za-z0-9_\-]+", path.read_text(encoding="utf-8-sig"))
    if len(keys) != 1:
        raise ValueError("Credential file must contain exactly one OpenAI API key")
    return keys[0]


class OpenAIBackend:
    def __init__(self, config, root, budget, client=None):
        if config["base_url"] != "https://api.openai.com/v1" or config["max_retries"] != 0:
            raise ValueError("Only authorized OpenAI endpoint and explicit zero retries supported")
        self.config, self.budget = config, budget
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=load_key(root / config["credential_file"]),
                            base_url=config["base_url"], max_retries=0,
                            timeout=config["timeout_seconds"])
        self.client = client

    def complete(self, messages, schema, metadata):
        common = {"model": self.config["model"], "input": messages,
                  "text": {"format": {"type": "json_schema", "name": "ranking",
                                      "strict": True, "schema": schema}}}
        start, cpu_start = time.perf_counter(), time.process_time()
        record = {**metadata, "model": self.config["model"], "status": "not_called",
                  "prompt_sha256": hashlib.sha256(json.dumps(common, sort_keys=True).encode()).hexdigest(),
                  "count_endpoint_calls": 1, "generation_attempts": 0, "usage": None,
                  "actual_known_usd": 0, "text": "", "error": None}
        try:
            count_start = time.perf_counter()
            counted = self.client.responses.input_tokens.count(**common).input_tokens
            record["count_latency_ms"] = (time.perf_counter() - count_start) * 1000
            record["preflight_input_tokens"] = counted
        except Exception as error:
            # Never serialize exception strings: they can contain request headers or credentials.
            record.update(status="count_error", error=type(error).__name__)
            record["total_latency_ms"] = (time.perf_counter() - start) * 1000
            return record
        if counted > self.config["max_input_tokens"]:
            record.update(status="input_limit", total_latency_ms=(time.perf_counter() - start) * 1000)
            return record
        price = self.config["pricing"]
        reserve_input = counted + self.config["input_reservation_margin_tokens"]
        worst = usage_cost({"input_tokens": reserve_input, "output_tokens": self.config["max_output_tokens"]}, price)
        call_id = self.budget.reserve(worst, metadata)
        record.update(call_id=call_id, reserved_usd=worst, generation_attempts=1)
        generation_start = time.perf_counter()
        try:
            response = self.client.responses.create(**common, store=False,
                max_output_tokens=self.config["max_output_tokens"], temperature=self.config["temperature"])
            usage = response.usage.model_dump() if response.usage is not None else None
            record.update(response_id=response.id, returned_model=response.model, text=response.output_text,
                          status=response.status, usage=usage,
                          incomplete_details=(response.incomplete_details.model_dump()
                                              if response.incomplete_details else None),
                          actual_known_usd=usage_cost(usage, price) if usage else None)
        except Exception as error:
            record.update(status="generation_error", error=type(error).__name__,
                          http_status=getattr(error, "status_code", None), actual_known_usd=None)
        record.update(generation_latency_ms=(time.perf_counter() - generation_start) * 1000,
                      total_latency_ms=(time.perf_counter() - start) * 1000,
                      client_cpu_seconds=time.process_time() - cpu_start)
        self.budget.settle(call_id, record["actual_known_usd"], record["status"])
        return record
