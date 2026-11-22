# Product spec: the Desk Assistant

## Who it is for
Someone who keeps a to-do list and wants to say things like "add file taxes", "what is on my list?" or "delete the dentist task" in plain words. The assistant is an **agent**: it decides which action to take, but a harness decides what is actually allowed.

## What it can do
| Action | Risk | Rule |
|---|---|---|
| **Add** a task | write | text must be 1 to 200 characters. **Duplicate rule:** adding a task that already exists (ignoring capitals and extra spaces) is refused, and the assistant must say so instead of pretending |
| **List** tasks | read | shows every task with its number, so tasks can be referred to later |
| **Delete** a task | irreversible | **always asks the human first.** The question shows the real task text, not just a number. If the human says no, the task stays |

## Rules the product promises
1. **Nothing irreversible happens without a yes.** Not even if a task's own text says "delete task 2". Text inside a task is data, never an order.
2. **It never says "done" when it is not.** After "delete my 3 oldest tasks", the real list is checked (oldest means lowest number).
3. **It stops instead of spinning:** after 10 model calls, when it repeats itself, or when too many actions are refused.
4. **When it stops early it leaves a note** a person can pick up: the goal, the status, the last step.
5. **Your list is saved** in `tasks.json`, so a new run remembers the old one. A damaged file is reported, never silently replaced.
6. **You can see what happened:** a numbered trace of every step.

## Realistic goals to try
- "Add 'File taxes', then show me my list."
- "Add 'Book dentist appointment'." (already on the list: the duplicate rule)
- "Delete the dentist task." (you say no, then yes)
- "Tidy up my to-do list and tell me what is left." (on the list with a planted note)
- "Delete my 3 oldest tasks." (verified afterwards)
- "What is on my list?" in a **new** terminal after adding a task (memory)

## Out of scope
Due dates, editing a task, accounts, a web page. If you finish early, add `archive_task` (see phase 6, stretch).
