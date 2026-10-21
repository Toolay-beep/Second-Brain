import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agentkit import budget, compress, heal, manifest, spend


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("print('a')\n")
        (self.root / "README.md").write_text("hi\n")
        (self.root / "src" / "__pycache__").mkdir()
        (self.root / "src" / "__pycache__" / "a.pyc").write_bytes(b"x")

    def tearDown(self):
        self.tmp.cleanup()

    def test_deterministic_and_ignores(self):
        m1, m2 = manifest.dumps(manifest.build(self.root)), manifest.dumps(manifest.build(self.root))
        self.assertEqual(m1, m2)
        files = json.loads(m1)["files"]
        self.assertEqual(sorted(files), ["README.md", "src/a.py"])
        self.assertIn("src", json.loads(m1)["dirs"])

    def test_verify_detects_drift(self):
        (self.root / manifest.MANIFEST_NAME).write_text(manifest.dumps(manifest.build(self.root)))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(manifest.main(["verify", str(self.root)]), 0)
        (self.root / "src" / "a.py").write_text("print('b')\n")
        (self.root / "new.txt").write_text("n\n")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(manifest.main(["verify", str(self.root)]), 1)
        self.assertIn("MODIFIED  src/a.py", out.getvalue())
        self.assertIn("ADDED     new.txt", out.getvalue())

    def test_manifestignore(self):
        (self.root / ".manifestignore").write_text("# c\n*.md\n")
        self.assertNotIn("README.md", manifest.build(self.root)["files"])


class SpendTests(unittest.TestCase):
    RECORDS = [
        {"agent": "a", "model": "m", "usage": {"input_tokens": 100, "output_tokens": 50,
                                                "cache_creation_input_tokens": 1000,
                                                "cache_read_input_tokens": 0,
                                                "cache_creation": {"ephemeral_5m_input_tokens": 1000,
                                                                   "ephemeral_1h_input_tokens": 0}}},
        {"agent": "a", "model": "m", "usage": {"input_tokens": 100, "output_tokens": 50,
                                                "cache_creation_input_tokens": 0,
                                                "cache_read_input_tokens": 1000}},
        {"agent": "b", "model": "x", "usage": {"input_tokens": 10, "output_tokens": 5}},
    ]

    def test_totals_and_cache_ratio(self):
        g = spend.aggregate(self.RECORDS, "agent")
        self.assertEqual(g["a"].total_input, 2200)
        self.assertAlmostEqual(g["a"].cache_hit_ratio, 1000 / 2200)
        self.assertEqual(g["b"].requests, 1)

    def test_cost_uses_multipliers(self):
        prices = {"m": {"input_per_mtok": 1_000_000, "output_per_mtok": 2_000_000}}  # $1/$2 per token
        g = spend.aggregate(self.RECORDS, "agent", prices)
        # 200 input*1 + 1000 write*1.25 + 1000 read*0.1 + 100 output*2
        self.assertAlmostEqual(g["a"].cost_usd, 200 + 1250 + 100 + 200)
        self.assertIsNone(g["b"].cost_usd)
        self.assertEqual(g["b"].unpriced_models, {"x"})

    def test_per_model_read_multiplier_override(self):
        prices = {"m": {"input_per_mtok": 1_000_000, "output_per_mtok": 0, "multipliers": {"cache_read": 0.05}}}
        c = spend.record_cost("m", {"cache_read_input_tokens": 1000}, prices)
        self.assertAlmostEqual(c, 50)


