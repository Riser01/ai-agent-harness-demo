"""The scoreboard: runs the acceptance tests for each phase and explains every result in plain words.

WHY THIS FILE EXISTS
    Raw test output is unreadable if you are not a programmer. This prints one line per phase, and for each failing test
    the requirement in plain words BEFORE any technical detail. A file you have not built yet says "not built yet", never
    a crash. This file is provided: do not edit it, and do not edit the tests.

Usage:  python3 check.py          every phase     python3 check.py 2     one phase (1, 2, 3, 3a, 3b, 4, 5, 6)
        python3 check.py style    the comment standard (every file explains itself, every function has a docstring)
"""
import ast
import importlib
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tests")]

BUILT_BY_YOU = {"harness": "harness.py", "tools": "tools.py", "store": "store.py", "agent": "agent.py", "graph": "graph.py"}
PHASES = [  # key, title, test module, test class
    ("1", "Loop, tools, trace", "test_phase1", "Phase1"),
    ("2", "Gate and context", "test_phase2", "Phase2"),
    ("3a", "Limits", "test_phase3", "Phase3a"),
    ("3b", "Verify and recovery", "test_phase3", "Phase3b"),
    ("4", "Memory", "test_phase4", "Phase4"),
    ("5", "LangGraph version (optional)", "test_phase5", "Phase5"),
    ("6", "The agent", "test_phase6", "Phase6"),
]


def short(text: str) -> str:
    """The line of a traceback that says what went wrong (the last 'SomethingError: ...' line), trimmed."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    errors = [l for l in lines if re.match(r"^[\w.]*(Error|Exception)\b", l)]
    return (errors[-1] if errors else lines[-1] if lines else "")[:260]


def missing_module(text: str):
    """If a traceback is 'No module named X', return X, else None."""
    match = re.search(r"No module named '([\w.]+)'", text)
    return match.group(1).split(".")[0] if match else None


def run_phase(label, title, module_name, class_name):
    """Run one phase's tests and print its line. Returns True when it is fully green."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as err:
        return report_missing(label, title, (err.name or "").split(".")[0])
    except ImportError as err:
        print(f"Phase {label}  {title}: not complete yet ({err})")
        return False
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, class_name))
    problems, total, absent = [], 0, set()
    for test in suite:
        total += 1
        result = unittest.TestResult()
        test.run(result)
        for _case, trace in result.failures + result.errors:
            name = missing_module(trace)
            if name:
                absent.add(name)
            problems.append((test, trace))
    if absent and len(problems) == total:
        return report_missing(label, title, sorted(absent)[0])
    if not problems:
        print(f"Phase {label}  {title}: all {total} green")
        return True
    print(f"Phase {label}  {title}: {total - len(problems)} of {total} green")
    for test, trace in problems:
        print(f"    Phase {label}, requirement: {(test.shortDescription() or test.id()).strip()}")
        print(f"        what happened: {short(trace)}")
    return False


def report_missing(label, title, name):
    """Print the plain 'not built yet' line for a missing file or package."""
    if name in BUILT_BY_YOU:
        print(f"Phase {label}  {title}: not built yet ({BUILT_BY_YOU[name]} does not exist)")
    elif name == "langgraph":
        print(f"Phase {label}  {title}: LangGraph is not installed. Run:  pip install -r requirements.txt")
    else:
        print(f"Phase {label}  {title}: cannot run yet (a Python package called '{name}' is missing)")
    return False


def run_provided():
    """Run the tests on the provided files (config, llm, ask, naive agent, seeds). They should always be green."""
    module = importlib.import_module("test_provided")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.Provided)
    bad = []
    for test in suite:
        result = unittest.TestResult()
        test.run(result)
        bad += [(test, t) for _c, t in result.failures + result.errors]
    if not bad:
        print(f"Setup   provided files: all {suite.countTestCases()} green")
        return True
    print(f"Setup   provided files: {suite.countTestCases() - len(bad)} of {suite.countTestCases()} green (do not edit these files)")
    for test, trace in bad:
        print(f"    requirement: {(test.shortDescription() or test.id()).strip()}\n        what happened: {short(trace)}")
    return False


def run_style():
    """The comment standard: every file you built opens with a docstring, and every function and class has a docstring."""
    ok, seen = True, 0
    for name, filename in BUILT_BY_YOU.items():
        path = os.path.join(ROOT, filename)
        if not os.path.exists(path):
            continue
        seen += 1
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        missing = [] if ast.get_docstring(tree) else ["the file itself (add a top docstring: why it exists, what it prevents)"]
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
                missing.append(f"{node.name} (line {node.lineno})")
        if missing:
            ok = False
            print(f"Style   {filename}: missing a docstring on: {', '.join(missing)}")
    if ok:
        print(f"Style   comment standard: ok ({seen} file{'s' if seen != 1 else ''} checked)")
    return ok


def main(argv):
    """Run what was asked for. Exit code 0 only when everything asked for is green."""
    want = argv[0].lower() if argv else "all"
    if want == "3":
        keys = ["3a", "3b"]
    elif want in ("all", "style") or want in {p[0] for p in PHASES}:
        keys = [p[0] for p in PHASES] if want == "all" else [] if want == "style" else [want]
    else:
        print("Usage: python3 check.py [1|2|3|3a|3b|4|5|6|style]")
        return 2
    results = []
    if want == "all":
        results.append(run_provided())
    for key, title, module, cls in PHASES:
        if key in keys:
            results.append(run_phase(key, title, module, cls))
    if want in ("all", "style"):
        results.append(run_style())
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
