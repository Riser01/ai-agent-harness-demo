"""Phase 4 acceptance tests: memory. Saving and loading the task list, and the checkpoint hook."""
import json
import os
import tempfile
import unittest

from fakes import scripted
from harness import run
from tools import ALL_TOOLS, Task, new_state
from test_phase1 import call
from test_phase2 import seeded


class Phase4(unittest.TestCase):
    def setUp(self):
        """Each test gets its own empty folder."""
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "tasks.json")

    def tearDown(self):
        """Remove the temporary folder."""
        self.dir.cleanup()

    def test_save_then_load_returns_the_same_list(self):
        """Saving a task list and loading it back gives the same tasks and the same next id."""
        from store import load_state, save_state
        state = seeded("buy milk", "pay rent")
        save_state(state, self.path)
        again = load_state(self.path)
        self.assertEqual([(t.id, t.text) for t in again.tasks], [(1, "buy milk"), (2, "pay rent")])
        self.assertEqual(again.next_id, state.next_id)

    def test_a_missing_file_is_a_fresh_start(self):
        """Loading a file that does not exist gives an empty list instead of an error."""
        from store import load_state
        state = load_state(self.path)
        self.assertEqual((state.tasks, state.next_id), ([], 1))

    def test_a_damaged_file_is_an_error_not_a_quiet_reset(self):
        """A file that is not valid JSON, or has the wrong shape, raises ValueError instead of starting over."""
        from store import load_state
        for bad in ("{ not json", '{"tasks": "nope", "next_id": 1}', '{"next_id": 3}'):
            with open(self.path, "w", encoding="utf-8") as handle:
                handle.write(bad)
            with self.assertRaises(ValueError):
                load_state(self.path)

    def test_an_inconsistent_file_is_an_error(self):
        """A file whose next_id is not above every saved id (it would reuse an id) raises ValueError."""
        from store import load_state
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"next_id": 2, "tasks": [{"id": 1, "text": "a"}, {"id": 5, "text": "b"}]}, handle)
        with self.assertRaises(ValueError):
            load_state(self.path)

    def test_saving_is_atomic_and_survives_a_new_process(self):
        """Saving leaves no temporary file behind, and what a run saved is there for the next run to load."""
        from store import load_state, save_state
        state = new_state()
        run("add", model=scripted([call("add_task", text="File taxes"), {"final": "ok"}]), tools=ALL_TOOLS, state=state,
            checkpoint=lambda s: save_state(s, self.path))
        self.assertEqual(os.listdir(self.dir.name), ["tasks.json"])
        self.assertEqual([t.text for t in load_state(self.path).tasks], ["File taxes"])

    def test_checkpoint_runs_after_a_change_but_not_after_a_read(self):
        """The checkpoint hook is called after a tool that changes the list, and not after one that only reads."""
        saved = []
        state = seeded("a", "b")
        run("x", model=scripted([call("list_tasks"), call("add_task", text="c"), call("delete_task", id=1), {"final": "ok"}]),
            tools=ALL_TOOLS, state=state, approve=lambda n, a, w: True, checkpoint=lambda s: saved.append(len(s.tasks)))
        self.assertEqual(saved, [3, 2])        # after the add (3 tasks) and after the delete (2 tasks); the list saved nothing

    def test_a_failing_save_stops_the_run_loudly(self):
        """If saving fails, the run stops with status 'checkpoint-failed' instead of carrying on and losing work."""
        def broken(_state):
            raise OSError("disk full")
        result = run("x", model=scripted([call("add_task", text="a"), {"final": "ok"}]), tools=ALL_TOOLS, state=new_state(),
                     checkpoint=broken)
        self.assertEqual(result.status, "checkpoint-failed")
        self.assertIn("checkpoint-failed", result.handover)
