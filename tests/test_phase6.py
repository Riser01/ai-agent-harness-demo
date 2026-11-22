"""Phase 6 acceptance tests: agent.py, the command-line app that wires everything together."""
import os
import tempfile
import unittest
from unittest.mock import patch

from fakes import scripted
from agent import main
from tools import ALL_TOOLS
from test_phase1 import call


class Phase6(unittest.TestCase):
    def setUp(self):
        """Each test gets its own folder, so no test touches your real tasks.json."""
        self.dir = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.dir.name, "tasks.json")
        self.seed = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "seeds", "week_start.json")

    def tearDown(self):
        """Remove the temporary folder."""
        self.dir.cleanup()

    def go(self, argv, model, answers=()):
        """Run agent.main with a fake model; returns (exit code, printed lines)."""
        lines, replies = [], iter(answers)
        code = main(argv + ["--state", self.state], model=model, input_fn=lambda _p: next(replies), out=lines.append)
        return code, "\n".join(lines)

    def test_add_and_list_saves_the_file_and_prints_the_summary(self):
        """A normal run exits 0, prints the status and 'tasks left', and saves the list to the state file."""
        code, text = self.go(["Add File taxes", "--approve", "no"], scripted([call("add_task", text="File taxes"), {"final": "Added."}]))
        self.assertEqual(code, 0)
        self.assertIn("status: done", text)
        self.assertIn("tasks left: 1", text)
        self.assertRegex(text, r"step\s+\d+\s+model\s+->")        # the print format the scenario runner reads
        self.assertTrue(os.path.exists(self.state))

    def test_approve_no_keeps_the_task_and_still_exits_0(self):
        """--approve no refuses the delete; the task stays, and 'done-with-denials' still counts as a finished run (exit 0)."""
        code, text = self.go(["Delete the dentist task", "--approve", "no", "--seed", self.seed], scripted([call("delete_task", id=4), {"final": "ok"}]))
        self.assertEqual(code, 0)
        self.assertIn("done-with-denials", text)
        self.assertIn("tasks left: 6", text)

    def test_approve_yes_and_approve_ask_delete(self):
        """--approve yes deletes at once; --approve ask prints the question, reads your answer and deletes on 'y'."""
        code, text = self.go(["delete", "--approve", "yes", "--seed", self.seed], scripted([call("delete_task", id=4), {"final": "ok"}]))
        self.assertIn("tasks left: 5", text)
        os.remove(self.state)
        code, text = self.go(["delete", "--approve", "ask", "--seed", self.seed], scripted([call("delete_task", id=4), {"final": "ok"}]), answers=["y"])
        self.assertIn("APPROVAL NEEDED", text)
        self.assertIn("Book dentist appointment", text)
        self.assertIn("tasks left: 5", text)

    def test_stopping_early_exits_1_and_prints_a_handover_note(self):
        """A run that stops early (here: step limit) exits 1 and prints the hand-over note."""
        from fakes import varying
        code, text = self.go(["loop forever", "--max-steps", "3"], varying("list_tasks"))
        self.assertEqual(code, 1)
        self.assertIn("hand-over note", text)

    def test_no_key_is_a_setup_problem_exit_2(self):
        """With no model configured, the app prints a plain message and exits 2, without showing a traceback."""
        with patch.dict(os.environ, {}, clear=True):
            lines = []
            code = main(["hello", "--state", self.state], out=lines.append)
        self.assertEqual(code, 2)
        self.assertIn("configuration error", "\n".join(lines))

    def test_the_seed_is_used_only_when_there_is_no_saved_file(self):
        """--seed starts a fresh list; once a state file exists, the saved list wins and the seed is ignored."""
        self.go(["add", "--seed", self.seed, "--approve", "no"], scripted([call("add_task", text="File taxes"), {"final": "ok"}]))
        code, text = self.go(["list", "--seed", self.seed], scripted([call("list_tasks"), {"final": "ok"}]))
        self.assertIn("tasks left: 7", text)         # 6 from the seed + the one added in run 1, not 6 again
        self.assertIn("File taxes", text)
