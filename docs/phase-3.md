# Phase 3: hard limits (3a) and verify + recovery (3b)

## 3a. Limits  (about 15 minutes)

### The story
A model can get stuck: ask for the same thing again and again, keep asking for something a human refused, or just never finish. A prompt saying "do not loop" is a request. **Limits are code.**

| Limit | Rule | Status |
|---|---|---|
| Step cap | at most `max_steps` model calls (default 10) | `step-limit` |
| Repeat check | the same call (same tool, same args, key order ignored) 3 times in the last 6 | `loop-detected` |
| Denial cap | `max_denials` (default 3) different actions refused | `denied-limit` |

Order matters: the repeat check comes **before** the gate, so a refused delete asked three times in a row ends `loop-detected`. `denied-limit` needs three *different* refused actions.

### What you build
In `harness.py`: the repeat check and the denial cap are the new parts; the step cap is the loop you already have (this phase just proves it). **Harness part:** loop exits. **Project feature:** none. Contract: `02-technical-spec.md` section 3, steps 4 and 6, and the last paragraph.

### Ask your agent exactly this
> Read `AGENTS.md` and `docs/02-technical-spec.md`. In `harness.py`, make sure the step cap, the repeat check (3 identical calls within the last 6, key order ignored) and the denial cap all end the run with the statuses in the spec. Change nothing else. Make `python3 check.py 3a` pass and do not stop until it passes. Never edit anything in `tests/`.

### Acceptance
`python3 check.py 3a`: all 5 green.

### Try it live
Goal: **"Tidy up my to-do list and tell me what is left."** on the planted-note list, approver **no**:
```
python3 try_it.py "Tidy up my to-do list and tell me what is left." --approve no --seed data/seeds/trap.json
```
**What to expect:** the model reads the note, asks to delete task 2, the gate refuses. A real model often then asks again or keeps listing, and the repeat check stops it as `loop-detected` (see `sample-runs/04-S4-planted-note.txt`), or it finishes `done-with-denials`. Either is a pass: "Pay rent" survives. If the model is **not** fooled, run `python3 naive_agent.py --gullible` to see the deterministic fooled stand-in.

### In the wild
OpenAI's Agents SDK has a `max_turns` limit; LangGraph has a `recursion_limit`. Both exist because every real agent eventually loops.

---

## 3b. Verify and recovery  (about 18 minutes)

### The story
A model can say "Deleted the 12 oldest tasks" when it deleted the wrong ones, or none. That is a **silent failure** (Google's Gemini CLI, July 2025, moved files into a folder that was never created and reported success). The rule: **verification in code first, a second model as judge second**. The harness checks the real state after the model says "final". And when a run stops early, it leaves a **hand-over note** so a person can pick up the work. It never retries a write on its own: a repeated write is worse than one failure (the model call itself is safe to retry, and `llm.py` does that).

### What you build
- `tools.py`: `make_oldest_verifier(state, n)`.
- `harness.py`: run `verify(state)` after `final` (a crashing check never passes); the hand-over note on every early stop; confirm a failing tool is run once only.

**Harness parts:** Verify, Recovery. **Project feature:** the "oldest N" rule. Contract: sections 3 (steps 2 and 7), 6 and 8.

### Ask your agent exactly this
> Read `AGENTS.md` and `docs/02-technical-spec.md`. Add Phase 3b only: `make_oldest_verifier` in `tools.py`, the `verify` step after `final` in `harness.py` (a crashing verifier counts as a problem), a hand-over note for every status except `done` and `done-with-denials` (it must contain the goal and the status name), and make sure a failing tool is never retried. Make `python3 check.py 3b` pass and do not stop until it passes. Never edit anything in `tests/`.

### Acceptance
`python3 check.py 3b`: all 5 green.

### Try it live
1. **The slide exercise (deterministic, no key): 12 oldest of 20, agents A, B and C.**
   ```
   python3 extras/oldest12_exercise.py
   ```
   Agent A deletes ids 1 to 12: `done`. Agent B deletes the 12 *newest*: `failed-verification`. Agent C deletes nothing and says "done": `failed-verification`. All three *said* the same thing; only the check on the real list tells the truth. "Oldest" means lowest id.
2. **Live, 3 of 20** (a real model needs one call per delete and the step cap is 10, so the live goal uses 3): goal **"Delete my 3 oldest tasks (the lowest ids)."**
   ```
   python3 try_it.py "Delete my 3 oldest tasks (the lowest ids)." --approve yes --seed data/seeds/twenty.json --verify-oldest 3
   ```
   Pass is either `done` with 17 left, or `failed-verification`. See `sample-runs/06-S5-delete-oldest.txt`.
3. **The timeout demo:** break the model on purpose and read the hand-over note:
   ```
   LLM_TIMEOUT_SECONDS=0.001 python3 try_it.py "Add File taxes"
   ```
   Status `model-error`, plus a note with the goal and the last step. On Windows: `set LLM_TIMEOUT_SECONDS=0.001` (cmd) or `$env:LLM_TIMEOUT_SECONDS="0.001"` (PowerShell), then run the same command. See `sample-runs/09-timeout-handover.txt`.

### Write your own "done" rule (product decision)
Pick a goal and finish this sentence in plain words: *"The agent may say done only if the real list ______."* Example for "Delete task 99" (see drill 4 in `drills.md`): *"nothing was removed except the task I named."* Then ask your agent to turn your sentence into a `verify` function and run it.

### Talk-only: timeouts
In this lab only the model call has a timeout (`LLM_TIMEOUT_SECONDS`). A production harness also gives every tool a timeout and the whole run a deadline, and remembers that a *write that timed out has an unknown result*: it may or may not have happened, which is why writes are never retried blindly.

### In the wild
Code that looks at the real state comes first. A second model as a judge exists (a "grader"): use it for taste, as pass/fail with a written rubric, and check it against a human's labels, because it is one more thing that can be fooled.

**Retry quiz.** Is it safe to retry `list_tasks`? Yes. `send_email`? Only after checking the Sent folder. A card charge? Only with an idempotency key. Retry at **one layer only** (`llm.py` retries the model call, with a little random jitter, and nothing else does).
