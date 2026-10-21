# 01 · Agentic SDLC practice

> "Agentic SDLC" is not a standardised term. This note uses it to mean running a software lifecycle in which LLM agents do some of the plan / code / test / review / ship work.

## What the sources establish

- **Workflows vs agents.** Workflows are "systems where LLMs and tools are orchestrated through predefined code paths". In agents, "LLMs dynamically direct their own processes and tool usage". [S1]
- **Five workflow patterns:** prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer. [S1]
- **Guardrails.** Autonomous agents call for "extensive testing in sandboxed environments, along with the appropriate guardrails", plus stopping conditions such as a maximum number of iterations. [S1]
- **Repo instructions for agents.** AGENTS.md is a convention for "a README for agents": build and test commands and conventions, in Markdown at the repo root. [S13] Claude Code advises keeping CLAUDE.md under about 200 lines and moving workflow-specific instructions into on-demand skills. [S4]
- **Verification targets cut rework.** Claude Code recommends giving Claude tests, screenshots or expected output so it can check its own work. It also recommends plan mode before complex changes. [S4]

## Practice (synthesis, not sourced)

| Phase | Default pattern | Gate (deterministic) |
|---|---|---|
| Intake | Routing: classify the issue, then pick a model and effort level | Issue has acceptance criteria |
| Plan | Single agent in plan mode | Human approves the plan for non-trivial changes |
| Implement | Orchestrator-workers only if the work splits into independent pieces | Manifest drift check passes ([07](07-agentic-manifest-and-hashing.md)) |
| Verify | Evaluator-optimizer, with tests as the evaluator ([08](08-self-healing-agents.md)) | Tests + lint green |
| Review | A separate agent context or a human | No unresolved blocking findings |
| Ship | Pipeline, not agent ([06](06-deterministic-delivery-pipelines.md)) | Pinned inputs and recorded provenance |

Rules of thumb:
1. **Start with a workflow and promote it to an agent only when the path really can't be predicted.** [S1] makes the same recommendation in favour of simplicity.
2. **Agents propose, pipelines dispose.** Anything that ships goes through a deterministic gate that an agent can't skip.
3. **Every loop gets a budget** ([03](03-token-conscious-loops.md)) and every swarm gets a controller ([04](04-agentic-swarm-controls.md)).
4. **Measure spend per phase** ([02](02-token-spend-analytics.md)). Unmeasured agent work tends to spread to fill whatever budget is available.
