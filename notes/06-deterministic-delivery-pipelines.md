# 06 · Deterministic delivery pipelines

LLM output is not guaranteed to be reproducible. The pipeline that turns agent output into a shipped artifact should be.

## What the sources establish

- **Reproducible build:** "given the same source code, build environment and build instructions, any party can recreate bit-by-bit identical copies of all specified artifacts". [S7] (The wording is being debated on the project's mailing list; see the search notes in SOURCES.md.)
- **SLSA build track:** provenance exists (L1), signed provenance from a hosted build platform (L2), hardened build platform (L3). [S12]
- Agentic systems need sandboxed testing and guardrails. [S1] Claude Code hooks can **block** tool calls deterministically (`PreToolUse` exit code 2). [S6]

## Design (*Practice*)

```
agent (non-deterministic)  ──►  PR / patch  ──►  pipeline (deterministic)
                                                 1. manifest verify   (inputs pinned)
                                                 2. lint + tests      (fixed seeds, no network)
                                                 3. build             (lockfiles, pinned toolchain)
                                                 4. hash artifacts + record provenance
                                                 5. ship only if 1-4 pass
```

Checklist:
- [ ] Lockfiles committed. Toolchain and container images pinned by digest, not by tag.
- [ ] No timestamps, absolute paths or random ordering in outputs (`agentkit.manifest` follows this rule).
- [ ] Tests use fixed seeds and no live network or LLM calls. Record model outputs as fixtures.
- [ ] Gates are code (CI, hooks), not instructions an agent can ignore.
- [ ] Every run records input digest → output digest (provenance), as SLSA L1 describes.
- [ ] Rerun the same commit and confirm the digests match. If they don't, the pipeline isn't deterministic.

## In this repo

`scripts/pipeline.sh` runs: manifest verify → unit tests → manifest rebuild check (determinism). `make ci` calls it.
