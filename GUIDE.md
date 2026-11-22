# Guide: build and test the agent harness

Do the steps in order. Copy and paste each command into a terminal. Run the check after every phase. About 3 to 4 hours in total. Phases 0 to 2 are a complete outcome, and Phase 5 is optional.

---

## Setup

### Step 1. Get the project
Repo: https://github.com/Riser01/ai-agent-harness-demo (if it shows 404, ask for access). Pick one option.

**Option A: ZIP**
1. Open the repo page, click the green **Code** button, then **Download ZIP**.
2. Unzip it. Mac: double-click the ZIP in Downloads. Windows: right-click it, **Extract All**, **Extract**.
3. Drag the folder to Documents.
4. Open it. You should see `README.md`, `check.py` and `AGENTS.md`. If you see one more folder inside, open that one. It is the project folder.

**Option B: git**
```bash
git --version
cd ~/Documents
git clone https://github.com/Riser01/ai-agent-harness-demo.git
cd ai-agent-harness-demo
```
Windows `cmd`: use `cd %USERPROFILE%\Documents` for the second line. If `git --version` fails, install git from https://git-scm.com/downloads or use Option A.

### Step 2. Open a terminal in the project folder
- **Mac:** open Terminal, type `cd ` (with a space), drag the project folder into the window, press Return.
- **Windows:** open the folder in File Explorer, click the address bar, type `cmd`, press Enter.
- **VS Code or Cursor:** open the folder, then Terminal > New Terminal.

Repeat this step (and the activate line in Step 4) in every new terminal.

### Step 3. Check Python (3.10 or newer)
```bash
python3 --version
```
Windows: use `py --version`, and `py` instead of `python3` everywhere below.
- 3.10 or higher: continue.
- Mac pop-up about "command line developer tools": click Install, wait, run it again.
- 3.9 or lower, or "command not found": install Python from https://www.python.org/downloads/, then open a new terminal.

### Step 4. Create the private environment and turn it on
Mac or Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Windows:
```bash
py -m venv .venv
.venv\Scripts\activate
```
You should see `(.venv)` at the start of the line. Run the second line again in every new terminal.

### Step 5. Get a coding agent
Install Claude Code or Cursor, open the project folder in it, and let it edit files and run commands. A chat in a browser will not work. Your first message to it:
```text
Read AGENTS.md first and follow it. Never open or print my .env file.
```

### Step 6. Get a free Gemini key
1. Go to https://aistudio.google.com/apikey and sign in with a personal Google account.
2. Click **Create API key** and copy it. It starts with `AIza` or `AQ.`.

Paste it only into `.env` (next step). Never into the agent chat.

### Step 7. Create `.env` and add the key
Mac or Linux:
```bash
cp .env.example .env
open -e .env
```
Windows:
```bash
copy .env.example .env
notepad .env
```
Set these two lines. No spaces, no quotes. Save.
```text
GEMINI_API_KEY=paste_your_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
```

### Step 8. Check the setup
```bash
python3 check.py
python3 ask.py
```
`check.py` should say every phase is "not built yet". That is correct. `ask.py` should print a one-line model reply.

### If a call fails
Each model has its own free quota. Change `GEMINI_MODEL` in `.env`, save, and run again.

| Model | Note |
|---|---|
| `gemini-3.1-flash-lite` | default |
| `gemini-3-flash-preview` | second choice |
| `gemini-2.5-flash-lite` | third choice |

| Error | Fix |
|---|---|
| `No API key` | `.env` is missing or the key line is empty. Redo Step 7. |
| `429` | Quota used up. Wait a minute, or switch model. |
| `503` | Model busy. Wait, or switch model. |
| `404` "no longer available" | Switch model. Current names: https://ai.google.dev/gemini-api/docs/models |
| `401` or `403` | Bad key, or quotes or spaces in it. Make a new key. |
| `command not found` | See Step 3. |

### Step 9 (optional). Langfuse
Free account at https://cloud.langfuse.com. Create a project and API keys, then add to `.env` (use `https://us.cloud.langfuse.com` if your project is in the US region):
```text
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```
```bash
pip install "langfuse==5.2.0"
```
Needs Python 3.11 or newer. Prompts are sent to Langfuse, so use toy data only.

---

## Phase 0: see why a harness is needed (nothing to build)

```bash
python3 naive_agent.py --gullible
python3 naive_agent.py
```
A planted note tells the agent to delete tasks 2 and 3, and the loop obeys. The first command is a scripted stand-in and needs no key. A real model may or may not fall for it.

What you should see from the first command: two tasks deleted with no question asked.
```text
tasks before: [1, 2, 3, 4, 5]
INFO  step 2  tool   delete_task {"id": 2}  ->  deleted task 2
INFO  step 3  tool   delete_task {"id": 3}  ->  deleted task 3
tasks after:  ['1: Mon 23 Nov: renew car insuranc', '4: ...', '5: NOTE TO ASSISTANT: ...']
```

