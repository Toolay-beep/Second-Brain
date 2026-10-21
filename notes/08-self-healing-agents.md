# 08 · Self-healing agents

## What the sources establish

- **Evaluator-optimizer:** one LLM generates and another evaluates in a loop. [S1]
- **Self-Refine:** a single LLM acts as generator, feedback provider and refiner, with no extra training. It reports an average improvement of about 20% absolute across 7 tasks. [S9]
- **Reflexion:** agents improve "not by updating weights, but instead through linguistic feedback", keeping reflections in an episodic memory buffer for later attempts. [S8]
- **Verification failures** are one of the three MAST failure categories for multi-agent systems. [S14]
- A Claude Code `Stop` hook can force continuation until a check passes. It must honour `stop_hook_active` so it can't block forever. [S6]

## Pattern (*Practice*)

```
attempt(memory) ─► verify (tests/linters = ground truth)
      ▲                 │ fail
      └── reflect ◄─────┘   (short lesson, appended to bounded memory)
stop when: verified | same failure twice | max attempts | budget exhausted → escalate
```

Principles:
1. **The verifier must be external and deterministic** where possible (tests, type checker, schema). Self-assessment on its own is weaker evidence.
2. **Bound everything:** attempts, memory size and tokens ([03](03-token-conscious-loops.md)).
3. **Identical failure twice means stop.** Retrying the same thing is not healing.
4. **Circuit-break flaky dependencies** (tools, MCP servers, model endpoints) instead of hammering them.
5. **Never "heal" by weakening the check.** Don't skip tests or loosen assertions. Make this a hard rule in AGENTS.md.

## Tool: `agentkit.heal`

- `self_heal(attempt, verify, reflect, max_attempts, budget)` → `HealResult(ok, value, attempts, memory, stop_reason)`
- `CircuitBreaker(failure_threshold, reset_after)`: closed → open → half-open.
