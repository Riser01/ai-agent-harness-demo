"""Save and load the task list as a JSON file, so work survives a restart or a crash. This is the MEMORY part.

WHY THIS FILE EXISTS
    State that lives only in memory disappears when the program stops. The harness calls a checkpoint hook after every
    step that changed something; this file is the project's answer to "what do we save, and where".

WHAT IT PREVENTS
    * Losing all progress on a crash: the harness checkpoints after each change.
    * A half-written file: we write a temporary file first, then swap it in, so the saved file is always whole.
    * Silently starting over on a damaged file: a bad file raises a clear error instead of pretending it is empty.
    * Reusing an id: a file whose next_id is not above every saved id would hand out an id twice.
"""
import json
import os

from tools import State, Task, new_state


def save_state(state: State, path: str) -> None:
    """Write the state to `path` atomically: temporary file first, then replace, so a crash never leaves half a file."""
    data = {"next_id": state.next_id, "tasks": [{"id": t.id, "text": t.text} for t in state.tasks]}
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)


def _whole(value):
    """Return `value` if it is a plain int (not a bool); a text or decimal id means a damaged file, so never guess."""
    if type(value) is not int:
        raise TypeError(f"expected a whole number, got {value!r}")
    return value


def _text(value):
    """Return `value` if it is a string; any other type means a damaged file."""
    if not isinstance(value, str):
        raise TypeError(f"expected text, got {value!r}")
    return value


def load_state(path: str) -> State:
    """Read the state from `path`. A missing file is a fresh start; a damaged or inconsistent file is an error."""
    if not os.path.exists(path):
        return new_state()
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        tasks = [Task(id=_whole(t["id"]), text=_text(t["text"])) for t in data["tasks"]]
        state = State(tasks=tasks, next_id=_whole(data["next_id"]))
    except (OSError, ValueError, KeyError, TypeError) as err:
        raise ValueError(f"cannot read saved tasks in {path}: {err}") from err
    ids = [t.id for t in tasks]
    if len(set(ids)) != len(ids) or (ids and state.next_id <= max(ids)):
        raise ValueError(f"saved tasks in {path} are inconsistent: next_id must be above every task id, and ids must be unique")
    return state
