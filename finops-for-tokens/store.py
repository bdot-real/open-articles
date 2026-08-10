"""Spend counters.

Two implementations behind one protocol. InMemory so the tests and the demo run
with no infrastructure, Redis for anything real.

The counter must be shared across every replica that can serve a request. A
per-process counter is not a budget, it is a budget multiplied by your replica
count, which is the sort of thing you find out during the incident.
"""
from typing import Protocol


class SpendStore(Protocol):
    def get(self, key: str) -> float: ...
    def add(self, key: str, amount: float, ttl_seconds: int = 172_800) -> float: ...


class InMemoryStore:
    """Single process only. Tests and demos."""

    def __init__(self) -> None:
        self._d: dict[str, float] = {}

    def get(self, key: str) -> float:
        return self._d.get(key, 0.0)

    def add(self, key: str, amount: float, ttl_seconds: int = 172_800) -> float:
        self._d[key] = self._d.get(key, 0.0) + amount
        return self._d[key]


class RedisStore:
    """Shared counters. INCRBYFLOAT is atomic, which matters under concurrency."""

    def __init__(self, client) -> None:
        self._r = client

    def get(self, key: str) -> float:
        v = self._r.get(key)
        return float(v) if v else 0.0

    def add(self, key: str, amount: float, ttl_seconds: int = 172_800) -> float:
        pipe = self._r.pipeline()
        pipe.incrbyfloat(key, amount)
        pipe.expire(key, ttl_seconds)
        total, _ = pipe.execute()
        return float(total)
