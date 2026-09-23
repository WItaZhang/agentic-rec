"""Deterministic non-LLM popularity model. No fitting or data loading."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PopularityModel:
    ranked_items: tuple[int, ...]

    def recommend(self, seen: set[int], k: int) -> list[int]:
        return [item for item in self.ranked_items if item not in seen][:k]
