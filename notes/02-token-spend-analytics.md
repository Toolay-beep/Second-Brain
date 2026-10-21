# 02 · Token spend analytics

## What the sources establish

- **Why it matters.** Agents use about 4× the tokens of chat, and multi-agent systems about 15×. [S2] On BrowseComp, token usage alone explained 80% of performance variance. [S2] So spend tracks quality as well as cost, and both are worth measuring.
- **The raw data.** Every API response carries `usage` with `input_tokens`, `output_tokens`, `cache_creation_input_tokens` and `cache_read_input_tokens`, plus a `cache_creation` breakdown (`ephemeral_5m_input_tokens`, `ephemeral_1h_input_tokens`). [S5]
- **Total input** = `cache_read_input_tokens + cache_creation_input_tokens + input_tokens`. [S5]
- **Cache pricing relative to base input:** 5-minute write 1.25×, 1-hour write 2×, read 0.1×, with per-model exceptions listed in the docs. [S5]
- **Claude Code baseline.** Enterprise averages are about $13 per developer per active day and $150–250 per developer per month. 90% of users stay under $30 per active day. [S4]
- **Tooling.** `/usage` shows session tokens and an estimated cost. OpenTelemetry export streams per-user token and cost metrics. On plan accounts, the usage breakdown attributes spend to skills, subagents, plugins and MCP servers. [S4]

## Metrics worth tracking

| Metric | Formula | Why |
|---|---|---|
| Total input | per [S5] | What you actually send each turn |
| Cache hit ratio | `cache_read / total_input` | Low → prompt prefix is unstable (see [S4] "cache misses") |
| Output/input ratio | `output / total_input` | High with no results → the agent is thrashing |
| Cost per merged PR / per resolved issue | spend grouped by `tag` | Unit economics (*Practice*) |
| Spend by agent role | spend grouped by `agent` | Shows which role in a swarm is the most expensive (*Practice*) |

## Tool: `agentkit.spend`

```bash
python -m agentkit.spend examples/usage.sample.jsonl --group-by agent
python -m agentkit.spend examples/usage.sample.jsonl --group-by agent --prices examples/prices.example.json
```

The prices file is required for dollar figures. `examples/prices.example.json` holds **placeholder** numbers, not real prices. Fill it in from your provider's current price list or your contract.
