"""
Training and confirmation seeds live in disjoint namespaces, so a genome is
never confirmed on a seed it was trained on. Values are masked to 31 bits to
match the simulator's signed int32 seed field.
"""
from __future__ import annotations

import hashlib


def _digest(tag: str) -> int:
    return int.from_bytes(hashlib.sha256(tag.encode()).digest()[:4], "big") & 0x7FFFFFFF


def training_seed(master: int, generation: int, scenario: str, k: int = 0) -> int:
    tag = f"{master}:{generation}:{scenario}"
    if k:
        tag = f"{tag}:{k}"
    return _digest(tag)


def confirm_seed(master: int, index: int, scenario: str) -> int:
    return _digest(f"confirm:{master}:{index}:{scenario}")


def seed_variants(base: int, n: int) -> list[int]:
    """`n` distinct seeds from a base, with the base itself first."""
    seeds = [base]
    for k in range(1, n):
        seeds.append(_digest(f"{base}:{k}"))
    return seeds
