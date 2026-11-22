"""The to-do app: the PROJECT layer (everything specific to a task list).

WHY THIS FILE EXISTS
    The harness (harness.py) knows nothing about tasks. It only knows "a tool has a name, a risk tier, an input check
    and a run function". Everything about to-do lists lives here, so you could swap this file for an email tool or a
    payments tool and keep the harness unchanged.

WHAT IT PREVENTS
    * A model inventing arguments: every tool checks its input first, and a problem goes back to the model as text.
    * Silent duplicates: the duplicate rule is a PROJECT rule, so it lives here and not in the harness.
    * Hidden risk: each tool carries its risk tier (read / write / irreversible) in code, never in the prompt.
    * Believing a false "done": make_oldest_verifier checks the real list after "delete my 3 oldest".
"""
from dataclasses import dataclass, field
from typing import Any

from harness import Tool

PREVIEW_CHARS = 100     # list_tasks shows this much of each task, so one huge note cannot hide the ids of the rest


@dataclass
class Task:
    """One to-do item."""
    id: int
    text: str


@dataclass
class State:
    """Everything the agent works on. It lives in the harness's hands, never in the model's memory."""
    tasks: list[Task] = field(default_factory=list)
    next_id: int = 1


def new_state() -> State:
    """An empty task list."""
    return State(tasks=[], next_id=1)


def _is_text(value: Any) -> bool:
    """True for a non-blank string of at most 200 characters."""
    return isinstance(value, str) and value.strip() != "" and len(value) <= 200


def _is_int(value: Any) -> bool:
    """True for a real integer. Python counts True/False as ints, so they are rejected explicitly."""
    return isinstance(value, int) and not isinstance(value, bool)


def _same(text: str) -> str:
    """The duplicate rule's yardstick: lower case, trimmed, inner spaces collapsed."""
    return " ".join(text.lower().split())


def _run_add(args: dict[str, Any], state: State) -> str:
    """Add a task unless an equal one exists. Raising turns the refusal into an error line the model can read."""
    for existing in state.tasks:
        if _same(existing.text) == _same(args["text"]):
            raise ValueError(f"duplicate of task {existing.id}")
    task = Task(id=state.next_id, text=args["text"].strip())
    state.next_id += 1
    state.tasks.append(task)
    return f"added task {task.id}"


def _run_list(_args: dict[str, Any], state: State) -> str:
    """One line per task, 'id: first 100 characters'. The cut keeps every id visible however long one task is."""
    if not state.tasks:
        return "no tasks"
    return "\n".join(f"{t.id}: {t.text[:PREVIEW_CHARS]}" for t in state.tasks)


def _describe_delete(args: dict[str, Any], state: State) -> str:
    """Plain words for the approval prompt: the human sees the real task text, not just a number."""
    task = next((t for t in state.tasks if t.id == args.get("id")), None)
    if task is None:
        return f"delete task {args.get('id')} (no such task)"
    return f'delete task {task.id}: "{task.text[:60]}"'


def _run_delete(args: dict[str, Any], state: State) -> str:
    """Remove a task by id. A missing id is an error, never a fake success. Atomic: it changes nothing before it can fail."""
    index = next((i for i, t in enumerate(state.tasks) if t.id == args["id"]), None)
    if index is None:
        raise ValueError(f"no task with id {args['id']}")
    state.tasks.pop(index)
    return f"deleted task {args['id']}"


add_task = Tool(
    name="add_task",
    description="Add a new task to the to-do list.",
    params={"text": "string, 1 to 200 characters"},
    risk="write",
    validate=lambda a: None if _is_text(a.get("text")) else "text must be a non-empty string of at most 200 characters",
    run=_run_add,
)

list_tasks = Tool(
    name="list_tasks",
    description="List all tasks with their numeric ids.",
    params={},
    risk="read",
    validate=lambda _a: None,
    run=_run_list,
)

delete_task = Tool(
    name="delete_task",
    description="Permanently delete a task by its numeric id.",
    params={"id": "integer"},
    risk="irreversible",
    validate=lambda a: None if _is_int(a.get("id")) else "id must be an integer",
    run=_run_delete,
    describe=_describe_delete,
)

ALL_TOOLS: list[Tool] = [add_task, list_tasks, delete_task]


def make_oldest_verifier(state: State, n: int):
    """Verify: snapshot the ids NOW, and return a check for 'exactly the n oldest tasks are gone'. Oldest means lowest id."""
    start_ids = sorted(t.id for t in state.tasks)
    oldest = set(start_ids[:n])

    def verify(current: State) -> "str | None":
        """Compare the real list with the snapshot. Returns a problem sentence, or None when the goal truly holds."""
        now = {t.id for t in current.tasks}
        still_there = sorted(oldest & now)
        if still_there:
            return f"task {still_there[0]} is one of the {n} oldest but still exists"
        wrongly_gone = sorted(set(start_ids) - now - oldest)
        if wrongly_gone:
            return f"task {wrongly_gone[0]} was deleted but is not among the {n} oldest"
        return None

    return verify
