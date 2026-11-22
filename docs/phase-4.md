# Phase 4: memory  (about 20 minutes)

## The story
Run the agent, add a task, close the terminal, run it again: the task is gone, because the list lived only in memory. The model has no memory either: `llm.py` is **stateless**, so the harness owns the context. **Memory** is a deliberate decision about what to save, where, and when. Here: the task list goes to `tasks.json`, and the harness saves it after every step that **changed** something (the *checkpoint hook*), not after reads.

Three safety details: write to a temporary file then replace it, so a crash never leaves half a file; a damaged file is an **error**, never a silent reset to empty; and if saving fails, the run **stops** (`checkpoint-failed`), because losing work silently is worse than stopping.

## What you build
- `store.py`: `save_state` (atomic) and `load_state` (missing file is a fresh start; damaged or inconsistent file raises `ValueError`).
- `harness.py`: call `checkpoint(state)` after every successful non-read tool; a failure ends the run `checkpoint-failed`.

**Harness part:** Memory. **Project feature:** `tasks.json`. Contract: sections 3 (step 8) and 9.

## Ask your agent exactly this
> Read `AGENTS.md` and `docs/02-technical-spec.md`. Create `store.py` with `save_state` and `load_state` as specified, and add the checkpoint hook to `harness.py` (called after each successful tool that is not `read`; if it raises, end with status `checkpoint-failed`). Make `python3 check.py 4` pass and do not stop until it passes. Never edit anything in `tests/`.

## Acceptance
`python3 check.py 4`: all 7 green. Phases 1 to 3 stay green.

## Try it live
Goal: **add, then in a NEW process ask what is on the list.**
```
python3 try_it.py "Add File taxes." --approve yes --seed data/seeds/week_start.json --state scratch.json
python3 try_it.py "What is on my list?" --approve yes --state scratch.json
```
Run them as two separate commands. The second run has no `--seed` and still knows the task, because `scratch.json` was saved by your checkpoint hook. See `sample-runs/07-S7-memory.txt`. Delete `scratch.json` to start fresh.

**What to expect:** the second run lists the old tasks plus "File taxes". Open `scratch.json` and read it: it is plain JSON.

## In the wild
LangGraph calls this a **checkpointer** (you will use one in Phase 5). Claude Code keeps its context between sessions in files too. "Where does state live?" is the question to ask of any agent.
