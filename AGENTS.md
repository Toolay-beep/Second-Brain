# AGENTS.md

Instructions for coding agents working in this repo.

## Layout
- `notes/`: knowledge notes. Every factual claim cites `[S#]` from `SOURCES.md`. Unsourced guidance is labelled **Practice**.
- `agentkit/`: Python standard library only. No third-party dependencies.
- `tests/`: `unittest`.
- `agent-manifest.json`: SHA-256 of every file. Read this instead of listing directories.

## Commands
- Test: `python3 -m unittest discover -s tests -t .`
- After changing any file: `python3 -m agentkit.manifest build .`, then commit the manifest.
- Full gate: `./scripts/pipeline.sh`. It must pass before you push.

## Rules
- Never add a factual claim to `notes/` without a source in `SOURCES.md`. If you can't verify a claim, leave it out or label it unverified.
- Never weaken or skip a test to make a check pass.
- Keep outputs deterministic: no timestamps, no absolute paths, sorted keys.
