"""Self-healing loop: attempt -> verify -> reflect -> retry, with hard stops.

The reflect step keeps a short memory of what failed and why, then feeds it to
the next attempt. This follows the Reflexion pattern (verbal feedback kept in an
episodic memory, SOURCES.md [S8]), with the verifier as the ground truth.
Retries are bounded by a LoopGuard (max attempts, repeated-failure detection,
optional budget) so a stuck agent stops early instead of burning tokens.

    result = self_heal(
        attempt=lambda memory: agent.fix(task, memory),
        verify=lambda r: run_tests(r),            # -> (ok: bool, report: dict|str)
        reflect=lambda report: summarize(report),  # -> short lesson (str)
        max_attempts=4,
    )
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .budget import Budget, LoopGuard, NoProgress


@dataclass
class HealResult:
    ok: bool
    value: Any
    attempts: int
    memory: list[str] = field(default_factory=list)
    stop_reason: str = ""


def self_heal(attempt: Callable[[list[str]], Any],
              verify: Callable[[Any], tuple[bool, Any]],
              reflect: Callable[[Any], str] = str,
              max_attempts: int = 3,
              budget: Budget | None = None,
              memory_limit: int = 5) -> HealResult:
    guard = LoopGuard(max_iterations=max_attempts, repeat_limit=2, budget=budget)
    memory: list[str] = []
    value = None
    n = 0
    try:
        for n in guard:
            value = attempt(list(memory))
            ok, report = verify(value)
            if ok:
                return HealResult(True, value, n + 1, memory, "verified")
            guard.observe(state=report)  # identical failure twice -> NoProgress
            memory.append(reflect(report))
            memory[:] = memory[-memory_limit:]
    except NoProgress as e:
        return HealResult(False, value, n + 1, memory, f"no progress: {e}")
    return HealResult(False, value, max_attempts, memory, "max attempts")


class CircuitOpen(RuntimeError):
    pass


class CircuitBreaker:
    """Stop calling a failing dependency (tool, model, MCP server) for a cool-down.

    closed -> (failure_threshold consecutive failures) -> open
    open   -> (reset_after seconds)                    -> half-open (one trial call)
    """

    def __init__(self, failure_threshold: int = 3, reset_after: float = 30.0, clock=time.monotonic):
        self.failure_threshold = failure_threshold
        self.reset_after = reset_after
        self.clock = clock
        self.failures = 0
        self.opened_at: float | None = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half-open" if self.clock() - self.opened_at >= self.reset_after else "open"

    def call(self, fn: Callable, *args, **kwargs):
        if self.state == "open":
            raise CircuitOpen(f"open; retry after {self.reset_after}s")
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self.failures += 1
            if self.state == "half-open" or self.failures >= self.failure_threshold:
                self.opened_at = self.clock()
            raise
        self.failures = 0
        self.opened_at = None
        return result
