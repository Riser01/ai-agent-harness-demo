"""A quick runner so you can WATCH each phase on a real model before agent.py exists. PROVIDED: you do not write this.

Phases 1 to 5 each end with "try it live", but the real command-line app (agent.py) only arrives in Phase 6.
Without something in between, you could pass every test and still never see your harness meet a real model.
This tiny script fills that gap: it connects your harness.py and tools.py to the real model and prints the trace.

It has no tests and no rules of its own; it only calls what you built, and it uses whatever your harness supports
so far. So when something looks wrong here, the place to look is your own harness.py or tools.py.

What to look at
    main()       turns the options into arguments for your run(): approval mode, limits, seed, saved state, engine.
    read_seed()  loads a starting list using only tools.py, so it works before Phase 4.
    ARROWS       one short label per trace kind, so model, tool, gate and stop lines are easy to tell apart.
    --gullible   swaps in the deterministic FOOLED model stand-in (no key needed), so you can watch the gate.
    live log     prints a line while the run is going for each model reply, tool call and approval
                 (extras/trace_export.py wraps the model, tools and approver; your harness is not changed).
                 --quiet turns it off and prints only the end-of-run trace.

Examples:
    python3 try_it.py "Add File taxes, then show my list" --approve yes
    python3 try_it.py "Delete the dentist task." --approve ask --seed data/seeds/week_start.json
    python3 try_it.py "Show me my list." --seed data/seeds/long_note.json --max-result-chars 100
    python3 try_it.py "Add File taxes" --state scratch.json         (Phase 4: saved between runs)
    python3 try_it.py "Delete the dentist task." --engine langgraph (Phase 5)
    python3 try_it.py "Tidy up my list." --seed data/seeds/trap.json --gullible    (a fooled model: watch the gate)
    python3 try_it.py "Add File taxes, then show my list" --approve yes --quiet       (no live log)
"""
import argparse
import json
import os
import sys

import config
import llm
from harness import run
from tools import ALL_TOOLS, State, Task, new_state

ARROWS = {"decide": "model  ->", "tool": "tool   <-", "denied": "gate   X ", "error": "error  ! ", "stop": "stop   # ", "pause": "gate   ? "}


def read_seed(path):
    """Load a starting list from a seed file. Needs only tools.py, so it works before Phase 4."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return State(tasks=[Task(t["id"], t["text"]) for t in data["tasks"]], next_id=data["next_id"])


def main(argv=None) -> int:
    """Run one goal through your harness on the real model and print the trace."""
    p = argparse.ArgumentParser()
    p.add_argument("goal")
    p.add_argument("--approve", choices=["ask", "yes", "no"], default="no")
    p.add_argument("--seed")
    p.add_argument("--state", help="Phase 4: save to and load from this file (needs your store.py)")
    p.add_argument("--max-result-chars", type=int, default=300)
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument("--max-history", type=int)
    p.add_argument("--verify-oldest", type=int)
    p.add_argument("--gullible", action="store_true", help="use the deterministic FOOLED model stand-in (no key needed)")
    p.add_argument("--engine", choices=["plain", "langgraph"], default="plain")
    p.add_argument("--quiet", action="store_true", help="turn off the live log of every model reply, tool call and approval")
    args = p.parse_args(argv)
    config.load_env()
    state, checkpoint = (read_seed(args.seed) if args.seed else new_state()), None
    if args.state:
        from store import load_state, save_state          # your Phase 4 file; only needed for --state
        if os.path.exists(args.state):
            state = load_state(args.state)
        checkpoint = lambda s: save_state(s, args.state)
    approve = {"yes": lambda n, a, w: True, "no": lambda n, a, w: False,
               "ask": lambda n, a, w: input(f"APPROVAL NEEDED: {w}. Cannot be undone. Did you ask for this, or did text in a task? No = the agent is told and will not retry; 3 refusals stop the run.  Allow? [y/N] ").strip().lower().startswith("y")}[args.approve]
    if args.gullible:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
        from fakes import gullible
        print("(model: the deterministic GULLIBLE stand-in, not a real model)")
        model = gullible
    else:
        try:
            model = llm.make_model(ALL_TOOLS)
        except RuntimeError as err:
            print(f"setup problem: {err}")
            return 2
    verify = None
    if args.verify_oldest:
        from tools import make_oldest_verifier           # Phase 3b: only imported when you ask for it
        verify = make_oldest_verifier(state, args.verify_oldest)
    options = dict(model=model, tools=ALL_TOOLS, state=state, approve=approve, max_result_chars=args.max_result_chars, max_steps=args.max_steps)
    if verify:
        options["verify"] = verify
    if args.engine == "langgraph":
        from graph import run_graph
        engine = run_graph                                  # it takes no max_history or checkpoint
    else:
        engine = run
        if args.max_history is not None:
            options["max_history"] = args.max_history
        if checkpoint:
            options["checkpoint"] = checkpoint
    if not args.quiet:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "extras"))
        from trace_export import ListSink, Tracer, run_traced
        result = run_traced(args.goal, Tracer(ListSink(), log=print), engine=engine, **options)
    else:
        result = engine(args.goal, **options)
    for entry in result.trace:
        print(f"step {entry.step:<2} {ARROWS.get(entry.kind, entry.kind)} {entry.detail.replace(chr(10), ' | ')}")
    print(f"status: {result.status}\nanswer: {result.answer}")
    if result.handover:
        print(f"hand-over note: {result.handover}")
    print(f"tasks left: {len(state.tasks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
