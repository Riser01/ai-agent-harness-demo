"""Phase 3b exercise: "Delete the 12 oldest of 20 tasks" with three scripted agents, A, B and C. No key needed.

The question behind this file: can you trust an agent that says "done"? Three agents get the same goal and all
three claim success. Agent A does it properly. Agent B deletes the wrong tasks (the 12 newest). Agent C deletes
nothing and says "done" anyway. Read only their final words and you cannot tell them apart; only the harness's
verify() step, which looks at the REAL list, can. "Oldest" means lowest id.

What to look at
    AGENTS     the three scripted agents and what each one really does.
    deletes()  builds a script that deletes the given ids and then claims success.
    the main block at the bottom
               runs each agent on a fresh copy of the list and prints what it claimed next to the status the
               harness gives it.

Run:  python3 extras/oldest12_exercise.py          (needs Phase 3b: tools.make_oldest_verifier and verify in harness.run)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "..", "tests")]

from fakes import scripted
from harness import run
from tools import ALL_TOOLS, State, Task, make_oldest_verifier

GOAL = "Delete the 12 oldest of my 20 tasks."
SEED = os.path.join(HERE, "..", "data", "seeds", "twenty.json")


def load_seed(path):
    """Read the seed file directly, so this exercise needs only Phase 3b (not the Phase 4 store)."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return State(tasks=[Task(t["id"], t["text"]) for t in data["tasks"]], next_id=data["next_id"])


def deletes(ids):
    """A script that deletes each id in turn and then claims success."""
    return scripted([{"tool": "delete_task", "args": {"id": i}} for i in ids] + [{"final": "Done: I deleted the 12 oldest tasks."}])


AGENTS = {
    "A (does it properly: ids 1-12)": deletes(range(1, 13)),
    "B (deletes the 12 newest: ids 9-20)": deletes(range(9, 21)),
    "C (deletes nothing, says done)": scripted([{"final": "Done: I deleted the 12 oldest tasks."}]),
}

if __name__ == "__main__":
    for name, model in AGENTS.items():
        state = load_seed(SEED)
        verify = make_oldest_verifier(state, 12)
        result = run(GOAL, model=model, tools=ALL_TOOLS, state=state, approve=lambda n, a, w: True, max_steps=15, verify=verify)
        claim = next((e.detail for e in result.trace if e.detail.startswith("final:")), "")
        print(f"Agent {name}: tasks left={len(state.tasks)}")
        print(f"    agent claimed: {claim[len('final: '):]}")
        print(f"    harness says:  {result.status}")
