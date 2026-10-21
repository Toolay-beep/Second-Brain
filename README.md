# Second Brain: Agentic SDLC

Cited notes plus a small stdlib-only Python toolkit (`agentkit`) covering eight practices for building software with LLM agents.

| # | Topic | Note | Tool |
|---|---|---|---|
| 1 | Agentic SDLC practice | [notes/01](notes/01-agentic-sdlc.md) | — |
| 2 | Token spend analytics | [notes/02](notes/02-token-spend-analytics.md) | `agentkit.spend` |
| 3 | Token-conscious loops | [notes/03](notes/03-token-conscious-loops.md) | `agentkit.budget.LoopGuard`, `Budget` |
| 4 | Agentic swarm controls | [notes/04](notes/04-agentic-swarm-controls.md) | `agentkit.budget.SwarmController` |
| 5 | Context compression | [notes/05](notes/05-context-compression.md) | `agentkit.compress` |
| 6 | Deterministic delivery pipelines | [notes/06](notes/06-deterministic-delivery-pipelines.md) | `scripts/pipeline.sh` |
| 7 | Codebase agentic manifest & hashing | [notes/07](notes/07-agentic-manifest-and-hashing.md) | `agentkit.manifest`, [AGENTS.md](AGENTS.md) |
| 8 | Self-healing agents | [notes/08](notes/08-self-healing-agents.md) | `agentkit.heal` |

## Citation convention

- `[S#]` marks a claim from a source in [SOURCES.md](SOURCES.md). Each source shows whether it was checked **directly** (page fetched) or only via **search** excerpts.
- **Practice** marks the author's own synthesis. It is opinion, not a sourced claim, so test it before relying on it.
- Some of these topic names (for example "agentic SDLC" and "agentic manifest") aren't industry-standard terms. The notes say so where it applies.

## Quick start

```bash
make test       # 20 unit tests, Python 3.10+, no dependencies
make spend      # spend report on sample data (placeholder prices)
make manifest   # rebuild agent-manifest.json after changing files
make ci         # deterministic gate: manifest verify → tests → determinism check
```
