# 05 · Context compression

## What the sources establish

- **Context rot.** As the context window grows, "the model's ability to accurately recall information from that context decreases". [S3]
- **Position matters.** Accuracy is U-shaped: best when relevant information sits at the start or end of the context, and worse in the middle, even for long-context models. [S11]
- **Techniques** [S3]:
  - *Tool-result clearing*: "one of the safest lightest touch forms of compaction".
  - *Compaction*: summarise a conversation that is nearing the limit and start a new context with the summary.
  - *Structured note-taking*: persist notes outside the context window and pull them back in when needed.
  - *Sub-agents*: do focused work in a clean context and return a condensed summary.
- **Claude Code specifics** [S4]: auto-compaction near the limit; `/compact <instructions>` to steer what is kept; a "Compact instructions" section in CLAUDE.md; hooks that pre-filter output (for example, grep a 10,000-line log down to the matching lines). Compaction is itself a large request. `/clear` costs nothing.
- **Learned compression.** LLMLingua uses a small LM to drop tokens. It reports up to 20× compression with a 1.5-point drop on its benchmarks. [S10]

## Ladder: cheapest and safest first (*Practice*, ordered after [S3])

1. **Don't load it.** Use pointers (paths, the manifest, [07](07-agentic-manifest-and-hashing.md)) instead of contents.
2. **Filter at the source.** Hooks or `grep` before output reaches the model.
3. **Truncate the middle** of oversized tool outputs and keep the head and tail. Errors usually sit at the end.
4. **Collapse duplicates.** The same tool output twice becomes a reference.
5. **Clear old tool results.** Keep the last K results and replace the rest with a stub plus a hash, so the tool can be re-run.
6. **Summarise (compaction)** only when the steps above aren't enough. It is lossy and costs tokens.
7. **Offload** to notes or sub-agents for long-horizon work.

Put the task statement and the latest evidence at the **start or end** of the prompt, not the middle. [S11]

## Tool: `agentkit.compress`

Deterministic steps 3–5: the same input always gives the same output, so results stay cacheable and hashable. Token counts there are a chars/4 **heuristic**. Use a real tokenizer or a token-counting endpoint when precision matters.
