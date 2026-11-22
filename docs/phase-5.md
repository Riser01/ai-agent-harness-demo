# Phase 5 (optional): the same harness, built with LangGraph  (about 25 minutes)

Needs one install: `pip install -r requirements.txt` (LangGraph 1.2.23). `python3 check.py 5` says so in plain words if it is missing.

## The story
You built a harness by hand to see the parts. A framework gives them names. LangGraph models an agent as a **graph** of steps (nodes) joined by edges, with state that is saved as it goes. Nothing new happens: it is the same seven parts.

| Your harness | LangGraph |
|---|---|
| the loop | a graph **cycle**: `act` goes back to `decide` |
| a decision and its exits | **conditional edges** that pick the next node |
| tools | the `act` node |
| the gate (ask a human) | `interrupt()` in the `gate` node: the graph **pauses**, saves, and resumes with the answer |
| memory | a **checkpointer** keyed by `thread_id` (and `store.py` JSON if you want it to survive a restart) |
| step cap | a `steps` counter in the state, plus `recursion_limit` as a backstop |
| trace | `stream()` |

**The rule everyone trips on:** on resume, the `gate` node reruns **from the top**, not from the `interrupt()` line. Never put a side effect (a write, an alert, an email) before `interrupt()`, or it happens twice.

## What you build
`graph.py`, with `run_graph(...)`, reusing your `tools.py`. Four nodes: `decide`, `gate`, `act`, `check`. It returns the same `RunResult`. Differences you will meet: an **unknown tool is gated** here (the harness refuses it outright), and this engine has no repeat check or history window. One file, about 150 lines; do not add features.

**Harness parts:** all seven, by LangGraph's names. Contract: `02-technical-spec.md` section 11.

## Ask your agent exactly this
> Read `AGENTS.md` and `docs/02-technical-spec.md` (section 11). Run `pip install -r requirements.txt` first. Create `graph.py` with `run_graph` using LangGraph: a `StateGraph` with an append-only `history` and a `steps` counter, nodes `decide`, `gate`, `act`, `check`, conditional edges, `interrupt()` in `gate`, an `InMemorySaver` checkpointer, `recursion_limit` only as a backstop, and `stream()` to build the trace. Reuse `tools.py` and `harness.py`'s `RunResult`, `TraceEntry` and `handover_note`. Make `python3 check.py 5` pass and do not stop until it passes. Never edit anything in `tests/`.

(LangGraph is not standard library; this is the only phase where installing a package is allowed.)

## Acceptance
`python3 check.py 5`: all 10 green.

## Try it live
Goal: **"Delete the dentist task."**, with the human saying no, then yes.
```
python3 try_it.py "Delete the dentist task." --engine langgraph --approve no --seed data/seeds/week_start.json
```
**What to expect:** a trace line `gate ? paused at the gate, state saved: delete task 4: "Book dentist appointment"`. That is `interrupt()` at work: the run is saved, waiting, and resumes with your answer. See `sample-runs/10-langgraph-S3a-approve-no.txt` and `...-yes.txt`.

## In the wild
LangGraph is used for production agents with human-in-the-loop steps. The interrupt-and-resume pattern is how "approve this action" buttons work in agent products.
