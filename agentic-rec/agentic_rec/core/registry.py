"""A tiny string-keyed component registry.

Components register under a *kind* (``"memory"``, ``"planner"`` ...) and a
*name*.  Configuration files reference them by these strings, which keeps the
config layer decoupled from concrete classes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class Registry:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Callable[..., Any]]] = {}

    def register(self, kind: str, name: str) -> Callable[[T], T]:
        def deco(obj: T) -> T:
            self._store.setdefault(kind, {})[name] = obj  # type: ignore[assignment]
            return obj

        return deco

    def get(self, kind: str, name: str) -> Callable[..., Any]:
        try:
            return self._store[kind][name]
        except KeyError as e:
            available = ", ".join(sorted(self._store.get(kind, {}))) or "<none>"
            raise KeyError(f"unknown {kind} '{name}'. available: {available}") from e

    def names(self, kind: str) -> list[str]:
        return sorted(self._store.get(kind, {}))

    def kinds(self) -> list[str]:
        return sorted(self._store)

    def create(self, kind: str, spec: str | dict[str, Any] | None, **overrides: Any) -> Any:
        """Instantiate ``spec``.

        ``spec`` may be ``None`` (returns None), a bare name, or a dict with a
        ``type`` key and constructor kwargs.  ``overrides`` are injected as
        extra kwargs (e.g. a shared ``llm`` instance) only when the target
        constructor accepts them.
        """
        if spec is None:
            return None
        if isinstance(spec, str):
            name, kwargs = spec, {}
        else:
            spec = dict(spec)
            name = spec.pop("type")
            kwargs = spec
        factory = self.get(kind, name)
        kwargs = {**_accepted(factory, overrides), **kwargs}
        return factory(**kwargs)


def _accepted(factory: Callable[..., Any], candidates: dict[str, Any]) -> dict[str, Any]:
    import inspect

    try:
        params = inspect.signature(factory).parameters
    except (TypeError, ValueError):  # pragma: no cover - builtins
        return {}
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return dict(candidates)
    return {k: v for k, v in candidates.items() if k in params}


registry = Registry()