class BudgetTests(unittest.TestCase):
    def test_budget_exceeded(self):
        b = budget.Budget(max_tokens=100)
        b.charge_usage({"input_tokens": 60, "output_tokens": 30})
        self.assertEqual(b.remaining, 10)
        with self.assertRaises(budget.BudgetExceeded):
            b.charge(11)

    def test_loop_guard_repeat(self):
        g = budget.LoopGuard(max_iterations=10)
        with self.assertRaises(budget.NoProgress):
            for _ in g:
                g.observe(state={"failing": ["test_x"]})
        self.assertEqual(g.i, 1)

    def test_loop_guard_patience(self):
        g = budget.LoopGuard(max_iterations=10, patience=2, min_gain=0.01)
        scores = iter([0.5, 0.7, 0.705, 0.706, 0.9])
        with self.assertRaises(budget.NoProgress):
            for i in g:
                g.observe(state=i, score=next(scores))
        self.assertEqual(g.best, 0.7)

    def test_loop_guard_max_iterations(self):
        self.assertEqual(len(list(budget.LoopGuard(max_iterations=3))), 3)

    def test_swarm_limits(self):
        s = budget.SwarmController(budget.Budget(1000), max_concurrency=2, max_depth=1, max_agents=2)
        with self.assertRaises(budget.SwarmHalted):
            with s.agent(depth=2):
                pass
        with s.agent(0):
            pass
        with s.agent(1):
            pass
        with self.assertRaises(budget.SwarmHalted):
            with s.agent(1):
                pass

    def test_swarm_budget_halts_everyone(self):
        s = budget.SwarmController(budget.Budget(100), max_concurrency=4)
        with self.assertRaises(budget.BudgetExceeded):
            with s.agent(0):
                s.budget.charge(101)
        self.assertTrue(s.halted)
        with self.assertRaises(budget.SwarmHalted):
            s.check()

    def test_swarm_concurrency_cap(self):
        s = budget.SwarmController(budget.Budget(10**6), max_concurrency=2, max_agents=10)
        active, peak, lock = [0], [0], threading.Lock()
        gate = threading.Barrier(2, timeout=2)

        def work():
            with s.agent(0):
                with lock:
                    active[0] += 1
                    peak[0] = max(peak[0], active[0])
                try:
                    gate.wait()
                except threading.BrokenBarrierError:
                    pass
                with lock:
                    active[0] -= 1

        ts = [threading.Thread(target=work) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertLessEqual(peak[0], 2)


class CompressTests(unittest.TestCase):
    def msgs(self):
        return [
            {"role": "user", "content": "fix bug"},
            {"role": "tool", "content": "A" * 10000},
            {"role": "assistant", "content": "ok"},
            {"role": "tool", "content": "same"},
            {"role": "tool", "content": "same"},
            {"role": "tool", "content": "latest"},
        ]

    def test_truncate_middle(self):
        t = compress.truncate_middle("x" * 1000, 200)
        self.assertLessEqual(len(t), 200 + 10)
        self.assertIn("elided", t)
        self.assertEqual(compress.truncate_middle("short", 200), "short")

    def test_compress_deterministic_and_smaller(self):
        a, b = compress.compress(self.msgs(), 500, 2), compress.compress(self.msgs(), 500, 2)
        self.assertEqual(a, b)
        self.assertLess(compress.history_tokens(a), compress.history_tokens(self.msgs()))
        self.assertTrue(a[1]["content"].startswith("[tool result cleared"))
        self.assertEqual(a[5]["content"], "latest")
        self.assertIn("identical to tool result #3", a[4]["content"])

    def test_pinned_kept_and_target_respected(self):
        m = self.msgs()
        m[1]["pinned"] = True
        self.assertIn("AAAA", compress.clear_old_tool_results(m, 1)[1]["content"])
        small = [{"role": "tool", "content": "x"}] * 5
        self.assertEqual(compress.compress(small, target_tokens=10_000, keep_last_tools=1)[0]["content"], "x")


class HealTests(unittest.TestCase):
    def test_heals_after_feedback(self):
        def attempt(memory):
            return len(memory)  # "gets better" with each lesson

        r = heal.self_heal(attempt, lambda v: (v >= 2, {"value": v}), max_attempts=5)
        self.assertTrue(r.ok)
        self.assertEqual(r.attempts, 3)
        self.assertEqual(len(r.memory), 2)

    def test_stops_on_repeated_failure(self):
        r = heal.self_heal(lambda m: 0, lambda v: (False, {"err": "same"}), max_attempts=10)
        self.assertFalse(r.ok)
        self.assertEqual(r.attempts, 2)
        self.assertIn("no progress", r.stop_reason)

    def test_stops_at_max_attempts(self):
        r = heal.self_heal(lambda m: len(m), lambda v: (False, {"v": v}), max_attempts=3)
        self.assertEqual((r.ok, r.attempts, r.stop_reason), (False, 3, "max attempts"))

    def test_circuit_breaker(self):
        now = [0.0]
        cb = heal.CircuitBreaker(failure_threshold=2, reset_after=10, clock=lambda: now[0])

        def boom():
            raise ValueError

        for _ in range(2):
            with self.assertRaises(ValueError):
                cb.call(boom)
        self.assertEqual(cb.state, "open")
        with self.assertRaises(heal.CircuitOpen):
            cb.call(lambda: 1)
        now[0] = 11
        self.assertEqual(cb.state, "half-open")
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")


if __name__ == "__main__":
    unittest.main()
