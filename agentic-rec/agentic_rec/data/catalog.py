from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from typing import Any

from ..core.types import Interaction, Item

_TOKEN = re.compile(r"[a-z0-9]+")


class Catalog:
    """Item store with attribute indexes, keyword search and co-occurrence stats.

    It is deliberately small: enough for tools to filter, search, rank and
    look up items, while remaining a pure-Python object that any real
    retrieval backend can replace.
    """

    def __init__(self, items: Iterable[Item] = ()) -> None:
        self._items: dict[str, Item] = {}
        self._attr_index: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        self._popularity: dict[str, int] = defaultdict(int)
        self._cooc: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for it in items:
            self.add(it)

    # ------------------------------------------------------------- mutation
    def add(self, item: Item) -> None:
        self._items[item.id] = item
        for k, v in item.attrs.items():
            for val in v if isinstance(v, (list, tuple, set)) else [v]:
                if val is not None:
                    self._attr_index[k][str(val).lower()].add(item.id)

    def fit_interactions(self, interactions: Iterable[Interaction]) -> None:
        """Compute popularity and item-item co-occurrence from a history log."""
        by_user: dict[str, list[str]] = defaultdict(list)
        for x in interactions:
            if x.item_id in self._items:
                by_user[x.user_id].append(x.item_id)
                self._popularity[x.item_id] += 1
        for items in by_user.values():
            uniq = list(dict.fromkeys(items))
            for i in uniq:
                for j in uniq:
                    if i != j:
                        self._cooc[i][j] += 1

    # -------------------------------------------------------------- queries
    def has(self, item_id: str) -> bool:
        return item_id in self._items

    def get(self, item_id: str) -> Item:
        return self._items[item_id]

    def ids(self) -> list[str]:
        return list(self._items)

    def __iter__(self) -> Iterator[Item]:
        return iter(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def popularity(self, item_id: str) -> int:
        return self._popularity.get(item_id, 0)

    def most_popular(self, k: int = 10, exclude: set[str] | None = None) -> list[str]:
        exclude = exclude or set()
        ranked = sorted(self._items, key=lambda i: -self._popularity.get(i, 0))
        return [i for i in ranked if i not in exclude][:k]

    def filter(self, **conditions: Any) -> list[str]:
        """Return ids matching *all* ``attr=value`` conditions (case-insensitive)."""
        result: set[str] | None = None
        for k, v in conditions.items():
            vals = v if isinstance(v, (list, tuple, set)) else [v]
            hits: set[str] = set()
            for val in vals:
                hits |= self._attr_index.get(k, {}).get(str(val).lower(), set())
            result = hits if result is None else result & hits
        return sorted(result or [])

    def search(self, query: str, k: int = 10) -> list[str]:
        """Keyword search over title + text + attribute values."""
        q = set(_TOKEN.findall(query.lower()))
        if not q:
            return []
        scored = []
        for it in self._items.values():
            text = " ".join([it.title, str(it.attrs.get("text", "")), *map(str, it.attrs.values())]).lower()
            toks = set(_TOKEN.findall(text))
            overlap = len(q & toks)
            if overlap:
                scored.append((overlap, self._popularity.get(it.id, 0), it.id))
        scored.sort(reverse=True)
        return [i for _, _, i in scored[:k]]

    def similar(self, item_ids: Iterable[str], k: int = 10, exclude: set[str] | None = None) -> list[str]:
        """Item-kNN by co-occurrence (a stand-in for any embedding retriever)."""
        exclude = set(exclude or ())
        scores: dict[str, float] = defaultdict(float)
        for i in item_ids:
            for j, c in self._cooc.get(i, {}).items():
                if j not in exclude:
                    scores[j] += c
        if not scores:
            return self.most_popular(k, exclude)
        return sorted(scores, key=lambda j: -scores[j])[:k]

    def score(self, candidates: Iterable[str], seed: Iterable[str]) -> dict[str, float]:
        """Score candidates by co-occurrence with the seed set (+ small popularity prior)."""
        seed = list(seed)
        out = {}
        for c in candidates:
            s = sum(self._cooc.get(i, {}).get(c, 0) for i in seed)
            out[c] = s + 0.01 * self._popularity.get(c, 0)
        return out

    def attr_values(self, attr: str) -> list[str]:
        return sorted(self._attr_index.get(attr, {}))
