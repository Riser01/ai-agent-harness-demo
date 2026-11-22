"""Phase 0b: a bare agent loop with tools but NO harness. PROVIDED: you do not write this file.

WHY THIS FILE EXISTS
    The plain call (ask.py) cannot act. This is the next step up: a loop that lets a model call tools. It is the loop
    most tutorials stop at. Look at what it does NOT have: no step cap, no repeat check, no approval gate, no result cut,
    no verification, no saved progress. Whatever the model asks for, it does.

WHAT IT PREVENTS (ONLY BECAUSE OF ONE SAFETY CATCH)
    It refuses to run more than 15 steps so a demo cannot run away. A real naive agent has no such catch.

Run it:  python3 naive_agent.py                       the planted-note list, a real model
         python3 naive_agent.py --gullible            the same, with the deterministic gullible stand-in (labelled)
         python3 naive_agent.py "your goal" --seed data/seeds/week_start.json
It is self-contained on purpose: it works before you have built anything.
"""
import argparse
import json
import re
import sys
from types import SimpleNamespace

DEMO_GOAL = "Tidy up my to-do list and tell me what is left."
DEMO_SEED = "data/seeds/trap.json"
SAFETY_CATCH = 15      # the only limit in this file, and it exists for the demo, not for the agent

# Just enough of a tool menu for llm.build_system_prompt (name, params, description). There is no risk tier here.
MENU = [
    SimpleNamespace(name="add_task", params={"text": "string"}, description="Add a new task to the to-do list."),
    SimpleNamespace(name="list_tasks", params={}, description="List all tasks with their numeric ids."),
    SimpleNamespace(name="delete_task", params={"id": "integer"}, description="Permanently delete a task by its numeric id."),
]


def do_tool(name, args, tasks):
    """Run a tool straight away. No validation, no approval: this is the point of the demo."""
    if name == "list_tasks":
        return "\n".join(f"{t['id']}: {t['text']}" for t in tasks) or "no tasks"
    if name == "add_task":
        tasks.append({"id": max([t["id"] for t in tasks], default=0) + 1, "text": args.get("text", "")})
        return "added"
    if name == "delete_task":
        tasks[:] = [t for t in tasks if t["id"] != args.get("id")]
        return f"deleted task {args.get('id')}"
    return f"unknown tool {name}"


def naive_run(goal, model, tasks, out=print):
    """Loop until the model says it is done. Returns the tasks left. Stops at SAFETY_CATCH steps and says so."""
    history = [f"user: {goal}"]
    for step in range(1, SAFETY_CATCH + 1):
        decision = model(history)
        if "final" in decision:
            out(f"step {step}: model says: {decision['final']}")
            return tasks
        name, args = decision["tool"], decision.get("args") or {}
        result = do_tool(name, args, tasks)            # <- no gate: whatever it asks for, it gets
        out(f"step {step}: model asked {name} {json.dumps(args)} -> {result.splitlines()[0] if result else ''}")
        history += [f"assistant wants {name} {json.dumps(args)}", f"tool: {result}"]
    out(f"SAFETY CATCH: stopped after {SAFETY_CATCH} steps. A real naive agent would keep going.")
    return tasks


def main(argv=None):
    """Load a seed, run the naive loop, and show what was destroyed."""
    parser = argparse.ArgumentParser(description="A bare agent loop: tools, no harness.")
    parser.add_argument("goal", nargs="?", default=DEMO_GOAL)
    parser.add_argument("--seed", default=DEMO_SEED)
    parser.add_argument("--gullible", action="store_true", help="use the deterministic fooled-model stand-in, not a real model")
    args = parser.parse_args(argv)
    with open(args.seed, encoding="utf-8") as handle:
        tasks = json.load(handle)["tasks"]
    print("tasks before:", [t["id"] for t in tasks])
    if args.gullible:
        sys.path.insert(0, "tests")
        from fakes import gullible
        print("(model: the deterministic GULLIBLE stand-in, not a real model)")
        model = gullible
    else:
        import config
        import llm
        config.load_env()
        try:
            model = llm.make_model(MENU, naive=True)
        except RuntimeError as err:
            print(f"configuration error: {err}")
            return 2
    try:
        tasks = naive_run(args.goal, model, tasks)
    except RuntimeError as err:
        print(f"model error: {err}")
        return 1
    print("tasks after: ", [f"{t['id']}: {t['text'][:30]}" for t in tasks])
    return 0


if __name__ == "__main__":
    sys.exit(main())
