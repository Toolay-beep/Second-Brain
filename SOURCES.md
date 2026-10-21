# Sources

All accessed **2026-10-21**. Notes cite these as `[S#]`.

**Verification** column:
- **direct**: the page was fetched and the quoted text was read on that page.
- **search**: the page couldn't be fetched from the build environment (DNS blocked), so the claim was checked against search-result excerpts of that page. Re-check against the original before quoting it formally.

| ID | Source | Date | Verification | Claims used |
|----|--------|------|--------------|-------------|
| S1 | Anthropic, *Building effective agents* — https://www.anthropic.com/engineering/building-effective-agents | 2024-12-19 | direct | Workflows vs agents; five workflow patterns; "finding the simplest solution possible, and only increasing complexity when needed"; orchestrator-workers ("a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes their results"); evaluator-optimizer ("one LLM call generates a response while another provides evaluation and feedback in a loop"); "stopping conditions (such as a maximum number of iterations)"; "extensive testing in sandboxed environments, along with the appropriate guardrails" |
| S2 | Anthropic, *How we built our multi-agent research system* — https://www.anthropic.com/engineering/multi-agent-research-system | 2025-06-13 | direct | Agents use ~4× and multi-agent systems ~15× the tokens of chat; token usage alone explains 80% of performance variance on BrowseComp (three factors explain 95%); effort-scaling rules (1 agent / 3–10 calls; 2–4 subagents / 10–15 calls; >10 subagents) |
| S3 | Anthropic, *Effective context engineering for AI agents* — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | 2025-09-29 | direct | Context rot; compaction; structured note-taking; sub-agent architectures; tool-result clearing as "one of the safest lightest touch forms of compaction" |
| S4 | Claude Code docs, *Manage costs effectively* — https://code.claude.com/docs/en/costs | living doc | direct | Average enterprise cost ~$13/dev/active day, $150–250/dev/month, <$30/active day for 90% of users; `/usage`, `/compact`, `/clear`; hooks to preprocess output; keep CLAUDE.md under 200 lines; subagents for verbose operations; agent teams ~7× tokens in plan mode; OpenTelemetry export |
| S5 | Claude API docs, *Prompt caching* — https://platform.claude.com/docs/en/build-with-claude/prompt-caching | living doc | direct | `usage` field names; `total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens`; multipliers: 5-min write 1.25×, 1-hour write 2×, read 0.1× base input (per-model exceptions listed on the page) |
| S6 | Claude Code docs, *Hooks reference* — https://code.claude.com/docs/en/hooks | living doc | direct | Hook events (`PreToolUse`, `PostToolUse`, `Stop`, `PreCompact`, `SubagentStop`, …); exit code 2 blocks a `PreToolUse` call and keeps Claude going on `Stop`; `stop_hook_active` loop guard; `{"decision": "block", "reason": …}` |
| S7 | Reproducible Builds, *Definitions* — https://reproducible-builds.org/docs/definition/ | — | search | "given the same source code, build environment and build instructions, any party can recreate bit-by-bit identical copies of all specified artifacts" |
| S8 | Shinn et al., *Reflexion: Language Agents with Verbal Reinforcement Learning*, arXiv:2303.11366 — https://arxiv.org/abs/2303.11366 | 2023 | search | Reinforcement "not by updating weights, but instead through linguistic feedback", with reflective text kept in an episodic memory buffer |
| S9 | Madaan et al., *Self-Refine: Iterative Refinement with Self-Feedback*, arXiv:2303.17651 — https://arxiv.org/abs/2303.17651 | 2023 | search | One LLM acts as generator, feedback provider and refiner; ~20% absolute average improvement across 7 tasks (GPT-3.5/GPT-4) |
| S10 | Jiang et al., *LLMLingua*, arXiv:2310.05736 (EMNLP 2023) — https://arxiv.org/abs/2310.05736 | 2023 | search | Prompt compression with a small LM; up to 20× compression with a 1.5-point performance drop on the reported benchmarks |
| S11 | Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*, arXiv:2307.03172 (TACL) — https://arxiv.org/abs/2307.03172 | 2023 | search | U-shaped accuracy: best when relevant information is at the start or end of the context, worse in the middle |
| S12 | SLSA, *Security levels* — https://slsa.dev/spec/v1.0/levels | v1.0+ | search | Build track: provenance exists (L1), signed provenance from a hosted build platform (L2), hardened build platform (L3) |
| S13 | AGENTS.md — https://agents.md/ (summarised by InfoQ, https://infoq.com/news/2025/08/agents-md/) | 2025-08 | search | "A README for agents"; Markdown at the repo root; nested files, with the nearest one in the directory tree taking effect |
| S14 | Cemri et al., *Why Do Multi-Agent LLM Systems Fail?*, arXiv:2503.13657 — https://arxiv.org/abs/2503.13657 | 2025 (v3 Oct 2025) | search | MAST taxonomy: 14 failure modes in 3 categories (specification issues, inter-agent misalignment, task verification); 41%–86.7% failure rates on 7 open-source MAS |

## Not sourced

Text marked **Practice** in the notes is the author's own engineering synthesis. It is not a claim from these sources: treat it as opinion and test it in your own setting.
