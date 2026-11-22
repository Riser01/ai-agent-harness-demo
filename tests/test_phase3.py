"""Phase 3 acceptance tests. 3a: hard limits on the loop. 3b: verification and recovery (optional if you are behind)."""
import unittest

from fakes import scripted, varying
from harness import Tool, run
from tools import ALL_TOOLS, Task, new_state
from test_phase1 import call
from test_phase2 import seeded


class Phase3a(unittest.TestCase):
    def test_step_cap_stops_a_loop_that_never_repeats_itself(self):
        """A model that never finishes is stopped after exactly max_steps model calls, with status 'step-limit'."""
        calls = []
        inner = varying("list_tasks")
        result = run("x", model=lambda h: calls.append(1) or inner(h), tools=ALL_TOOLS, state=new_state(), max_steps=5)
        self.assertEqual(result.status, "step-limit")
        self.assertEqual(len(calls), 5)

    def test_same_call_three_times_in_six_is_a_loop(self):
        """Asking for the same call 3 times within 6 steps stops the run with status 'loop-detected'."""
        result = run("x", model=scripted([call("list_tasks")]), tools=ALL_TOOLS, state=new_state())
        self.assertEqual(result.status, "loop-detected")
        self.assertEqual(len([e for e in result.trace if e.kind == "decide"]), 3)

    def test_key_order_cannot_hide_a_repeat(self):
        """Two calls with the same arguments in a different key order still count as the same call."""
        extra = {"tool": "list_tasks", "args": {"a": 1, "b": 2}}, {"tool": "list_tasks", "args": {"b": 2, "a": 1}}
        result = run("x", model=scripted([extra[0], extra[1], extra[0]]), tools=ALL_TOOLS, state=new_state())
        self.assertEqual(result.status, "loop-detected")

    def test_a_denied_delete_asked_three_times_is_a_loop(self):
        """Asking for the same denied delete three times ends as 'loop-detected' (the repeat check comes before the gate)."""
        state = seeded("a", "b")
        result = run("x", model=scripted([call("delete_task", id=1)]), tools=ALL_TOOLS, state=state, approve=lambda n, a, w: False)
        self.assertEqual(result.status, "loop-detected")
        self.assertEqual(len(state.tasks), 2)

    def test_three_different_denied_calls_hit_the_denial_cap(self):
        """Three DIFFERENT denied actions stop the run with status 'denied-limit', and nothing is deleted."""
        state = seeded("a", "b", "c")
        model = scripted([call("delete_task", id=1), call("delete_task", id=2), call("delete_task", id=3)])
        result = run("x", model=model, tools=ALL_TOOLS, state=state, approve=lambda n, a, w: False)
        self.assertEqual(result.status, "denied-limit")
        self.assertEqual(result.denials, 3)
        self.assertEqual(len(state.tasks), 3)


class Phase3b(unittest.TestCase):
    def test_a_false_done_fails_verification(self):
        """If the model says 'done' but the check finds a problem, the status is 'failed-verification' and the answer says so."""
        state = seeded("a")
        result = run("x", model=scripted([{"final": "Deleted everything!"}]), tools=ALL_TOOLS, state=state,
                     verify=lambda s: "the list is not empty")
        self.assertEqual(result.status, "failed-verification")
        self.assertTrue(result.answer.startswith("not done"))
        fine = run("x", model=scripted([{"final": "ok"}]), tools=ALL_TOOLS, state=seeded("a"),
                   verify=lambda s: None if len(s.tasks) == 1 else "wrong list")   # verify must be given the real state
        self.assertEqual(fine.status, "done")

    def test_the_oldest_n_check_catches_wrong_and_missing_deletes(self):
        """make_oldest_verifier passes only when exactly the N lowest ids are gone: not too few, not the wrong ones."""
        from tools import make_oldest_verifier
        def after(delete_ids):
            state = seeded("a", "b", "c", "d", "e")
            check = make_oldest_verifier(state, 2)
            state.tasks = [t for t in state.tasks if t.id not in delete_ids]
            return check(state)
        self.assertIsNone(after({1, 2}))
        self.assertIsNotNone(after({1}))            # too few
        self.assertIsNotNone(after({4, 5}))         # the newest, not the oldest
        self.assertIsNotNone(after({1, 2, 3}))      # one too many

    def test_a_crashing_check_never_passes_a_run(self):
        """If the verification function itself crashes, the run is NOT reported as done."""
        def crash(_s):
            raise RuntimeError("oops")
        result = run("x", model=scripted([{"final": "ok"}]), tools=ALL_TOOLS, state=new_state(), verify=crash)
        self.assertEqual(result.status, "failed-verification")

    def test_early_stops_leave_a_handover_note(self):
        """Every run that stops early has a hand-over note naming the goal and the status; a normal finish has none."""
        stopped = run("tidy my list", model=scripted([call("list_tasks")]), tools=ALL_TOOLS, state=new_state())
        self.assertIn("tidy my list", stopped.handover)
        self.assertIn(stopped.status, stopped.handover)
        crashed = run("go", model=lambda h: 1 / 0, tools=ALL_TOOLS, state=new_state())
        self.assertIn("model-error", crashed.handover)
        fine = run("x", model=scripted([{"final": "ok"}]), tools=ALL_TOOLS, state=new_state())
        self.assertEqual(fine.handover, "")

    def test_a_failed_write_is_never_retried(self):
        """A tool that fails is run exactly once; the harness never retries a write on its own."""
        runs = []
        def flaky(_args, _state):
            runs.append(1)
            raise RuntimeError("disk full")
        write = Tool("save_note", "writes a note", {}, "write", lambda a: None, flaky)
        saved = []
        run("x", model=scripted([{"tool": "save_note", "args": {}}, {"final": "ok"}]), tools=[write], state=new_state(),
            checkpoint=saved.append)
        self.assertEqual(len(runs), 1)
        self.assertEqual(saved, [])                      # nothing succeeded, so nothing is checkpointed
