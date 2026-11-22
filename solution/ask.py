"""Phase 0, the plain prompt call: the "before" picture of a model that can talk but cannot act.

Before you build a harness, it helps to see what a bare model does with "Add 'pay rent' to my to-do list". It
replies "Done!", and nothing was saved. Nothing in this program can save anything: there are no tools, no loop
and no state, so the only thing the model can produce here is words.

Keep that gap in mind for the rest of the course. Every later file exists to turn "the model said it" into "it
really happened, and we can check".

What to look at
    PROMPT        the one request we send, the same kind of request the later phases handle properly.
    plain_call()  sends it and reports the reply next to the tasks really saved, which is always an empty list.
    main()        prints the two side by side so the gap is impossible to miss.

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
