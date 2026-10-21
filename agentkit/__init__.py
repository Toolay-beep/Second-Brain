"""agentkit: small, stdlib-only reference implementations for agentic SDLC practices.

Modules:
    manifest  - deterministic codebase manifest + content hashing + drift check
    spend     - token spend analytics over API `usage` records
    budget    - token/iteration budgets, no-progress loop guard, swarm controller
    compress  - deterministic context compression (tool-result clearing, truncation)
    heal      - verify-diagnose-retry loop and circuit breaker for self-healing agents
"""

__version__ = "0.1.0"
