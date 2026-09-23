"""Deterministic non-LLM popularity model. No fitting or data loading."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PopularityModel:
    ranked_items: tuple[int, ...]

    def recommend(self, seen: set[int], k: int) -> list[int]:
        return [item for item in self.ranked_items if item not in seen][:k]


@dataclass(frozen=True)
class ItemKNNModel:
    """Binary-positive cosine graph, source-row top-K, popularity tie fallback."""

    catalog: tuple
    similarity: object
    popularity: tuple

    @property
    def ranked_items(self):
        return self.catalog

    def recommend(self, seen, k, positive_history=()):
        import numpy as np

        indices = {item: index for index, item in enumerate(self.catalog)}
        known = [indices[item] for item in set(positive_history) if item in indices]
        scores = np.asarray(self.similarity[known].sum(axis=0)).ravel()
        order = sorted(range(len(self.catalog)),
                       key=lambda i: (-scores[i], -self.popularity[i], self.catalog[i]))
        return [self.catalog[i] for i in order if self.catalog[i] not in seen][:k]
