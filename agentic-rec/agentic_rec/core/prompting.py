"""Minimal prompt helpers (no template engine dependency)."""

from __future__ import annotations

from collections.abc import Iterable

from .types import Item, Message


def bullet(lines: Iterable[str], marker: str = "-") -> str:
    return "\n".join(f"{marker} {ln}" for ln in lines)


def render_items(items: Iterable[Item], limit: int | None = None) -> str:
    rows = [it.describe() for it in items]
    if limit is not None:
        rows = rows[:limit]
    return bullet(rows) if rows else "(none)"


def render_dialogue(messages: Iterable[Message], limit: int | None = None) -> str:
    msgs = list(messages)
    if limit is not None:
        msgs = msgs[-limit:]
    return "\n".join(f"{m.role}: {m.content}" for m in msgs) if msgs else "(no dialogue yet)"


def section(title: str, body: str) -> str:
    body = body.strip() or "(empty)"
    return f"## {title}\n{body}\n"
