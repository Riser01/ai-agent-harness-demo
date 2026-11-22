"""Realistic goals on a REAL model, each judged by what actually happened (not by the model's words). PROVIDED.

The tests use fake models so they are exact. A real model varies from run to run, so judging a live run by its
exact words would fail at random. Instead, each scenario is judged by invariants about the real result: "the
dentist task still exists", "pay rent survived the planted note". This file runs data/scenarios.json through
agent.main and prints one PASS or FAIL line per scenario.

Passing check.py is the grade; this is for watching your finished agent cope with real goals.

What to look at
    evaluate()  judges one invariant against the saved list, the run status and the trace, never the model's claim.
    run_one()   runs one scenario's goals in order, as separate calls that share a temporary state file.

Usage:  python3 run_scenarios.py                 the default three (S1, S3a, S4)
        python3 run_scenarios.py --all           every scenario
        python3 run_scenarios.py --only S5 --repeat 3
Each scenario uses its own temporary state file, so your tasks.json is never touched. Uses model calls from your free quota.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def evaluate(check, status, tasks, ids_before, lines=()):
    """Judge one invariant against what really happened. `tasks` is a list of {id, text} read from the state file."""
    kind = check["type"]
    texts = [t["text"].lower() for t in tasks]
    ids = {t["id"] for t in tasks}
    if kind == "status_in":
        return status in check["values"]
    if kind == "task_exists":
        return any(check["text"].lower() in t for t in texts)
    if kind == "task_missing":
        return not any(check["text"].lower() in t for t in texts)
    if kind == "task_count":
        return len(tasks) == check["value"]
    if kind == "ids_gone":
        return all(i in ids_before and i not in ids for i in check["ids"])
    if kind == "max_task_length":
        return all(len(t["text"]) <= check["value"] for t in tasks)
    if kind == "trace_contains":
        return any(check["text"] in line for line in lines)
    if kind == "any_of":
        return any(evaluate(c, status, tasks, ids_before, lines) for c in check["checks"])
    if kind == "all_of":
        return all(evaluate(c, status, tasks, ids_before, lines) for c in check["checks"])
    raise ValueError(f"unknown check type {kind}")


def run_one(scenario, quiet=True):
    """Run one scenario's goals in order (separate calls, shared state file) and return (passed, status, model calls)."""
    import agent
    seed = os.path.join(ROOT, "data", "seeds", scenario["seed"] + ".json")
    with open(seed, encoding="utf-8") as handle:
        ids_before = [t["id"] for t in json.load(handle)["tasks"]]
    with tempfile.TemporaryDirectory() as folder:
        state_path = os.path.join(folder, "tasks.json")
        lines, status, code, model_calls = [], "", 0, 0
        for goal in scenario["goals"]:
            lines.clear()
            code = agent.main([goal, "--approve", scenario["approve"], "--state", state_path, "--seed", seed, *scenario["flags"]], out=lines.append)
            status = next((l.split(": ", 1)[1] for l in lines if l.startswith("status: ")), "no-status")
            model_calls += sum(1 for l in lines if re.match(r"step\s+\d+\s+model\s+->", l))
            if status == "no-status":              # setup problem (no key, bad file): never judge the untouched seed
                return False, status, model_calls, lines
        tasks = []
        if os.path.exists(state_path):
            with open(state_path, encoding="utf-8") as handle:
                tasks = json.load(handle)["tasks"]
        else:
            tasks = json.load(open(seed, encoding="utf-8"))["tasks"]
    passed = all(evaluate(c, status, tasks, ids_before, lines) for c in scenario["checks"])
    return passed, status, model_calls, lines


def main(argv=None) -> int:
    """Pick the scenarios, print the call budget first, run them, print one line each. Exit 0 only if all passed."""
    parser = argparse.ArgumentParser(description="Run realistic goals on a real model.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--only", help="one scenario id, for example S5")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--verbose", action="store_true", help="also print each run's output (the live log and the trace)")
    args = parser.parse_args(argv)
    import config
    config.load_env()
    os.environ.setdefault("LLM_MIN_SECONDS_BETWEEN_CALLS", "1")    # be gentle with a free quota
    with open(os.path.join(ROOT, "data", "scenarios.json"), encoding="utf-8") as handle:
        scenarios = json.load(handle)
    chosen = [s for s in scenarios if (s["id"] == args.only if args.only else args.all or s["default"])]
    if not chosen:
        print("No such scenario.")
        return 2
    runs = len(chosen) * args.repeat
    print(f"Budget: {runs} run(s), about 2 to 6 model calls each, so roughly {runs * 2} to {runs * 6} calls from your free quota.")
    failures = 0
    for scenario in chosen:
        for attempt in range(args.repeat):
            started = time.time()
            passed, status, calls, lines = run_one(scenario)
            failures += not passed
            tag = "PASS" if passed else "FAIL"
            print(f"{tag}  {scenario['id']:<4} {scenario['title']:<44} status={status:<19} model calls={calls}  {time.time() - started:.0f}s")
            if not passed:
                print(f"      expected: {scenario['passes_if']}")
            if args.verbose or not passed:
                print("\n".join("      " + l for l in lines))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
