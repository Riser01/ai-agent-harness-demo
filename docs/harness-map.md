# Harness map: the seven parts, where each lives, and what it protects against

## 1. The seven parts, in our code
| Part | In `harness.py` | Phase | Failure it prevents | Scenario | In the wild |
|---|---|---|---|---|---|
| Loop | the `for` loop and its exits | 1, 3a | runaway loop | S4 (`loop-detected`) | Claude Code, OpenAI Agents SDK (`max_turns`) |
| Tools | the `Tool` contract, lookup, `validate` | 1 | wrong tool, invented argument | S8, S9 | MCP (a standard way to describe tools) |
| Context | `cut`, `view` (the window) | 2 | a huge result drowns the model; injected text acts like an order | huge-note drill, S11 | long-context management in every coding agent |
| Memory | the `checkpoint` hook, `store.py` | 4 | lost work after a crash | S7 | LangGraph checkpointers |
| Gates | risk tiers, `approve`, `describe` | 2 | unsafe action | S3a, S4, S9 | Claude Code permission prompts; Replit incident |
| Verify | `verify` after `final` | 3b | silent failure, false "done" | S5, `oldest12_exercise.py` | Gemini CLI incident |
| Trace | `TraceEntry` list | 1 | "what did it do?" | every run; the read-this-trace exercise | Langfuse (`extras/trace_export.py`) |
| + Recovery | `handover_note`; no write retry; `llm.py` retries model calls only | 3b | a failed run nobody can pick up | timeout demo | agent products with "resume" |

## 2. The five failure modes, and where to see each
| Failure mode | Phase | See it | Real incident |
|---|---|---|---|
| Runaway loop | 3a | S4: the model keeps listing; the repeat check stops it | any unbounded agent bill |
| Wrong tool | 1, 2 | S9: asked to "archive", the model reaches for delete. With a blind `yes` it deletes (`sample-runs/12-wrong-tool-archive-approve-yes.txt`); with the gate, the question reads "delete" | OpenAI Operator (Feb 2025): asked to *find* eggs, it *bought* them |
| Invented argument | 1 | S8 (a too-long text, retried shorter) and the model's own slips like a wrong argument name | |
| Silent failure | 3b | S10 and the oldest-12 exercise: the claim differs from the real list | Gemini CLI (Jul 2025): moved files into a folder that was never created, reported success |
| Unsafe action | 2 | S3a, S4, S11; `naive_agent.py` vs `agent.py` | Replit (Jul 2025): "change nothing" was only a prompt |

Talk-only (no code): the **lethal trifecta** (untrusted text + private data + a way out) and Meta's **Rule of Two** (at most two in one session, or a human approves). Our agent has **all three legs**: A, task text anyone can paste (the planted note in `trap.json`); B, personal data (tasks like "Pay rent"); C, a way to change things (`delete_task`). That breaks the Rule of Two, which is exactly why `delete_task` cannot run without a human yes. A **spend cap** in dollars is also talk-only here: this lab prints a call budget instead.

## 3. The plain harness and its LangGraph twin (Phase 5)
| Idea | Plain harness (`harness.py`) | LangGraph (`graph.py`) |
|---|---|---|
| Loop | `for step in range(max_steps)` | a graph **cycle**: `act` -> `decide`, with conditional edges |
| Tools | `tool.validate` + `tool.run` | the `act` node |
| Gate | `approve(...)` before running an irreversible tool | `interrupt()` inside the `gate` node; resumed with `Command(resume=...)` |
| Memory | `checkpoint(state)` + `store.py` JSON | a **checkpointer** (`InMemorySaver`) keyed by `thread_id`; add `store.py` JSON for restarts |
| Step cap | `max_steps` | a `steps` counter in state, plus `recursion_limit` as a backstop |
| Trace | a `TraceEntry` list | `stream()` |
| Verify | `verify(state)` after `final` | the `check` node |
| Unknown tool | refused as an `error:` line | gated like an irreversible tool |

## 4. Numbers worth knowing
- Each task is cut to **100** characters in `list_tasks` (`PREVIEW_CHARS`) so the planted note fits.
- There are **8** statuses. The eighth, `checkpoint-failed`, arrives with memory in Phase 4.
- The "never retry a write" rule is step 7 of `run()` in `harness.py`.

## 5. Two vocabulary notes
- The code's risk words are `read`, `write`, `irreversible`. Some write-ups call the middle tier "reversible": same idea, `write` is the word in the code.
- **Unknown tools are refused outright** in the plain harness. Many designs treat an unknown tool as irreversible (ask a human); the LangGraph engine does exactly that. The plain version is stricter: a tool that does not exist cannot be approved into existence.
