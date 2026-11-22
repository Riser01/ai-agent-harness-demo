# AI Agent Harness Demo: build the harness around an AI agent

You will build the **harness** that makes an AI agent safe and dependable, one part at a time, using **any coding agent** (Cursor, Claude Code, Windsurf, Copilot, ChatGPT...). You do not need to type the code yourself. You read the spec, ask your agent well, and check the result with a test scoreboard. A finished reference lives in `solution/` for when you want to compare.

> **Agent = model + harness.** The model proposes what to do. The harness (ordinary code) decides what is actually allowed, enforces limits, keeps memory and records a trace.

The project is a small to-do agent, the "Desk Assistant": it can add, list and delete tasks, and deleting needs a human yes. Around it you build the seven parts of a harness (loop, tools, context, memory, gates, verify, trace), then rebuild the core with LangGraph.

## Start here
1. [`SETUP.md`](SETUP.md): Python, your free Gemini key, and the first check (10 minutes).
2. [`docs/00-overview.md`](docs/00-overview.md): the three layers and the phase map.
3. **Phase 0** (nothing to build): `python3 ask.py` and `python3 naive_agent.py` show why a bare model and an unguarded loop are not enough. No key yet? `python3 naive_agent.py --gullible` runs offline.
4. [`docs/phase-1.md`](docs/phase-1.md), then 2 to 6. Each phase gives you the exact thing to ask your coding agent, and a check.

## The phases
| Phase | You build | Harness part | Check |
|---|---|---|---|
| 1 | `tools.py`, `harness.py`: the loop, tools, trace | Loop, Tools, Trace | `python3 check.py 1` |
| 2 | the approval gate and context control | Gates, Context | `python3 check.py 2` |
| 3a | step cap, repeat check, denial cap | Loop exits | `python3 check.py 3a` |
| 3b | verification and the hand-over note | Verify, Recovery | `python3 check.py 3b` |
| 4 | `store.py`: the saved file and the checkpoint hook | Memory | `python3 check.py 4` |
| 5 *(optional)* | `graph.py`: the same harness in LangGraph | the core parts | `python3 check.py 5` |
| 6 | `agent.py`, live scenarios, the design review | all seven | `python3 check.py 6` |

## How to check your work
```
python3 check.py        every phase at once
python3 check.py 2      just Phase 2
python3 check.py style  the comment standard (every file explains itself)
```
Each line says in plain words what passed and what did not. For a failing test it prints `Phase N, requirement: ...` first. **Passing the check is the grade.** Tests use fake models so results are exact; live runs on a real model vary and are for watching. If a model is not fooled in a demo, that is a valid result: the gate is there for the day it is.

## The two-failures rule
1. Paste the failing line from `python3 check.py N` into your coding agent and say: **"fix only this"**.
2. After **two** failed tries, paste the phase's contract section from `docs/02-technical-spec.md`.
3. Still stuck? Open the matching file in `solution/` to compare. Do this after two tries or after your phase is green, not before: the learning is in the building.
4. Never edit anything in `tests/`.

## The reference solution
`solution/` is the finished, runnable project (`harness.py`, `tools.py`, `store.py`, `graph.py`, `agent.py`, plus copies of the provided files and tests). It is meant to be read: every file opens with why it exists and what it prevents.
```
cd solution
cp ../.env .env              # or make your own .env from ../.env.example
python3 check.py             # all green (Phase 5 needs: pip install -r requirements.txt)
python3 agent.py "Delete the dentist task." --approve ask --seed data/seeds/week_start.json --state scratch.json
python3 run_scenarios.py     # live scenarios on a real model
```
Fallen behind? `checkpoints/after-phase-2.zip` and `after-phase-4.zip` hold the learner-built files up to those phases. Unzip into the project root (this overwrites your own `harness.py` and `tools.py`, so copy them first) and run `python3 check.py`.

## Your key
Your free Gemini key goes only in a git-ignored `.env` (see `SETUP.md`), **never** in your coding agent's chat or in a shared file. No key appears anywhere in this repo.

## Optional: see a run in Langfuse
`python3 agent.py "..." --export langfuse` (needs `pip install langfuse` and three `LANGFUSE_*` lines in `.env`; works with `--engine langgraph` too; `extras/test_trace_export.py` runs after Phase 4) draws each run as a tree: the run, every model call (with model name, tokens and any retries), every tool, and every approval question. Failed runs and failed model calls are marked ERROR, refusals WARNING, and each run gets scores (`outcome`, `denials`, `steps`, `model_retries`). Without keys, `--export console` prints the same tree in the terminal. Prompts and task text leave your machine: use toy data only. See `docs/sample-runs/16-langfuse-enriched.txt`.

## An honest note on how far you need to get
Finishing **Phases 0 to 2** is a complete, successful outcome, especially if you do not code: you will have seen an agent with no rules do damage, built the loop, the tools, the approval gate and the context controls, and understood why those rules live in code. The non-coder route is `docs/predict-sheet.md` plus the recorded real runs in `docs/sample-runs/`. Want to see the parts a normal run never shows? `docs/drills.md`.

## What is in this repo
| Path | What it is |
|---|---|
| `docs/` | the specs, one document per phase, edge cases, the harness map, drills, the predict sheet, recorded real runs |
| `tests/`, `check.py` | the acceptance tests and the scoreboard. Do not edit |
| `config.py`, `llm.py`, `ask.py`, `naive_agent.py`, `try_it.py`, `run_scenarios.py` | provided: you do not write these |
| `data/` | starting task lists and the live scenarios |
| `extras/` | optional: planner demo, the 12-oldest exercise, Langfuse trace export and its tests |
| `solution/` | the finished reference code |
| `checkpoints/` | rejoin points for Phases 2 and 4 |
| you build | `tools.py`, `harness.py`, `store.py`, `graph.py`, `agent.py` (in this folder) |

Python 3.10 or newer. Everything except LangGraph (Phase 5) and Langfuse (optional) uses only the standard library.
