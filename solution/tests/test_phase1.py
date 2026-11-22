"""Phase 1 acceptance tests: the loop, the tools, the trace. Every test says its requirement in one plain line."""
import json
import unittest

from fakes import scripted
from harness import Tool, run
from tools import ALL_TOOLS, Task, new_state


def call(name, **args):
    """A scripted decision that asks for a tool."""
    return {"tool": name, "args": args}


def recorder(decisions):
    """A scripted model that also remembers every history it was shown."""
    seen, inner = [], scripted(decisions)

    def model(history):
        seen.append(list(history))
        return inner(history)
    return model, seen


class Phase1(unittest.TestCase):
    def test_add_then_list_then_final(self):
        """The agent can add a task, list it, and finish: status is 'done' and the task is really in the state."""
        state = new_state()
        result = run("add", model=scripted([call("add_task", text="File taxes"), call("list_tasks"), {"final": "Added it."}]),
                     tools=ALL_TOOLS, state=state)
        self.assertEqual(result.status, "done")
        self.assertEqual(result.answer, "Added it.")
        self.assertEqual([t.text for t in state.tasks], ["File taxes"])

    def test_history_lines_follow_the_contract(self):
        """The model sees 'user: <goal>' first, then 'assistant wants <tool> <JSON>' and 'tool: <result>' lines."""
        model, seen = recorder([call("add_task", text="Pay rent"), {"final": "ok"}])
        run("please add rent", model=model, tools=ALL_TOOLS, state=new_state())
        second = seen[1]
        self.assertEqual(second[0], "user: please add rent")
        self.assertTrue(second[1].startswith("assistant wants add_task "))
        self.assertEqual(json.loads(second[1].split(" ", 3)[3]), {"text": "Pay rent"})
        self.assertEqual(second[2], "tool: added task 1")

    def test_list_shows_ids(self):
        """list_tasks shows every task with its numeric id, so the model can refer to it later."""
        state = new_state()
        state.tasks += [Task(1, "buy milk"), Task(2, "call bank")]
        state.next_id = 3
        model, seen = recorder([call("list_tasks"), {"final": "ok"}])
        run("show", model=model, tools=ALL_TOOLS, state=state)
        self.assertIn("1: buy milk", seen[1][-1])
        self.assertIn("2: call bank", seen[1][-1])

    def test_duplicate_is_refused_as_an_error_line(self):
        """Adding the same task twice (ignoring case and extra spaces) is refused with an 'error: duplicate of task' line."""
        state = new_state()
        model, seen = recorder([call("add_task", text="Pay rent"), call("add_task", text="  pay   RENT "), {"final": "ok"}])
        run("add twice", model=model, tools=ALL_TOOLS, state=state)
        self.assertTrue(seen[2][-1].startswith("error: duplicate of task"))
        self.assertEqual(len(state.tasks), 1)

    def test_unknown_tool_comes_back_as_an_error_line(self):
        """A tool that does not exist does not crash the run: the model gets an 'error:' line and can recover."""
        model, seen = recorder([call("format_disk"), {"final": "ok"}])
        result = run("x", model=model, tools=ALL_TOOLS, state=new_state())
        self.assertTrue(seen[1][-1].startswith("error:"))
        self.assertEqual(result.status, "done")

    def test_bad_input_is_refused_and_changes_nothing(self):
        """Missing, empty or wrongly typed arguments are refused with an 'error:' line and nothing is added."""
        state = new_state()
        model, seen = recorder([call("add_task"), call("add_task", text=""), call("add_task", text=42), {"final": "ok"}])
        run("x", model=model, tools=ALL_TOOLS, state=state)
        self.assertEqual(state.tasks, [])
        self.assertTrue(all(h[-1].startswith("error:") for h in seen[1:4]))

    def test_a_tool_that_crashes_is_data_not_a_crash(self):
        """If a tool raises an exception, the run carries on and the model sees an 'error:' line."""
        def boom(_args, _state):
            raise RuntimeError("disk on fire")
        broken = Tool("explode", "always fails", {}, "read", lambda a: None, boom)
        model, seen = recorder([call("explode"), {"final": "ok"}])
        result = run("x", model=model, tools=[broken], state=new_state())
        self.assertEqual(result.status, "done")
        self.assertTrue(seen[1][-1].startswith("error:"))

    def test_final_wins_and_missing_args_mean_none(self):
        """If a reply has both a tool and a final, final wins; a missing or non-dict 'args' means no arguments."""
        both = run("x", model=scripted([{"tool": "list_tasks", "args": {}, "final": "stop here"}]), tools=ALL_TOOLS, state=new_state())
        self.assertEqual((both.status, both.answer), ("done", "stop here"))
        for decision in ({"tool": "list_tasks"}, {"tool": "list_tasks", "args": "nonsense"}):
            result = run("x", model=scripted([decision, {"final": "ok"}]), tools=ALL_TOOLS, state=new_state())
            self.assertEqual(result.status, "done")

    def test_a_failing_model_is_a_status_not_a_crash(self):
        """If the model call raises, or returns nonsense, the run ends with status 'model-error' instead of crashing."""
        def broken(_history):
            raise RuntimeError("network down")
        self.assertEqual(run("x", model=broken, tools=ALL_TOOLS, state=new_state()).status, "model-error")
        self.assertEqual(run("x", model=lambda h: "not a dict", tools=ALL_TOOLS, state=new_state()).status, "model-error")
