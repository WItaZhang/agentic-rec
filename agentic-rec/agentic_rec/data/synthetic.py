"""A small synthetic movie-style dataset with latent genre preferences.

Users are drawn with a preference vector over genres; histories are sampled
from that vector.  Because the ground-truth preferences are known, the
dataset supports both offline ranking metrics and rule-based user
simulation without any external files.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..core.types import Interaction, Item, User
from .catalog import Catalog

GENRES = ["action", "comedy", "drama", "sci-fi", "romance", "thriller", "animation", "documentary"]
_ADJ = ["Silent", "Broken", "Golden", "Last", "Hidden", "Electric", "Lost", "Wild", "Distant", "Crimson"]
_NOUN = ["Horizon", "Empire", "Garden", "Signal", "Harbor", "Machine", "Summer", "Kingdom", "Orbit", "Echo"]


@dataclass
class SyntheticDataset:
    catalog: Catalog
    users: list[User]
    truth: dict[str, dict[str, float]] = field(default_factory=dict)  # user -> genre -> weight
    holdout: dict[str, list[str]] = field(default_factory=dict)  # user -> held-out positives

    def user(self, user_id: str) -> User:
        return next(u for u in self.users if u.id == user_id)


def make_synthetic(
    n_items: int = 200,
    n_users: int = 50,
    history_len: int = 15,
    holdout_len: int = 3,
    seed: int = 0,
) -> SyntheticDataset:
    rng = random.Random(seed)
    items: list[Item] = []
    for i in range(n_items):
        genre = rng.choice(GENRES)
        second = rng.choice(GENRES)
        genres = [genre] if second == genre else [genre, second]
        items.append(
            Item(
                id=f"i{i}",
                title=f"{rng.choice(_ADJ)} {rng.choice(_NOUN)} {i}",
                attrs={"genre": genres, "year": rng.randint(1980, 2025), "rating": round(rng.uniform(2.5, 5.0), 1)},
            )
        )
    catalog = Catalog(items)
    by_genre = {g: [it.id for it in items if g in it.attrs["genre"]] for g in GENRES}

    users: list[User] = []
    truth: dict[str, dict[str, float]] = {}
    holdout: dict[str, list[str]] = {}
    for u in range(n_users):
        fav = rng.sample(GENRES, 2)
        w = {g: 0.05 for g in GENRES}
        w[fav[0]] += 0.6
        w[fav[1]] += 0.3
        z = sum(w.values())
        w = {g: v / z for g, v in w.items()}
        truth[f"u{u}"] = w
        seen: list[str] = []
        pool_weights = [w[g] for g in GENRES]
        while len(seen) < history_len + holdout_len:
            g = rng.choices(GENRES, weights=pool_weights)[0]
            cand = rng.choice(by_genre[g]) if by_genre[g] else rng.choice(items).id
            if cand not in seen:
                seen.append(cand)
        hist, held = seen[:history_len], seen[history_len:]
        user = User(
            id=f"u{u}",
            history=[Interaction(f"u{u}", iid, "click", 1.0, t) for t, iid in enumerate(hist)],
            attrs={
                "likes": fav,
                "activity": rng.choice(["low", "medium", "high"]),
                "conformity": rng.choice(["low", "medium", "high"]),
                "diversity": rng.choice(["low", "medium", "high"]),
            },
        )
        users.append(user)
        holdout[user.id] = held
    catalog.fit_interactions(x for u in users for x in u.history)
    return SyntheticDataset(catalog=catalog, users=users, truth=truth, holdout=holdout)
