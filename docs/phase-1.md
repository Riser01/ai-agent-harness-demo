# Phase 1: the loop, the tools, the trace  (about 25 minutes)

## First, what is a loop?
A person solves a task by repeating four moves: **decide** what to do next, **act**, **observe** what happened, and **stop** when done. An agent does the same, and the repeating part is a `for` loop in ordinary code:

```
repeat up to max_steps times:
    decide   ask the model what to do next
    act      run the tool it picked
    observe  put the result in the history, so the model sees it next turn
    stop     if the model says "final", or a limit is hit
```
Earlier weeks never needed a loop. An agent does, because it cannot know the result of step 2 before it has done step 1. The loop has **exits**: the model says it is done (`final`), or the harness cuts it off (step cap, repeat check, denial cap, a model error). Every exit gets a name, called a *status*.

## The story
Phase 0b showed a loop with no harness. Now you build the first part of the real one. The model never touches your tasks. It only *asks*; your code looks the tool up, checks the input, runs it, and tells the model what happened.

## What you build
- `tools.py`: `Task`, `State`, `new_state`, and the tools `add_task` (with the **duplicate rule**) and `list_tasks`.
- `harness.py`: `Tool`, `TraceEntry`, `RunResult`, and `run(...)` with the loop: ask the model, handle `final`, look up the tool, check input, run it, add history lines, record the trace.

**Harness parts:** Loop, Tools, Trace. **Project feature:** add and list, duplicate rule.

Contract: `02-technical-spec.md` sections 1, 2, 3 (steps 1 to 3, 5 and 7), 7 and 8. Keep the `max_steps` loop in; it is graded in Phase 3a.

## Ask your agent exactly this
> Read `AGENTS.md` and `docs/02-technical-spec.md`. Create `harness.py` and `tools.py` for Phase 1 only (the `Tool`, `TraceEntry` and `RunResult` classes, `run()` with the loop, and `add_task` and `list_tasks`). Do not add a gate, a window, a checkpoint or a verifier yet. Use only the standard library. Make `python3 check.py 1` pass and do not stop until it passes. Never edit anything in `tests/`.

## Acceptance
`python3 check.py 1` prints `Phase 1  Loop, tools, trace: all 9 green`.

## Try it live (once Phase 1 is green)
`agent.py` comes in Phase 6, so use the provided quick runner, which only calls what you built. Goal in plain words: **"Add File taxes, then show me my list."**
```
python3 try_it.py "Add File taxes, then show me my list." --approve yes
```

**What to expect:** about 3 model calls: `add_task`, `list_tasks`, then `final`. A trace with numbered steps. Status `done`. Your wording will differ from `sample-runs/01-S1-add-and-list.txt`.

**The live log.** While the run goes, `try_it.py` prints one line per event (on by default; add `--quiet` to see only the end-of-run trace). Each line starts with a level: `INFO` is normal, `WARN` is worth a look (a tool error, a rejected input, a refused approval, a retry), `ERROR` is a failed model call or an unusable reply. Then the step (the model-call count) and what happened:
- `model  asking the model (shown 3 lines)`: printed before the call, so you know the program is waiting for the model (a busy model can take up to a minute). The model is shown 3 history lines.
- `model  reply in 1.8s (412 in / 31 out tokens): {...}`: the call took 1.8 seconds, and this is its **raw reply**, exactly as it wrote it, before the harness read it. A reply wrapped in chatter or code fences shows up here. A retry adds `after 2 attempts, waited 4.1s (HTTP 429)` and the line becomes `WARN`.
- `tool   add_task {"text": "File taxes"}  ->  added task 1`: the tool's input, then its output.
- `gate   delete task 2: "Pay rent"  ->  approved` (or `denied`): the question the human saw and the answer.
- `run    ended: status=done after 3 model calls. Last: ...`: why the run stopped.
The live log is printed by `extras/trace_export.py`, which wraps your model, tools and approver; your `harness.py` is not changed.

## In the wild
This loop is the core of every coding agent, for example Claude Code, and of the OpenAI Agents SDK: ask the model, run the tool, feed the result back, repeat.