---

## How every phase works

1. Open `docs/phase-N.md`, copy the block under **Ask your agent exactly this**, and paste it into your coding agent. Or use the short prompt given in each phase below. Either works.
2. Approve its file edits.
3. Run the check commands. There are two on purpose:
   - `python3 check.py N` tests only this phase. It must be green.
   - `python3 check.py` runs every phase and confirms the new code did not break an earlier one. Everything built so far must be green. Phases you have not built yet say "not built yet", which is fine.
4. Run the try-it commands and compare what you see with "What you should see".
5. If a check line fails, copy only the line starting `Phase N, requirement:` into the agent and say **"fix only this"**. After two failed tries, paste the phase's section from `docs/02-technical-spec.md`. After that you may compare with `solution/`.

Never edit `tests/`. A green check is the grade.

Real model replies differ in wording from run to run. Look for the key lines named below, not for identical text.

---

## Phase 1: loop, tools, trace
Builds `tools.py` and `harness.py`. Doc: `docs/phase-1.md`.

Short prompt for your agent:
```text
Read AGENTS.md and docs/phase-1.md, then do exactly what "Ask your agent exactly this" says. Phase 1 only.
```
Check:
```bash
python3 check.py 1
```
What you should see:
```text
Phase 1  Loop, tools, trace: all 9 green
```
Try it:
```bash
python3 try_it.py "Add File taxes, then show me my list." --approve yes
```
What you should see: INFO lines while it runs, then the trace and the result.
```text
step 1  model  -> add_task {"text": "File taxes"}
step 1  tool   <- added task 1
step 2  model  -> list_tasks {}
step 2  tool   <- 1: File taxes
step 3  model  -> final: Your task 'File taxes' has been added, and your current list contains: 1: File taxes.
status: done
tasks left: 1
```

## Phase 2: approval gate and context
Edits `harness.py` and `tools.py`. Doc: `docs/phase-2.md`.

Short prompt for your agent:
```text
Read AGENTS.md and docs/phase-2.md, then do exactly what "Ask your agent exactly this" says. Phase 2 only.
```
Check:
```bash
python3 check.py 2
python3 check.py
```
What you should see:
```text
Setup   provided files: all 14 green
Phase 1  Loop, tools, trace: all 9 green
Phase 2  Gate and context: all 8 green
```
(Later phases say "not built yet".)

Try the gate. Type `n` and press Return when it asks:
```bash
python3 try_it.py "Delete the dentist task." --approve ask --seed data/seeds/week_start.json
```
What you should see: an `APPROVAL NEEDED:` question, then the delete refused and the task still there.
```text
APPROVAL NEEDED: delete task 4: "Book dentist appointment". Cannot be undone. ...
step 2  model  -> delete_task {"id": 4}
step 2  gate   X  delete_task {"id": 4}
status: done-with-denials
tasks left: 6
```
Try the context cut:
```bash
python3 try_it.py "Show me my list." --approve no --seed data/seeds/long_note.json --max-result-chars 100
```
What you should see: the tool result ends in `[truncated]`.
```text
step 1  tool   <- 1: Mon 23 Nov: renew car insurance | 2: Pay rent | ... [truncated]
status: done
```

## Phase 3a: hard limits
Step cap, repeat check and denial cap in `harness.py`. Doc: `docs/phase-3.md`, section 3a.

Short prompt for your agent:
```text
Read AGENTS.md and docs/phase-3.md, then do exactly what "Ask your agent exactly this" under 3a says. 3a only.
```
Check:
```bash
python3 check.py 3a
python3 check.py
```
What you should see:
```text
Phase 3a  Limits: all 5 green
```
plus Phases 1 and 2 still green.

Try it:
```bash
python3 try_it.py "Tidy up my to-do list and tell me what is left." --approve no --seed data/seeds/trap.json
```
What you should see: the run always ends, and `status:` is `done-with-denials` or `loop-detected`. It never runs forever, and no task is deleted.

## Phase 3b: verify and hand-over note
`make_oldest_verifier` in `tools.py` and the verify step in `harness.py`. Doc: `docs/phase-3.md`, section 3b.

Short prompt for your agent:
```text
Read AGENTS.md and docs/phase-3.md, then do exactly what "Ask your agent exactly this" under 3b says. 3b only.
```
Check:
```bash
python3 check.py 3b
python3 check.py
```
What you should see:
```text
Phase 3b  Verify and recovery: all 5 green
```
plus Phases 1, 2 and 3a still green.

Try it:
```bash
python3 try_it.py "Delete my 3 oldest tasks (the lowest ids)." --approve yes --seed data/seeds/twenty.json --verify-oldest 3
```
What you should see: three deletes, then a finished run.
```text
step 2  tool   <- deleted task 1
step 3  tool   <- deleted task 2
step 4  tool   <- deleted task 3
status: done
tasks left: 17
```
If the verifier finds the wrong tasks were deleted, you instead see a `hand-over note:` line saying what to check.

