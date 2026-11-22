# Rules for any coding agent working in this folder

You are helping a learner build an AI agent harness. These rules apply whatever coding agent you are.

1. **Standard library only.** Do not add dependencies. The only exception is Phase 5, where `graph.py` may use LangGraph (see `requirements.txt`).
2. **No new files** beyond the ones the phase asks for (`tools.py`, `harness.py`, `store.py`, `graph.py`, `agent.py`). No helper modules, no extra folders, no config files.
3. **Implement exactly the names and signatures in `docs/02-technical-spec.md`.** Do not paraphrase the contract or invent your own design. If the spec and your habits disagree, the spec wins.
4. **Comment standard (checked by `python3 check.py style`):** every file opens with a short plain-prose docstring (what the file is, why it is needed, what goes wrong without it, then what to look at; no blunt headings; see `docs/02-technical-spec.md` section 12); every function and class has a one-line docstring; comments explain *why*, not *what*; label each step of `run()` with the harness part it is.
5. **Do not read the `solution/` folder on your own.** Build from `docs/` first. Open a file in `solution/` only if the learner tells you to (after two failed tries, or after the phase is green), and never copy it in wholesale. If the learner asks you to compare with `solution/<file>.py` after two failed tries or a green phase, that is allowed.
6. **Never edit anything in `tests/`, `check.py`, `docs/`, `data/` or the provided files** (`config.py`, `llm.py`, `ask.py`, `naive_agent.py`, `try_it.py`, `run_scenarios.py`). If a test seems wrong, say so to the learner; do not change it.
7. **One phase at a time.** Build only the phase you were asked for. Do not add features from later phases.
8. **Run `python3 check.py N` until it is green**, then also run `python3 check.py` to make sure earlier phases are still green. Report the actual output, not a guess.
9. **Never put a key in code, a comment, a doc or a chat message.** Keys live in `.env` only.
10. Keep it small and simple. A reader who is not a programmer should be able to follow each function.
