"""The Desk Assistant: the command-line app that wires every part together. This is Phase 6.

WHY THIS FILE EXISTS
    harness.py is the engine, tools.py is the to-do app, store.py is the saved file, llm.py is the model. Nothing runs
    until something connects them and reads your command line. That is this file, and it should stay thin: no rules of
    its own, only wiring.

WHAT IT PREVENTS
    * Rules hiding in the wrapper: every safety rule stays in the harness, where the tests protect it.
    * A confusing exit: 0 = the run finished (done, or done-with-denials), 1 = it stopped early, 2 = a setup problem.

Examples:
    python3 agent.py "Add 'File taxes', then show my list" --approve yes
    python3 agent.py "Delete the dentist task" --approve ask
    python3 agent.py "Tidy up my to-do list" --seed data/seeds/trap.json --approve no
"""
import argparse
import os
import sys

import config
from harness import run
from store import load_state, save_state
from tools import ALL_TOOLS, make_oldest_verifier, new_state

ARROWS = {"decide": "model  ->", "tool": "tool   <-", "denied": "gate   X ", "error": "error  ! ", "stop": "stop   # ", "pause": "gate   ? "}


def build_parser() -> argparse.ArgumentParser:
    """All command-line flags in one place."""
    p = argparse.ArgumentParser(description="Desk Assistant: a to-do agent with a harness around it.")
    p.add_argument("goal", help="what you want done, in plain words")
    p.add_argument("--approve", choices=["ask", "yes", "no"], default="ask", help="who answers approval questions (default: ask you)")
    p.add_argument("--state", default="tasks.json", help="where the task list is saved (default: tasks.json)")
    p.add_argument("--seed", help="a starting task list (a JSON file); used only when the state file does not exist yet")
    p.add_argument("--engine", choices=["plain", "langgraph"], default="plain")
    p.add_argument("--export", choices=["console", "langfuse"], help="also draw the run as a tree (extras/trace_export.py)")
    p.add_argument("--naive-prompt", action="store_true", help="drop the prompt's warning about tool results (injection drill)")
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument("--max-history", type=int, default=None, help="show the model only the last N history lines")
    p.add_argument("--max-result-chars", type=int, default=300)
    p.add_argument("--verify-oldest", type=int, metavar="N", help="after 'final', check that exactly the N oldest tasks are gone")
    return p


def make_approver(mode: str, input_fn, out):
    """Turn --approve into the harness's approve(name, args, words) callback."""
    def approve(_name, _args, words):
        """Answer one approval question."""
        if mode == "yes":
            return True
        if mode == "no":
            return False
        out(f"APPROVAL NEEDED: {words}. Cannot be undone. Did you ask for this, or did text in a task? No = the agent is told and will not retry; 3 refusals stop the run.")
        return input_fn("Allow this? [y/N] ").strip().lower().startswith("y")
    return approve


def main(argv=None, *, model=None, input_fn=input, out=print) -> int:
    """Run one goal. `model` and `input_fn` can be replaced in tests. Returns the exit code."""
    args = build_parser().parse_args(argv)

    # Memory: a saved file wins. The seed is only the first-ever starting point.
    try:
        if os.path.exists(args.state):
            state = load_state(args.state)
        elif args.seed:
            if not os.path.exists(args.seed):
                raise ValueError(f"seed file not found: {args.seed}")
            state = load_state(args.seed)
        else:
            state = new_state()
    except ValueError as err:
        out(f"configuration error: {err}")
        return 2

    if model is None:
        import llm
        try:
            model = llm.make_model(ALL_TOOLS, naive=args.naive_prompt)
        except RuntimeError as err:
            out(f"configuration error: {err}")
            return 2

    limits = dict(max_steps=args.max_steps, max_result_chars=args.max_result_chars)
    common = dict(model=model, tools=ALL_TOOLS, state=state, approve=make_approver(args.approve, input_fn, out),
                  verify=make_oldest_verifier(state, args.verify_oldest) if args.verify_oldest else None)
    if args.engine == "langgraph":
        if args.max_history is not None:
            out("note: --max-history is not used by the langgraph engine")
        from graph import run_graph
        if args.export:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "extras"))
            from trace_export import Tracer, choose_sink, run_traced
            result = run_traced(args.goal, Tracer(choose_sink(args.export)), engine=run_graph, **common, **limits)
        else:
            result = run_graph(args.goal, **common, **limits)
        save_state(state, args.state)               # this engine has no checkpoint hook, so save once at the end
    else:
        engine_args = dict(common, max_history=args.max_history, checkpoint=lambda s: save_state(s, args.state))
        if args.export:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "extras"))
            from trace_export import Tracer, choose_sink, run_traced
            result = run_traced(args.goal, Tracer(choose_sink(args.export)), **engine_args, **limits)
        else:
            result = run(args.goal, **engine_args, **limits)

    for entry in result.trace:
        out(f"step {entry.step:<2} {ARROWS[entry.kind]} {entry.detail.replace(chr(10), ' | ')}")
    out(f"status: {result.status}")
    out(f"answer: {result.answer}")
    if result.handover:
        out(f"hand-over note: {result.handover}")
    out(f"tasks left: {len(state.tasks)}")
    for task in state.tasks:
        out(f"  {task.id}: {task.text[:80]}")
    return 0 if result.status in ("done", "done-with-denials") else 1


if __name__ == "__main__":
    config.load_env()          # only the command line reads .env; main() itself reads the environment, so tests stay predictable
    sys.exit(main())