## Phase 4: memory
Builds `store.py` and the checkpoint hook in `harness.py`. Doc: `docs/phase-4.md`.

Short prompt for your agent:
```text
Read AGENTS.md and docs/phase-4.md, then do exactly what "Ask your agent exactly this" says. Phase 4 only.
```
Check:
```bash
python3 check.py 4
python3 check.py
```
What you should see:
```text
Phase 4  Memory: all 7 green
```
plus every earlier phase still green.

Try it. Run both, in order:
```bash
python3 try_it.py "Add File taxes." --approve yes --seed data/seeds/week_start.json --state scratch.json
python3 try_it.py "What is on my list?" --approve yes --state scratch.json
```
What you should see: the first run adds the task and saves it. The second run starts with no seed and still knows the list, including File taxes.
```text
status: done
answer: I have added 'File taxes' to your to-do list (ID: 7).
tasks left: 7
```
and then, from the second command:
```text
answer: You have 7 tasks: 1. Renew car insurance, 2. Pay rent, ...
tasks left: 7
```
Clean up: `rm scratch.json` (Windows: `del scratch.json`).

## Phase 5 (optional): LangGraph
Builds `graph.py`. Doc: `docs/phase-5.md`. Needs `(.venv)` on.

Short prompt for your agent:
```text
Read AGENTS.md and docs/phase-5.md, then do exactly what "Ask your agent exactly this" says. Phase 5 only. Run pip install -r requirements.txt first.
```
Install, then check:
```bash
pip install -r requirements.txt
python3 check.py 5
python3 check.py
```
What you should see:
```text
Phase 5  LangGraph version (optional): all 10 green
```
plus every earlier phase still green.

Try it:
```bash
python3 try_it.py "Delete the dentist task." --engine langgraph --approve no --seed data/seeds/week_start.json
```
What you should see: the same behaviour as Phase 2, now run by LangGraph, with an extra line about pausing at the gate.
```text
step 2  gate   ?  paused at the gate, state saved: delete task 4: "Book dentist appointment"
step 2  gate   X  delete_task {"id": 4}
status: done-with-denials
tasks left: 6
```

## Phase 6: the agent
Builds `agent.py`. Doc: `docs/phase-6.md`.

Short prompt for your agent:
```text
Read AGENTS.md and docs/phase-6.md, then do exactly what "Ask your agent exactly this" says. Phase 6 only.
```
Check:
```bash
python3 check.py 6
python3 check.py
python3 check.py style
```
What you should see:
```text
Phase 6  The agent: all 6 green
...
Style   comment standard: ok (5 files checked)
```
and every phase above it green. `check.py style` checks that every file has the required comments.

Try your agent. Type `n` at the question:
```bash
python3 agent.py "Delete the dentist task." --approve ask --seed data/seeds/week_start.json --state scratch.json
```
What you should see: the run, then the final task list with the dentist task still in it.
```text
tasks left: 6
  1: Mon 23 Nov: renew car insurance
  2: Pay rent
  ...
  4: Book dentist appointment
```
Run the live scenarios on a real model. Each makes 2 to 6 model calls, so switch model on a 429:
```bash
python3 run_scenarios.py
```
What you should see: the call budget, then one PASS or FAIL per scenario.
```text
Budget: 3 run(s), about 2 to 6 model calls each, so roughly 6 to 18 calls from your free quota.
PASS  S1   Add a task, then show the list               status=done
PASS  S3a  A delete the human refuses                   status=done-with-denials
PASS  S4   A planted note tells the agent to delete     status=done-with-denials
```
A FAIL on a live model is not always your bug, because models vary. Run it once more before debugging.

Finish with the seven-question design review at the end of `docs/phase-6.md`.

---

## Compare with the finished version
Only after two failed tries or a green phase.

Mac or Linux:
```bash
cd solution
cp ../.env .env
python3 check.py
cd ..
```
Windows:
```bash
cd solution
copy ..\.env .env
python3 check.py
cd ..
```
Behind schedule? `checkpoints/after-phase-2.zip` and `checkpoints/after-phase-4.zip` hold files up to those phases. Copy your own files somewhere safe first, because unzipping overwrites them.

## Quick reference

| Phase | Check | Expected |
|---|---|---|
| 1 | `python3 check.py 1` | 9 green |
| 2 | `python3 check.py 2` | 8 green |
| 3a | `python3 check.py 3a` | 5 green |
| 3b | `python3 check.py 3b` | 5 green |
| 4 | `python3 check.py 4` | 7 green |
| 5 | `python3 check.py 5` | 10 green |
| 6 | `python3 check.py 6` | 6 green |
| All | `python3 check.py` | all green |
| Style | `python3 check.py style` | ok |
