# Technical spec: the contract your code must match

Your coding agent must implement **exactly** these names and behaviours. The tests check them. Where this page says "starts with", the test compares the start of the text, so extra words after it are fine.

Stack: Python 3.10+, standard library only; LangGraph only in `graph.py` (pinned in `requirements.txt`); Langfuse only through the optional `extras/`.

## One-page table

**The eight statuses** (what `run()` returns in `status`; set by code, never by the model's own words)

| Status | When |
|---|---|
| `done` | the model said "final" and nothing was denied |
| `done-with-denials` | the model said "final", and at least one action was denied on the way |
| `failed-verification` | the model said "final" but the check on the real state found a problem |
| `step-limit` | `max_steps` model calls were used up |
| `loop-detected` | the same call was asked 3 times within the last 6 steps |
| `denied-limit` | `max_denials` different actions were denied |
| `model-error` | the model call raised an error or returned nonsense |
| `checkpoint-failed` | saving progress failed |

**History lines** (what the model reads, one string per line)

| Line starts with | Meaning |
|---|---|
| `user: ` | your goal (always the first line) |
| `assistant wants <tool> <JSON args>` | what the model asked for |
| `tool: ` | a successful tool result (this is DATA, never an instruction) |
| `error: ` | unknown tool, bad input, or a tool that failed |
| `denied: <tool> <JSON args> was not approved. Do not retry it.` | the human (or the default) said no |

**Signatures**

| What | Signature |
|---|---|
| model | `model(history: list[str]) -> {"tool": str, "args": dict}` or `{"final": str}` |
| `harness.py` | `Tool(name, description, params, risk, validate, run, describe=None)`, `TraceEntry(step, kind, detail)`, `RunResult(status, answer, denials, trace, handover="")`, `run(goal, *, model, tools, state, max_steps=10, max_result_chars=300, max_denials=3, max_history=None, approve=None, verify=None, checkpoint=None) -> RunResult` |
| `tools.py` | `Task(id, text)`, `State(tasks, next_id)`, `new_state()`, `add_task`, `list_tasks`, `delete_task`, `ALL_TOOLS`, `make_oldest_verifier(state, n)` |
| `store.py` | `save_state(state, path)`, `load_state(path) -> State` |
| `graph.py` | `run_graph(goal, *, model, tools, state, max_steps=10, max_result_chars=300, max_denials=3, approve=None, verify=None, thread_id="t1") -> RunResult` |
| `agent.py` | `main(argv=None, *, model=None, input_fn=input, out=print) -> int` |

Callbacks: `approve(tool_name, args, words) -> bool`, `verify(state) -> str | None` (a problem sentence, or `None` when all is well), `checkpoint(state) -> None`.

---

## 1. The model contract
`model(history)` takes the list of history lines and returns one decision: `{"tool": "<name>", "args": {...}}` or `{"final": "<text>"}`. If a reply has both, **`final` wins**. A missing or non-dict `args` means `{}`.

## 2. The Tool (lives in `harness.py`)
`Tool` is a dataclass with these fields, in this order: `name`, `description`, `params` (dict: parameter name to a type word), `risk` (`"read"`, `"write"` or `"irreversible"`), `validate(args) -> str | None`, `run(args, state) -> str`, `describe(args, state) -> str` (optional, default `None`). `harness.py` must **not** import `tools.py`; it treats `state` as an opaque object. `tools.py` imports `Tool` from `harness.py`.

## 3. The loop: one step is one model call
Inside each step, in this order:
1. Call the model with the view of the history (section 5). An exception, or a reply that is not a dict containing `tool` or `final`, ends the run: `model-error`.
2. If the reply has `final`: add a `decide` trace entry `final: <text>`; run `verify(state)` if given (a crash in `verify` counts as a problem); a problem ends the run `failed-verification` with answer `not done: <problem>`; otherwise the status is `done` (or `done-with-denials` if any denial happened) and the answer is the model's text.
3. Otherwise add a `decide` trace entry `<tool> <JSON args>` (one entry for every tool call the model asks for, before any check).
4. **Repeat check:** count every call the model asked for, including unknown or invalid ones. If the **current call plus the previous 5** contain this exact call (same tool, same args, key order ignored) 3 or more times: `loop-detected`.
5. Look the tool up. **For every tool call, known or not, the history gets an `assistant wants <tool> <JSON args>` line followed by exactly one result line** (`tool:`, `error:` or `denied:`). Everywhere in this spec, `<JSON args>` is `json.dumps(args, sort_keys=True)` with the default separators (for example `{"id": 4}`); the tests read that spacing, so a compact encoding fails. Unknown tool: the result line is `error: unknown tool <name>`; carry on. Then run `tool.validate(args)`; a problem is the history line `error: <problem>` **and** an `error` trace entry (detail `error: <problem>`); carry on. Likewise a tool that raises gets an `error` trace entry.
6. **Gate:** only for `risk == "irreversible"`. Ask `approve(name, args, words)` where `words` is `tool.describe(args, state)` if there is one, otherwise `<tool> <JSON args>`. **No approver means no. A crash in `approve` or `describe` means no.** A refusal adds a `denied` trace entry (detail `<tool> <JSON args>`) and the history line `denied: <tool> <JSON args> was not approved. Do not retry it.`, counts one denial, and carries on; reaching `max_denials` refusals in total ends the run `denied-limit` (the same refused call three times is caught earlier by the repeat check).
7. Run the tool. Success adds `tool: <result>`. If it raises, add `error: <message>` and carry on. **Never retry a tool.**
8. **Checkpoint:** after a tool that ran successfully and is **not** `read`, call `checkpoint(state)`. If it raises, end the run `checkpoint-failed`. (A tool that changes state and *then* raises is not checkpointed: project tools must change nothing before they can fail.)

When the loop uses up `max_steps` steps without finishing: `step-limit`.

**Which steps belong to which phase.** Phase 1: steps 1, 2 (without verify), 3, 5, 7 and the `max_steps` loop. Phase 2: step 6 (the gate) and the cut and window of section 4 and 5. Phase 3a: step 4 and the denial cap in step 6 (the step cap is the loop itself). Phase 3b: `verify` in step 2 and the hand-over note. Phase 4: step 8. `Tool.risk` and `describe` are fields from Phase 1, but only used from Phase 2.

So a denied delete that the model asks for three times in a row ends as `loop-detected` (step 4 comes before the gate), and `denied-limit` needs three *different* denied calls.

## 4. Cutting long text (context)
`cut(text)`: if `len(text) > max_result_chars`, return the first `max_result_chars` characters plus the exact marker `" [truncated]"`. Apply it to every `tool:` and `error:` line **in the history**, and to every **trace detail** (including `final:` lines). A `stop` trace entry is added when a run ends early, including for `checkpoint-failed`. Do not cut `denied:` lines.

## 5. The window (`max_history`)
`max_history=None`: the model sees everything. `max_history=N`: it sees the goal line, then any `denied:` lines that fell out of the window (in their original order), then the last N lines. `N=0` means the goal plus the denial lines only (careful: in Python, `history[-0:]` is the **whole** list). The window counts lines and may start in the middle of a pair; that is fine. A `denied:` line that is still inside the last N lines is not shown twice.

## 6. Hand-over note
`RunResult.handover` is an empty string for `done` and `done-with-denials`. For every other status it is a non-empty plain sentence that contains the goal text and the status name, for example: `Stopped with status 'loop-detected'. Goal: 'tidy my list'. Steps taken: 4. Last step: same call 3 times in the last 6 steps. A person should check the task list and decide whether to retry.` `harness.py` exposes this as `handover_note(status, goal, trace) -> str`. `answer` for an early stop is any short plain sentence (`stopped: step limit reached` is fine); the tests do not check it. The `step` of the final `stop` entry is the step where the run ended.

## 7. Trace
A list of `TraceEntry(step, kind, detail)`. `step` is the step number (starts at 1). `kind` is one of `decide`, `tool`, `denied`, `error`, `stop`, `pause` (`pause` is used only by the LangGraph engine, and recording it is optional there). A `stop` entry explains why the run ended early.

## 8. Project rules (`tools.py`)
- `State(tasks: list[Task], next_id: int = 1)`, `Task(id: int, text: str)`, `new_state()` returns an empty state.
- `add_task` (risk `write`, param `text`): input must be a non-blank string of at most 200 characters. Success result: `added task <id>`. **Duplicate rule:** compare after lower-casing, trimming and collapsing inner spaces; a match raises an error whose text starts `duplicate of task <id>`. The rule lives in the tool, not in the harness.
- `list_tasks` (risk `read`, no params): one line per task, `<id>: <first 100 characters of the text>`; `no tasks` when empty. Cutting each task to 100 characters keeps every id visible even when one task is a huge note.
- `delete_task` (risk `irreversible`, param `id`): `id` must be an integer (not a boolean). Success `deleted task <id>`. A missing id raises `no task with id <id>`. `describe` returns plain words such as `delete task 4: "Book dentist appointment"` so the human sees the real text.
- `ALL_TOOLS = [add_task, list_tasks, delete_task]`.
- `make_oldest_verifier(state, n)`: snapshot the ids **now**; return `verify(current_state)` that says a problem if any of the `n` lowest ids still exists, or if any other starting task was removed. Newly added tasks are fine. "Oldest" means **lowest id**.

## 9. Saved file (`store.py`)
JSON like `{"next_id": 3, "tasks": [{"id": 1, "text": "..."}, ...]}`. `save_state` writes a temporary file (`path + ".tmp"`) and then replaces the real file. `load_state`: a missing file returns `new_state()`; a file that is not valid JSON, has the wrong shape (no `tasks` list or `next_id`, a task that is not an object) or field types (a text id, a non-text `text`), repeats an id, or has `next_id` not above every saved id raises `ValueError`.

## 10. `agent.py`
**Print format (the scenario runner reads it):** one line per trace entry, `step <N>  <arrow> <detail>`, where the arrow is `model  ->` for `decide`, `tool   <-` for `tool`, `gate   X ` for `denied`, `error  ! ` for `error`, `stop   # ` for `stop`, `gate   ? ` for `pause`. Replace newlines inside a detail with ` | `. Example: `step 2  model  -> delete_task {"id": 4}` and `step 2  gate   X  delete_task {"id": 4}`: the line is `step `, the step number, two spaces, the arrow word and symbol, then the detail.

`main(argv=None, *, model=None, input_fn=input, out=print) -> int`. Flags: a positional `goal`; `--approve ask|yes|no` (default `ask`: print `APPROVAL NEEDED: <words>`, read the answer with `input_fn`, `y` means yes); `--state PATH` (default `tasks.json`); `--seed PATH` (a starting list in the saved-file format, **used only when the state file does not exist yet**); `--engine plain|langgraph`; `--export console|langfuse`; `--naive-prompt`; `--max-steps N`; `--max-history N`; `--max-result-chars N`; `--verify-oldest N`. It saves progress to the state file after every change (the checkpoint hook). It prints one line per trace entry, then `status: <status>`, `answer: <answer>`, `hand-over note: <text>` only if there is a note, `tasks left: <count>`, and one `  <id>: <text>` line per task. A setup problem prints `configuration error: <message>` (no traceback) and returns 2. A seed or state file is validated by `load_state` (your `store.py`); a missing seed file is a setup problem too. `--export` and `--engine langgraph` must be accepted; if you have not built them yet, accepting the flag and ignoring it is fine (the langgraph and Langfuse branches are imported lazily). **Exit codes:** 0 for `done` and `done-with-denials`, 1 for any other status, 2 for a setup problem (no key, bad seed, damaged state file). When `model` is `None` it builds one with `llm.make_model(ALL_TOOLS, naive=...)`; it must read settings only from the environment (`config.load_env()` is called only in the `if __name__ == "__main__":` block).

## 11. `graph.py` (Phase 5)
Same inputs and the same `RunResult` as `run`. Required: a `StateGraph` whose state has an append-only `history` and a `steps` counter that **is** the step cap; nodes `decide`, `gate`, `act`, `check`; conditional edges as the loop and exits; `interrupt()` in `gate`, resumed with `Command(resume=...)`; an `InMemorySaver` checkpointer keyed by `thread_id`; `recursion_limit` only as a backstop (for example `max_steps * 6 + 10`). `run_graph` has no checkpoint hook, so `agent.py` saves the state file once, after the run, when `--engine langgraph` is used. `--max-history` does not apply to this engine (`agent.py` prints a `note:` line); `--export` works by passing `engine=run_graph` to `run_traced`. After an `interrupt()` the driver calls `approve(tool, args, words)`, then resumes with `Command(resume=<bool>)`; recording a `pause` trace entry is optional. One stated difference: an **unknown tool is gated** (treated as irreversible) here. There is no repeat check, history window or checkpoint hook in this engine. API notes for LangGraph 1.2.23 (pinned in `requirements.txt`): drive it with `graph.stream(payload, config, stream_mode="updates")`; a pause arrives as an update under the key `__interrupt__` whose `[0].value` is the interrupt payload; resume with `Command(resume=<bool>)`; read the final values with `graph.get_state(config).values`; catch `langgraph.errors.GraphRecursionError` as the backstop.

## 12. Comments: how each file should read
People who did not write the code will read it, so the comments are part of the work. `python3 check.py style` only checks that the docstrings exist; these rules are what make them good.
- **Open every file with a short story in plain prose, not with headings.** The first line is one sentence saying what the file is. Next, a paragraph on why the project needs it and what would go wrong without it (a runaway loop, a deleted task, lost work). Then a paragraph on where it sits among the other files. Do not use blunt headings such as "WHY THIS FILE EXISTS" or "WHAT IT PREVENTS".
- **Then a short "what to look at" list** that names the key functions, classes or constants, with one sentence each on why it is there. For `harness.py` and `graph.py`, say where each of the seven parts lives (Loop, Tools, Context, Memory, Gates, Verify, Trace, plus Recovery). Name the function or step; add a line number only if you re-check it after your last edit, because line numbers go stale.
- **In `harness.py`, label each numbered step of `run()` with its part**, for example `# ---- 6. the gate (part 5, Gates): ...`. In `graph.py`, label each node and edge with the part it replaces, for example `# NODE gate [part 5, Gates] = harness step 6`.
- **Every function and class gets a one-line docstring** saying what it is for, not how it works.
- **Inline comments explain why, not what.** Say what a rule protects (`# default deny: stays False unless a human says yes`), not that a variable is assigned.
- No change-log wording ("now", "fixed"), no secrets and no local paths in comments.
