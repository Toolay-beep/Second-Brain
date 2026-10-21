"""Token spend analytics over Claude API `usage` records.

Input: JSON Lines, one record per API response, e.g.
    {"agent": "planner", "model": "m", "tag": "issue-42",
     "usage": {"input_tokens": 120, "output_tokens": 800,
               "cache_creation_input_tokens": 0, "cache_read_input_tokens": 9000,
               "cache_creation": {"ephemeral_5m_input_tokens": 0,
                                  "ephemeral_1h_input_tokens": 0}}}

Field names and the identity
    total_input = cache_read_input_tokens + cache_creation_input_tokens + input_tokens
follow Anthropic's prompt-caching docs (see SOURCES.md, [S5]).

Dollar costs are computed ONLY from a prices file you supply, because prices
change and differ per model and per contract. Cache multipliers default to the
documented 1.25x (5m write), 2x (1h write) and 0.1x (read) of base input price;
some models use a different read multiplier, so override it per model.

CLI:
    python -m agentkit.spend usage.jsonl [--group-by agent|model|tag] [--prices prices.json] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field

DEFAULT_MULTIPLIERS = {"cache_write_5m": 1.25, "cache_write_1h": 2.0, "cache_read": 0.1}


@dataclass
class Totals:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    cost_usd: float | None = None
    unpriced_models: set = field(default_factory=set)

    @property
    def total_input(self) -> int:
        return self.input_tokens + self.cache_read_input_tokens + self.cache_creation_input_tokens

    @property
    def cache_hit_ratio(self) -> float:
        return self.cache_read_input_tokens / self.total_input if self.total_input else 0.0

    @property
    def output_input_ratio(self) -> float:
        return self.output_tokens / self.total_input if self.total_input else 0.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["unpriced_models"] = sorted(self.unpriced_models)
        d["total_input"] = self.total_input
        d["cache_hit_ratio"] = round(self.cache_hit_ratio, 4)
        d["output_input_ratio"] = round(self.output_input_ratio, 4)
        return d


def record_cost(model: str, u: dict, prices: dict) -> float | None:
    p = prices.get(model)
    if p is None:
        return None
    base_in = p["input_per_mtok"] / 1e6
    out = p["output_per_mtok"] / 1e6
    m = {**DEFAULT_MULTIPLIERS, **p.get("multipliers", {})}
    cc = u.get("cache_creation") or {}
    w5 = cc.get("ephemeral_5m_input_tokens")
    w1 = cc.get("ephemeral_1h_input_tokens")
    if w5 is None and w1 is None:  # no breakdown: treat all writes as 5-minute
        w5, w1 = u.get("cache_creation_input_tokens", 0), 0
    return (
        u.get("input_tokens", 0) * base_in
        + (w5 or 0) * base_in * m["cache_write_5m"]
        + (w1 or 0) * base_in * m["cache_write_1h"]
        + u.get("cache_read_input_tokens", 0) * base_in * m["cache_read"]
        + u.get("output_tokens", 0) * out
    )


def aggregate(records, group_by: str | None = None, prices: dict | None = None) -> dict[str, Totals]:
    groups: dict[str, Totals] = defaultdict(Totals)
    for r in records:
        key = str(r.get(group_by, "<none>")) if group_by else "all"
        t = groups[key]
        u = r.get("usage", {})
        t.requests += 1
        t.input_tokens += u.get("input_tokens", 0)
        t.output_tokens += u.get("output_tokens", 0)
        t.cache_read_input_tokens += u.get("cache_read_input_tokens", 0)
        t.cache_creation_input_tokens += u.get("cache_creation_input_tokens", 0)
        cc = u.get("cache_creation") or {}
        t.cache_write_5m += cc.get("ephemeral_5m_input_tokens", 0)
        t.cache_write_1h += cc.get("ephemeral_1h_input_tokens", 0)
        if prices is not None:
            c = record_cost(r.get("model", ""), u, prices)
            if c is None:
                t.unpriced_models.add(r.get("model", ""))
            else:
                t.cost_usd = (t.cost_usd or 0.0) + c
    return dict(sorted(groups.items()))


def read_jsonl(path: str):
    fh = sys.stdin if path == "-" else open(path, encoding="utf-8")
    with fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{n}: invalid JSON: {e}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agentkit.spend", description="Aggregate token usage records.")
    ap.add_argument("path", help="JSONL file of usage records, or '-' for stdin")
    ap.add_argument("--group-by", default=None, help="record key to group by, e.g. agent, model, tag")
    ap.add_argument("--prices", default=None, help="JSON: {model: {input_per_mtok, output_per_mtok, multipliers?}}")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args(argv)

    prices = None
    if args.prices:
        with open(args.prices, encoding="utf-8") as fh:
            prices = json.load(fh)
    groups = aggregate(read_jsonl(args.path), args.group_by, prices)

    if args.json:
        print(json.dumps({k: v.as_dict() for k, v in groups.items()}, indent=2, sort_keys=True))
        return 0
    hdr = f"{'group':<20}{'reqs':>6}{'total_in':>12}{'output':>10}{'cache_hit':>10}{'cost_usd':>11}"
    print(hdr)
    print("-" * len(hdr))
    for k, t in groups.items():
        cost = "n/a" if t.cost_usd is None else f"{t.cost_usd:.4f}"
        print(f"{k[:19]:<20}{t.requests:>6}{t.total_input:>12}{t.output_tokens:>10}{t.cache_hit_ratio:>10.1%}{cost:>11}")
        if t.unpriced_models:
            print(f"  ! no price for: {', '.join(sorted(t.unpriced_models))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
