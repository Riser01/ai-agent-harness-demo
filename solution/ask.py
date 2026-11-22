"""Phase 0: the plain prompt call. This is the "before" picture: a model that can talk but cannot act.

WHY THIS FILE EXISTS
    Before building a harness, see what a bare model does with "Add 'pay rent' to my to-do list". It replies "Done!".
    Nothing was saved, because nothing in this program can save anything: no tools, no loop, no state.

Run it live:  python3 ask.py     (needs a model key in .env; see .env.example)
"""
from typing import Callable

PROMPT = "Add 'pay rent' to my to-do list."


def plain_call(chat: Callable[[str], str], prompt: str = PROMPT) -> dict:
    """Send one prompt and report what the model said and what was actually saved (always nothing)."""
    saved_tasks: list[str] = []          # there is nowhere for the model to put a task
    reply = chat(prompt)
    return {"reply": reply, "tasks_after": list(saved_tasks)}


def main() -> None:
    """Call the real model once and show the gap between what it says and what happened."""
    from config import load_env
    from llm import ask_text

    load_env()
    result = plain_call(ask_text)
    print("model says:      ", result["reply"])
    print("tasks really saved:", result["tasks_after"], " <- nothing: a prompt cannot change anything by itself")


if __name__ == "__main__":
    main()
