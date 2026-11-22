# Overview: what you are building and how to know it works

## Agent = model + harness
A **model** is a text predictor: it reads text and proposes the next thing to do. An **agent** is that model plus a **harness**: ordinary program code that decides what the model is allowed to do, runs the tools, keeps the memory, enforces limits and records a trace. The model proposes; the harness decides. A harness has seven parts: loop, tools, context, memory, gates, verify and trace. You build them one by one.

Whenever you are unsure which side something belongs to, ask: *could a model be talked out of it?* A prompt can be ignored, so a rule that must hold goes in code.

## Three layers (keep them apart)
| Layer | What it is | Files |
|---|---|---|
| **Harness** | the generic engine: loop, tool contract, limits, gate, verify, trace, recovery. Knows nothing about to-do lists | `harness.py` (you build it) |
| **Project** | the Desk Assistant app: tasks, add / list / delete, the duplicate rule, the saved file | `tools.py`, `store.py`, `agent.py` (you build them) |
| **Model adapter** | one call to a real model: history in, decision out | `llm.py`, `config.py` (provided) |

## Before you build: Phase 0 (provided, nothing to write)
- **0a** `python3 ask.py`: a plain prompt. The model says "Done!" and nothing was saved.
- **0b** `python3 naive_agent.py`: a loop with tools but no harness. Watch what it deletes. (If your real model is not fooled, run `python3 naive_agent.py --gullible`: the same loop with a labelled stand-in that is fooled every time.)

**What you will see.** Every demo prints a console log while it runs: `INFO` lines with what the model was asked, its raw reply, and what was sent to and returned from each tool, plus the approval question and answer once there is a gate; `WARN` and `ERROR` mark anything worth a look. So you can tell what happened from the log alone. `try_it.py` and `agent.py` accept `--quiet` to show only the end-of-run trace.

## The phase map
| Phase | You build | Harness part | Check |
|---|---|---|---|
| 1 | `tools.py`, `harness.py`: the loop, tools, trace | Loop, Tools, Trace | `python3 check.py 1` |
| 2 | the gate, `describe`, data-not-orders, result cut, history window | Gates, Context | `python3 check.py 2` |
| 3a | repeat check, denial cap, step cap | Loop exits | `python3 check.py 3a` |
| 3b | verify and the hand-over note | Verify, Recovery | `python3 check.py 3b` |
| 4 | `store.py` and the checkpoint hook | Memory | `python3 check.py 4` |
| 5 *(optional, the part to cut if behind)* | `graph.py`: the same harness in LangGraph | all seven, by LangGraph's names | `python3 check.py 5` |
| 6 | `agent.py`, then live scenarios and the design review | all seven | `python3 check.py 6` |

Passing `python3 check.py N` is the grade for phase N.

## Live model runs vary, on purpose
Your harness is graded by **tests that use fake models**, so the result is the same every time. Live runs on a real model (`agent.py`, `run_scenarios.py`) are for *watching*: a real model varies from run to run. "The model was not fooled this time" is a valid result: the gate is still there for the day it is. If you see an error with **429**, your free quota for that model is used up: wait 60 seconds, or set `GEMINI_MODEL` in `.env` to another model.

## Where to look
`README.md` (start here), `SETUP.md`, `AGENTS.md`, `drills.md` (see the parts a normal run hides), `01-product-spec.md`, `02-technical-spec.md` (the contract), `phase-1.md` to `phase-6.md`, `edge-cases.md`, `harness-map.md`, `predict-sheet.md`, `sample-runs/` (recorded real runs).

Build from these docs first. The `solution/` folder is a finished reference: open its matching file only after two failed tries on a phase, or after the phase is green.
