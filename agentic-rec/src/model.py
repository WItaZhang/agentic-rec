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
        scores = self.score_items(positive_history)
        order = sorted(range(len(self.catalog)),
                       key=lambda i: (-scores[i], -self.popularity[i], self.catalog[i]))
        return [self.catalog[i] for i in order if self.catalog[i] not in seen][:k]

    def score_items(self, positive_history):
        import numpy as np

        indices = {item: index for index, item in enumerate(self.catalog)}
        # Floating point addition is order-dependent; string-set iteration varies
        # across processes and must not perturb candidate hashes or tie ordering.
        known = sorted(indices[item] for item in set(positive_history) if item in indices)
        return np.asarray(self.similarity[known].sum(axis=0)).ravel()
