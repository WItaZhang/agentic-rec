"""Durable USD reservations shared by all experiment runs, including interrupted calls."""

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
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"timestamp": time.time(), **event}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _charge(call):
        return call["reserved_usd"] if call.get("actual_usd") is None else call["actual_usd"]

    def reserve(self, amount, metadata):
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("A positive finite reservation is required")
        with self.lock:
            calls = self._read()
            total = sum(self._charge(c) for c in calls.values())
            current = sum(self._charge(c) for c in calls.values() if c["run_id"] == self.run_id)
            if total + amount > min(self.total, self.stop) or current + amount > self.run_cap:
                raise BudgetExceeded("Reservation would exceed the campaign or round spending limit")
            call_id = uuid.uuid4().hex
            self._append({"event": "reserve", "call_id": call_id, "run_id": self.run_id,
                          "reserved_usd": amount, "metadata": metadata})
            return call_id

    def settle(self, call_id, actual_usd, status):
        if actual_usd is not None and (not math.isfinite(actual_usd) or actual_usd < 0):
            raise ValueError("Invalid measured charge")
        with self.lock:
            call = self._read()[call_id]
            if call["run_id"] != self.run_id or call["event"] != "reserve":
                raise ValueError("Wrong owner or already settled")
            self._append({"event": "settle", "call_id": call_id,
                          "actual_usd": actual_usd, "status": status})
            if actual_usd is not None and actual_usd > call["reserved_usd"] + 1e-12:
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


def usage_cost(usage, pricing):
    """Provider token usage -> estimated bill at frozen public prices, not an invoice."""
    input_tokens, output_tokens = usage["input_tokens"], usage["output_tokens"]
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    if not 0 <= cached <= input_tokens or output_tokens < 0:
        raise ValueError("Invalid provider usage")
    return ((input_tokens - cached) * pricing["input_per_million_usd"]
            + cached * pricing["cached_input_per_million_usd"]
            + output_tokens * pricing["output_per_million_usd"]) / 1_000_000
