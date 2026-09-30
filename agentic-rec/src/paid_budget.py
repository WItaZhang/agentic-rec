"""Durable USD reservations shared by all experiment runs, including interrupted calls."""

import hashlib
import json
import math
import os
import time
import uuid
from pathlib import Path

from filelock import FileLock


class BudgetExceeded(RuntimeError):
    pass


class PaidBudget:
    def __init__(self, path, run_id, total_usd, run_usd, stop_usd):
        if not 0 < run_usd <= stop_usd <= total_usd or not math.isfinite(total_usd):
            raise ValueError("Invalid paid budget limits")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(path) + ".lock")
        self.run_id, self.total, self.run_cap, self.stop = run_id, total_usd, run_usd, stop_usd

    def _read(self):
        calls = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)  # Corruption fails closed; never silently drop spending.
                if event["event"] == "reserve":
                    calls[event["call_id"]] = event
                else:
                    calls[event["call_id"]].update(event)
        return calls

    def _append(self, event):
        self._append_many([event])

    def _append_many(self, events):
        # Serialize before writing. The caller holds the cross-process lock;
        # fsync completes before any corresponding network request may begin.
        payload = "".join(json.dumps({"timestamp": time.time(), **event}) + "\n" for event in events)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _charge(call):
        return call["reserved_usd"] if call.get("actual_usd") is None else call["actual_usd"]

    def reserve(self, amount, metadata):
        return self.reserve_many([(amount, metadata)])[0]

    def reserve_many(self, requests):
        """Reserve a whole shard under one lock and ledger read; denial writes nothing."""
        if not requests or any(not math.isfinite(amount) or amount <= 0 for amount, _ in requests):
            raise ValueError("A positive finite reservation is required")
        amount = sum(value for value, _ in requests)
        with self.lock:
            calls = self._read()
            total = sum(self._charge(c) for c in calls.values())
            current = sum(self._charge(c) for c in calls.values() if c["run_id"] == self.run_id)
            if total + amount > min(self.total, self.stop) or current + amount > self.run_cap:
                raise BudgetExceeded("Reservation would exceed the campaign or round spending limit")
            events = [{"event": "reserve", "call_id": uuid.uuid4().hex, "run_id": self.run_id,
                       "reserved_usd": value, "metadata": metadata} for value, metadata in requests]
            self._append_many(events)
            return [event["call_id"] for event in events]

    def settle(self, call_id, actual_usd, status):
        self.settle_many([(call_id, actual_usd, status)])

    def settle_many(self, settlements):
        """Record every physical charge before raising on any reservation overage."""
        if any(actual is not None and (not math.isfinite(actual) or actual < 0)
               for _, actual, _ in settlements):
            raise ValueError("Invalid measured charge")
        if len({identity for identity, _, _ in settlements}) != len(settlements):
            raise ValueError("Duplicate settlement in shard")
        if not settlements:
            return
        with self.lock:
            calls = self._read()
            for identity, _, _ in settlements:
                if calls[identity]["run_id"] != self.run_id or calls[identity]["event"] != "reserve":
                    raise ValueError("Wrong owner or already settled")
            self._append_many([{"event": "settle", "call_id": identity, "actual_usd": actual, "status": status}
                               for identity, actual, status in settlements])
            if any(actual is not None and actual > calls[identity]["reserved_usd"] + 1e-12
                   for identity, actual, _ in settlements):
                raise BudgetExceeded("Actual charge exceeded reservation; recorded actual charge and stopped")

    def snapshot(self):
        with self.lock:
            calls = self._read()
        return {"campaign_accounted_usd": sum(self._charge(c) for c in calls.values()),
                "round_accounted_usd": sum(self._charge(c) for c in calls.values()
                                           if c["run_id"] == self.run_id),
                "campaign_actual_known_usd": sum(c.get("actual_usd") or 0 for c in calls.values()),
                "unknown_or_pending_calls": sum(c.get("actual_usd") is None for c in calls.values()),
                "pending_reservations": sum(c["event"] == "reserve" for c in calls.values()),
                "unknown_settled_calls": sum(c["event"] == "settle" and c["actual_usd"] is None for c in calls.values()),
                "campaign_attempts": len(calls), "total_authorized_usd": self.total,
                "round_cap_usd": self.run_cap, "planning_stop_usd": self.stop}

    def entries(self):
        with self.lock:
            return self._read()

    def validate_queue_rejection(self, receipt):
        """Require explicit batch-level zero usage, not inference from missing rows."""
        errors = (receipt.get("errors") or {}).get("data") or []
        counts, usage = receipt.get("request_counts") or {}, receipt.get("usage") or {}
        if (not receipt.get("id") or receipt.get("status") != "failed" or receipt.get("in_progress_at") is not None
                or receipt.get("output_file_id") or receipt.get("error_file_id")
                or not errors or any(e.get("code") != "token_limit_exceeded" for e in errors)
                or any(counts.get(k) != 0 for k in ("total", "completed", "failed"))
                or any(usage.get(k) != 0 for k in ("input_tokens", "output_tokens"))
                or (receipt.get("metadata") or {}).get("research_run") != self.run_id):
            raise ValueError("Provider evidence does not establish a zero-generation queue rejection")
        return hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()

    def reconcile_queue_rejection(self, identities, receipt):
        """Release only a provider-proven queue rejection before any generation."""
        proof = self.validate_queue_rejection(receipt)
        if not identities or len(set(identities)) != len(identities):
            raise ValueError("Unique original reservations required")
        with self.lock:
            entries = self._read()
            pending = []
            for identity in identities:
                old = entries[identity]
                if (old['run_id'] == self.run_id and old.get('actual_usd') == 0
                        and old.get('status') == 'submission_rejected_before_generation'
                        and old.get('reconciliation_evidence_sha256') == proof):
                    continue  # Safe checkpoint recovery after a settled-ledger interruption.
                if (old['run_id'] != self.run_id or old.get('actual_usd') is not None
                        or (old['event'] == 'settle' and old['status'] != 'missing_batch_result')):
                    raise ValueError("Only original pending or unknown missing-result charges can be reconciled")
                pending.append(identity)
            self._append_many([{'event': 'settle', 'call_id': identity, 'actual_usd': 0.0,
                'status': 'submission_rejected_before_generation', 'provider_code': 'token_limit_exceeded',
                'provider_batch_id': receipt['id'], 'reconciliation_evidence_sha256': proof} for identity in pending])


def usage_cost(usage, pricing):
    """Provider token usage -> estimated bill at frozen public prices, not an invoice."""
    input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    if not 0 <= cached <= input_tokens or output_tokens < 0:
        raise ValueError("Invalid provider usage")
    return ((input_tokens - cached) * pricing["input_per_million_usd"]
            + cached * pricing["cached_input_per_million_usd"]
            + output_tokens * pricing["output_per_million_usd"]) / 1_000_000
