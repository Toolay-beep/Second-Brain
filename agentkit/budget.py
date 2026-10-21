"""Budgets, loop guards and swarm controls for token-conscious agent loops.

- Budget: thread-safe ceiling on tokens / iterations, shareable by many agents.
- LoopGuard: bounded loop with a no-progress detector (same state fingerprint
  repeated) and diminishing-returns detector (score stops improving).
- SwarmController: caps concurrency, spawn depth and total agents; one budget
  and one kill switch for the whole swarm.

Stopping conditions such as a maximum number of iterations are recommended in
Anthropic's "Building effective agents" (SOURCES.md, [S1]).
"""

from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    pass


class NoProgress(RuntimeError):
    pass


class SwarmHalted(RuntimeError):
    pass


@dataclass
class Budget:
    max_tokens: int
    max_iterations: int | None = None
    used_tokens: int = 0
    iterations: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def charge(self, tokens: int, iterations: int = 0) -> None:
        """Record spend; raise BudgetExceeded once a limit is crossed."""
        with self._lock:
            self.used_tokens += tokens
            self.iterations += iterations
            if self.used_tokens > self.max_tokens:
                raise BudgetExceeded(f"tokens {self.used_tokens} > {self.max_tokens}")
            if self.max_iterations is not None and self.iterations > self.max_iterations:
                raise BudgetExceeded(f"iterations {self.iterations} > {self.max_iterations}")

    def charge_usage(self, usage: dict) -> None:
        """Charge an API `usage` dict (all input incl. cache, plus output)."""
        self.charge(
            usage.get("input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("output_tokens", 0)
        )

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    def fraction_used(self) -> float:
        return self.used_tokens / self.max_tokens if self.max_tokens else 1.0


def fingerprint(state) -> str:
    """Stable hash of a JSON-serialisable state (e.g. failing tests, diff)."""
    blob = json.dumps(state, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


class LoopGuard:
    """Use in a loop: `for i in guard: ...; guard.observe(state, score)`.

    Stops (raises) when:
      * max_iterations reached (StopIteration -> loop ends normally),
      * the same state fingerprint is seen `repeat_limit` times (NoProgress),
      * the best score hasn't improved by `min_gain` for `patience` steps (NoProgress),
      * the attached Budget is exhausted (BudgetExceeded).
    """

    def __init__(self, max_iterations: int, repeat_limit: int = 2, patience: int | None = None,
                 min_gain: float = 0.0, budget: Budget | None = None):
        self.max_iterations = max_iterations
        self.repeat_limit = repeat_limit
        self.patience = patience
        self.min_gain = min_gain
        self.budget = budget
        self.seen: dict[str, int] = {}
        self.best: float | None = None
        self.stale = 0
        self.i = 0

    def __iter__(self):
        while self.i < self.max_iterations:
            if self.budget is not None:
                self.budget.charge(0, iterations=1)
            yield self.i
            self.i += 1

    def observe(self, state=None, score: float | None = None) -> None:
        if state is not None:
            fp = fingerprint(state)
            self.seen[fp] = self.seen.get(fp, 0) + 1
            if self.seen[fp] >= self.repeat_limit:
                raise NoProgress(f"state {fp} repeated {self.seen[fp]}x")
        if score is not None and self.patience is not None:
            if self.best is None or score > self.best + self.min_gain:
                self.best, self.stale = score, 0
            else:
                self.stale += 1
                if self.stale >= self.patience:
                    raise NoProgress(f"no gain > {self.min_gain} for {self.stale} steps (best={self.best})")


class SwarmController:
    """Admission control for sub-agents.

    with swarm.agent(depth=1):  # blocks while at max_concurrency
        ... run sub-agent, call swarm.budget.charge_usage(resp.usage) ...
    """

    def __init__(self, budget: Budget, max_concurrency: int = 4, max_depth: int = 2, max_agents: int = 16):
        self.budget = budget
        self.max_depth = max_depth
        self.max_agents = max_agents
        self.spawned = 0
        self._sem = threading.BoundedSemaphore(max_concurrency)
        self._lock = threading.Lock()
        self._halt = threading.Event()
        self.halt_reason: str | None = None

    def halt(self, reason: str) -> None:
        self.halt_reason = reason
        self._halt.set()

    @property
    def halted(self) -> bool:
        return self._halt.is_set()

    def check(self) -> None:
        """Call between steps inside each agent; raises if the swarm was halted."""
        if self._halt.is_set():
            raise SwarmHalted(self.halt_reason or "halted")

    @contextmanager
    def agent(self, depth: int):
        self.check()
        if depth > self.max_depth:
            raise SwarmHalted(f"depth {depth} > max_depth {self.max_depth}")
        with self._lock:
            if self.spawned >= self.max_agents:
                raise SwarmHalted(f"max_agents {self.max_agents} reached")
            self.spawned += 1
        with self._sem:
            try:
                yield self
            except BudgetExceeded as e:
                self.halt(f"budget: {e}")
                raise
