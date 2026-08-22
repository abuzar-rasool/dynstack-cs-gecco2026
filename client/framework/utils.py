"""
Pure framework utilities: no policy, no protobuf knowledge.
"""
from __future__ import annotations

from typing import Callable, Iterable, TypeVar

_T = TypeVar("_T")


def argmin_or_none(items: Iterable[_T], key: Callable[[_T], float]) -> _T | None:
    """The item with the smallest key, or None when `items` is empty.

    Hooks return None to decline a decision, so an empty candidate list has
    to collapse to None rather than raise.
    """
    items = list(items)
    if not items:
        return None
    return min(items, key=key)
