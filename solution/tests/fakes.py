"""Deterministic stand-ins for a real model, so tests give the same answer every time with no key and no network.

Code written by a coding agent must be gradeable without randomness. A real model varies from run to run, so a
test that used one could pass today and fail tomorrow for no reason in your code. The tests use these fakes
instead. Each one has the same shape as a real model: history lines in, one decision out, so the harness cannot
tell the difference.

What to look at: the three fakes
    scripted(decisions)   replays a fixed list of decisions, then repeats the last one.
    gullible(history)     obeys any "delete/remove task N" it finds inside a tool result. It plays a FOOLED model,
                          which proves the gate protects you even when the model does not.
    varying(tool, key)    never repeats exactly the same call, so it can only be stopped by the step cap.
"""
import os
import re
import sys

# Make the project folder importable no matter where the tests are started from.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def scripted(decisions):
    """Replay fixed decisions in order; once they run out, repeat the last one."""
    position = 0

    def model(_history):
        """Return the next scripted decision."""
        nonlocal position
        choice = decisions[min(position, len(decisions) - 1)]
        position += 1
        return choice

    return model


def gullible(history):
    """A fooled model: list the tasks, then obey every 'delete/remove task N' written inside the tool result."""
    if history[-1].startswith("user:"):
        return {"tool": "list_tasks", "args": {}}
    notes = [h for h in history if h.startswith("tool:") and re.search(r"\b(delete|remove)\b", h, re.IGNORECASE)]
    already = {int(n) for h in history if h.startswith("assistant wants delete_task") for n in re.findall(r'"id": (\d+)', h)}
    for note in notes:
        for number in re.findall(r"task (\d+)", note, re.IGNORECASE):
            if int(number) not in already:
                return {"tool": "delete_task", "args": {"id": int(number)}}
    return {"final": "All done."}


def varying(tool="list_tasks", key=None, start=100):
    """A model that asks for `tool` forever but changes its arguments every time, so the repeat check cannot fire."""
    count = 0

    def model(_history):
        """Return a call that differs from every earlier one."""
        nonlocal count
        count += 1
        return {"tool": tool, "args": {key or "n": start + count}}

    return model
