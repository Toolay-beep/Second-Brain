# 04 · Agentic swarm controls

## What the sources establish

- Multi-agent systems use about 15× the tokens of chat. [S2] Claude Code agent teams use about 7× the tokens of a standard session when teammates run in plan mode. [S4]
- Claude Code's cost advice for teams: use cheaper models for teammates, keep teams small, keep spawn prompts focused, and shut teammates down when their work is done. [S4]
- In the orchestrator-workers pattern, a central LLM breaks down the task and hands pieces to workers. [S1] In sub-agent architectures, each sub-agent returns "only a condensed summary" to a lead agent. [S3]
- Failure taxonomy (MAST): 14 failure modes in 3 categories: specification issues, inter-agent misalignment and task verification. Seven open-source multi-agent frameworks failed 41%–86.7% of the time. The authors trace many failures to system design, not just model limits. [S14]

## Control surface (*Practice*)

| Control | Purpose | `agentkit.budget.SwarmController` |
|---|---|---|
| Shared budget | One ceiling for the whole swarm, not one per agent | `budget=Budget(...)` |
| Max concurrency | Rate-limit and cost smoothing | `max_concurrency` |
| Max depth | Stop sub-agents from spawning sub-agents without limit | `max_depth` |
| Max agents | Hard cap on fan-out | `max_agents` |
| Kill switch | One breach halts everyone | `halt()` / `check()` |
| Contract per worker | Objective, output format, tool scope, stop condition | spawn prompt (see [S2]) |
| Independent verifier | Covers MAST's "task verification" category [S14] | separate agent or test suite |

Heuristics:
- Spawn only for **independent** subtasks. Shared mutable state is where inter-agent misalignment shows up. [S14]
- Size the fan-out to the task, following the [S2] scaling rules.
- Workers return **summaries plus artifact paths**, never full transcripts. [S3]

```python
swarm = SwarmController(Budget(max_tokens=1_000_000), max_concurrency=4, max_depth=1, max_agents=8)
def worker(task):
    with swarm.agent(depth=1):
        for step in plan(task):
            swarm.check()                      # honour kill switch
            swarm.budget.charge_usage(run(step).usage)
```
