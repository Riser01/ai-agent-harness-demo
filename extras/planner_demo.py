"""OPTIONAL stretch: a planner model proposes steps, and EVERY step still passes through the same harness gate.

"Split it into a planner and an executor" is a popular design, and it is easy to assume it makes an agent safer
on its own. The lesson here is what it does NOT change: the plan is only a proposal. Each step runs through
harness.run with the same tools, the same gate and the same limits, so a bad plan cannot delete anything the gate
would not allow one step at a time.

What to look at
    plan_with_model()  asks the real model for a short list of steps. Planning is a model call, with no side effects.
    MAX_PLAN_STEPS     a plan is cut to this many steps, so the planner gets no unlimited ambition either.
    execute()          runs every step through the same harness and stops at the first one that does not finish
                       cleanly.

Run:  python3 extras/planner_demo.py "Add 'File taxes' and delete the dentist task"      (a real model plans; you approve)
      python3 extras/planner_demo.py --scripted                                           (deterministic, no key needed)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "..", "tests")]

from fakes import scripted
from harness import run
from tools import ALL_TOOLS, State, Task

MAX_PLAN_STEPS = 5     # a plan is cut to this many steps: the planner gets no unlimited ambition either


def load_seed(path):
    """Read the seed file directly so this extra needs only tools.py."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return State(tasks=[Task(t["id"], t["text"]) for t in data["tasks"]], next_id=data["next_id"])


def plan_with_model(goal: str, tasks_text: str) -> list[str]:
    """Ask the real model for a short list of plain-words steps (one JSON array). Planning is a model call: no side effects."""
    import llm
    system = ("You break a goal into at most 5 short steps for a to-do assistant. Reply with ONE JSON object: "
              '{"final": "[\\"step 1\\", \\"step 2\\"]"} where the value is a JSON array of strings. No other text.')
    text = llm._chat(system, f"Goal: {goal}\nCurrent tasks:\n{tasks_text}", json_mode=True)
    return [str(s) for s in json.loads(llm.parse_decision(text)["final"])][:MAX_PLAN_STEPS]


def execute(goal, plan, executor_for, state, approve):
    """Run each planned step through the SAME harness. Stop at the first step that does not finish cleanly."""
    for number, step in enumerate(plan, start=1):
        result = run(step, model=executor_for(step), tools=ALL_TOOLS, state=state, approve=approve, max_steps=4)
        print(f'step {number} "{step}" -> {result.status}')
        for line in result.trace:
            print(f"      {line.step} {line.kind:<6} {line.detail}")
        if result.status != "done":
            return f"stopped at step {number}: {result.status}"
    return "done"


def main(argv):
    """Plan, then execute every step under the gate; you answer the approval questions."""
    state = load_seed(os.path.join(HERE, "..", "data", "seeds", "week_start.json"))
    approve = lambda _n, _a, words: input(f"APPROVAL NEEDED: {words}  Allow? [y/N] ").strip().lower().startswith("y")
    if "--scripted" in argv:
        plan = ["add 'File taxes'", "delete the dentist task", "list tasks"]
        steps = {"add": [{"tool": "add_task", "args": {"text": "File taxes"}}, {"final": "added"}],
                 "delete": [{"tool": "delete_task", "args": {"id": 4}}, {"final": "deleted"}],
                 "list": [{"tool": "list_tasks", "args": {}}, {"final": "listed"}]}
        executor_for = lambda step: scripted(steps[step.split()[0]])
    else:
        import config
        import llm
        config.load_env()
        goal = " ".join(argv) or "Add 'File taxes' and delete the dentist task"
        plan = plan_with_model(goal, "\n".join(f"{t.id}: {t.text}" for t in state.tasks))
        model = llm.make_model(ALL_TOOLS)
        executor_for = lambda step: model
    print("PLAN:", plan)
    print("RESULT:", execute(" ".join(argv), plan, executor_for, state, approve))
    print("tasks left:", [f"{t.id}: {t.text}" for t in state.tasks])


if __name__ == "__main__":
    main(sys.argv[1:])
