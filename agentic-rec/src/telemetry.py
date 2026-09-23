"""Exact local-token reservation and attempt-level accounting."""

from dataclasses import dataclass


@dataclass
class TokenBudget:
    token_limit: int
    call_limit: int
    used_tokens: int = 0
    calls: int = 0
    reserved: int = 0
    usage_unknown: bool = False

    def reserve(self, input_tokens, max_output_tokens):
        amount = input_tokens + max_output_tokens
        if self.usage_unknown or self.reserved or self.calls >= self.call_limit:
            return False
        if min(input_tokens, max_output_tokens) < 0 or self.used_tokens + amount > self.token_limit:
            return False
        self.reserved = amount
        self.calls += 1  # Attempts, including failed generation, consume the call limit.
        return True

    def settle(self, input_tokens, output_tokens):
        if not self.reserved:
            raise ValueError("No active reservation")
        if input_tokens is None or output_tokens is None:
            self.used_tokens += self.reserved
            self.usage_unknown = True
        else:
            amount = input_tokens + output_tokens
            if amount > self.reserved:
                raise ValueError("Observed usage exceeds reservation")
            self.used_tokens += amount
        self.reserved = 0
