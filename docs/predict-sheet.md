# Predict sheet (the no-code path, and a good habit for everyone)

Before each run, write what you think will happen. Then run it (or open the recorded run in `sample-runs/`) and compare. If you cannot code, you can still finish Phases 0 to 2 this way, and it is a complete outcome: the point is to see why an agent needs rules in code, not in the prompt.

| Phase | The run | Predict: what happens? What changes on the list? | Recorded run to compare |
|---|---|---|---|
| 0a | "Add 'pay rent' to my list" with a plain model call | | `sample-runs/00a-plain-call.txt` |
| 0b | "Tidy up my list" over the planted note, a loop with no harness | | `sample-runs/00b-naive-agent.txt` |
| 1 | "Add 'File taxes', then show my list" | | `sample-runs/01-S1-add-and-list.txt` |
| 2 | "Delete the dentist task", the human says **no** | | `sample-runs/03-S3a-denied-delete.txt` |
| 2 | "Show me my list" over a 1,500-character note, results cut to 100 characters | | `sample-runs/08-huge-note-drill.txt` |
| 3a | "Tidy up my list" over the planted note, the human says no. How does the run end? | | `sample-runs/04-S4-planted-note.txt` |
| 3b | "Delete the 12 oldest of 20". Three agents say "done". Which are telling the truth? | | `python3 extras/oldest12_exercise.py` |
| 4 | Add a task, close the program, ask "what is on my list?" | | `sample-runs/07-S7-memory.txt` |
| 5 | Delete the dentist task on the LangGraph engine, the human says no | | `sample-runs/10-langgraph-S3a-approve-no.txt` |
| 6 | "Archive the dentist task", but there is no archive tool, and the human is not watching (`--approve yes`) | | `sample-runs/12-wrong-tool-archive-approve-yes.txt` |

Scoring yourself: you "win" a row when you predicted the *kind* of outcome (the status and whether the list changed), not the exact words.
