"""The saved file: how the to-do list survives the program ending.

Without this file, a crash, a closed laptop or even a second command would start again from an empty list. The harness
only promises to call a checkpoint hook after every step that changed something (harness.py, step 8). What to save and
where to put it is the project's decision, so it lives here, in the app layer.

What to look at, and why each piece is here (line numbers are for this file as shipped)
    save_state (line 25, the swap at 31)
        Writes a temporary file and then replaces the real one, so a crash in the middle of a write can never leave
        half a file behind.
    _whole and _text (lines 34 and 41)
        Refuse a text id or a number where text belongs. A damaged file must be an error, not a guess.
    load_state (line 48, the error at 58)
        A missing file means a fresh start. A damaged one raises a clear error instead of quietly starting over, which
        would erase real tasks the next time the file is saved.
    The consistency check (line 60)
        A next_id that is not above every saved id would hand out the same id twice.
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
