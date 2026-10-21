# 03 · Token-conscious loops

## What the sources establish

- Use stopping conditions such as a maximum number of iterations to stay in control. [S1]
- Agents "struggle to judge appropriate effort". Anthropic put scaling rules into its prompts: 1 agent with 3–10 tool calls for simple fact-finding, 2–4 subagents with 10–15 calls each for comparisons, and more than 10 subagents for complex research. [S2]
- **Every turn resends the whole history.** Claude Code sends the full conversation with every request, so long sessions cost more per turn. A break longer than the cache lifetime causes a cache miss. [S4]
- **Cheaper levers** [S4]: `/clear` between unrelated tasks, use a smaller model for simple subagents, lower the effort level for simple tasks, use hooks to filter verbose output (for example, show only failing tests), write specific prompts, and stop early with Esc or `/rewind`.
- A `Stop` hook can block Claude from stopping (`{"decision":"block","reason":...}` or exit code 2). The docs warn you to check `stop_hook_active` "to avoid blocking on a condition that will never resolve". [S6]

## Loop design (*Practice*)

1. **Budget first.** Fix tokens and iterations before the loop starts (`agentkit.budget.Budget`).
2. **Detect no-progress, not just failure.** Fingerprint the observable state, such as the failing-test set or a diff hash. If the same fingerprint comes back, the loop is cycling (`LoopGuard(repeat_limit=2)`).
3. **Detect diminishing returns.** Track a score and stop after `patience` steps without a gain above `min_gain`.
4. **Keep the prompt prefix stable** so caching works: system prompt and tools first, volatile content last.
5. **Feed back summaries, not raw logs** ([05](05-context-compression.md)).
6. **Escalate instead of spinning.** When a guard trips, hand off to a human or a stronger model with the evidence attached.

```python
from agentkit.budget import Budget, LoopGuard, NoProgress
b = Budget(max_tokens=200_000)
g = LoopGuard(max_iterations=6, repeat_limit=2, patience=2, min_gain=0.01, budget=b)
try:
    for i in g:
        resp = call_model(...)
        b.charge_usage(resp.usage)
        failing = run_tests()
        if not failing: break
        g.observe(state=sorted(failing), score=-len(failing))
except NoProgress as e:
    escalate(e)
```
