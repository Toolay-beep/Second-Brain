# 07 · Codebase agentic manifest & hashing

> "Agentic manifest" isn't a standard. Two real things sit next to it: the **AGENTS.md** convention for instructions [S13], and **content hashing** as practised in reproducible builds and provenance [S7][S12]. This note combines the two.

## Two artifacts

| Artifact | Audience | Content |
|---|---|---|
| `AGENTS.md` (instructions) | Agents | Build and test commands, conventions, boundaries, where things live. Nested files apply to subtrees, and the nearest file takes effect. [S13] |
| `agent-manifest.json` (state) | Agents + pipeline | Every file → SHA-256 and size, per-directory digests, one root digest |

## Why hash (*Practice*)

- **Cheap orientation.** An agent reads the file list instead of exploring with `ls` and `cat`, which saves tokens ([05](05-context-compression.md)).
- **Drift detection.** If the root digest changed, something changed. The per-directory digests show where, without re-reading everything.
- **Cache keys.** Summaries and embeddings keyed by file digest are reused until the file changes.
- **Pinned inputs.** The pipeline records the root digest as the input state ([06](06-deterministic-delivery-pipelines.md)).
- **Tamper evidence for agent edits.** Diff the manifests from before and after an agent run to list every touched file.

## Tool: `agentkit.manifest`

```bash
python -m agentkit.manifest build .     # writes agent-manifest.json
python -m agentkit.manifest verify .    # exit 1 + ADDED/REMOVED/MODIFIED list on drift
```

Determinism rules: POSIX paths, sorted entries, sorted JSON keys, no timestamps. Exclusions come from `.manifestignore` (fnmatch patterns; a trailing `/` matches a directory).

The digest scheme hashes the sorted `"<sha256>  <path>\n"` lines under each directory (the same line format as `sha256sum`). That gives a hierarchical digest but **not** a full Merkle tree with inclusion proofs.
